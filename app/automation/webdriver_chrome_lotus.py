from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
import time
import random
import json
from app.db.models import TbCampaigns, TbInstances
from app import db
from contextlib import contextmanager
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log")
    ]
)

TIME_WAIT = 15  # Aumentar o tempo de espera
MAX_RETRIES = 2  # Máximo de tentativas para encontrar um elemento
DELAY_BETWEEN_KEYS = 0.3  # Tempo de delay entre o envio de cada tecla (em segundos)

def type_like_human(element, text, min_delay=0.1, max_delay=0.3):
    logging.info(f"Typed text '{text}' into element {element}")

    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(min_delay, max_delay))

def append_to_campaign_data(session, campaign, array_consult):
    logging.info(f"Appending data to campaign: {array_consult}")

    if campaign.query_data:
        if isinstance(campaign.query_data, list):
            existing_json = campaign.query_data
        else:
            existing_json = json.loads(campaign.query_data)
    else:
        existing_json = []

    new_json = array_consult
    combined_json = existing_json + new_json
    campaign.query_data = json.dumps(combined_json)

    campaign.records_consulted = len(json.loads(campaign.query_data))

    if campaign.records_consulted == campaign.records:
        campaign.status = "CONCLUÍDA"
    else:
        campaign.status = "PARCIAL"
    
    session.commit()

def handle_selenium_exception(session, page, exception, instance, id_campaign):
    error_name = type(exception).__name__
    logging.error(f"Error: {error_name}")

    instance.status = "LIVRE"
    logging.info(f"Set instance status to LIVRE for instance ID: {instance.id}")

    if error_name != "NoSuchWindowException":
        campaign = session.query(TbCampaigns).filter_by(id=id_campaign).first()
        campaign.status = "CANCELADA"
        logging.info(f"Set campaign status to CANCELADA for campaign ID: {id_campaign}")

    session.commit()
    logging.info("Database commit completed")

    page.quit()
    logging.info("Closed Selenium page")

def finalize_campaign(session, instance, id_campaign, array_consult):
    logging.info(f"Finalizing campaign {id_campaign} with data: {array_consult}")

    instance.status = "LIVRE"
    db.session.commit()

    campaign = session.query(TbCampaigns).filter_by(id=id_campaign).first()
    session.refresh(campaign)

    append_to_campaign_data(session, campaign, array_consult)

    session.commit()

def determine_status(page):
    body_text = page.find_element(By.TAG_NAME, "body").text.lower()

    if (
        "Existe uma operação fiduciária em andamento.".lower()
        in body_text
    ):
        status = "Existe uma operação fiduciária em andamento."
    elif (
        "O valor de liberação deve ser maior que R$ 70,00".lower()
        in body_text
    ):
        status = "O valor de liberação deve ser maior que R$ 70,00"
    elif (
        "Instituição Fiduciária não possui autorização do Trabalhador para Operação Fiduciária.".lower()
        in body_text
    ):
        status = "Instituição Fiduciária não possui autorização do Trabalhador para Operação Fiduciária."
    else:
        status = "Ocorreu uma falha na consulta aos dados do cliente"
    
    logging.info(f"Determined status: {status}")
    return status

@contextmanager
def webdriver_chrome_lotus(flask_app, user, password, company, id_instance, id_campaign, array_documents):
    logging.info("Starting webdriver_chrome_lotus context")

    with flask_app.app_context():
        instance = db.session.query(TbInstances).filter_by(id=id_instance).first()
        db.session.refresh(instance)

        # Configura o serviço do ChromeDriver
        driver_path = './chromedriver.exe'
        service = Service(executable_path=driver_path)
        # service = Service(ChromeDriverManager().install())

        # Configura as opções do Chrome
        options = webdriver.ChromeOptions()

        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-infobars')
        options.add_experimental_option("useAutomationExtension", False)
        options.add_experimental_option("excludeSwitches", ["enable-automation"])

        # Inicializa o driver do Chrome com o serviço e as opções configuradas
        
        page = webdriver.Chrome(service=service, options=options)
        page.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            """
        })
        page.delete_all_cookies()

        array_consult = []
        index = 0

        try:
            # Navega até a página de login
            logging.info("Navigating to the login page")
            page.get('https://app.lotusmais.com.br/login')

            # Realiza o preenchimento dos dados de login
            logging.info("Filling in login details")
            login_element = page.find_element(By.XPATH, '//*[@id="email"]')
            password_element = page.find_element(By.XPATH, '//*[@id="password"]')

            type_like_human(login_element, user)
            type_like_human(password_element, password)

            logging.info("Waiting for the dashboard page to load")
            WebDriverWait(page, 2000).until(EC.url_to_be('https://app.lotusmais.com.br/dashboard'))

            current_datetime = datetime.now()
            formatted_date = current_datetime.strftime("%d/%m/%Y %H:%M:%S")

            for document in array_documents:
                try:
                    name = ""
                    phone = ""
                    guarantee_value = 0
                    released_value = 0
                    status = "Ocorreu uma falha na consulta aos dados do cliente"

                    campaign = db.session.query(TbCampaigns).filter_by(id=id_campaign).first()
                    db.session.refresh(campaign)

                    if index >= 10:
                        append_to_campaign_data(db.session, campaign, array_consult)
                        array_consult = []
                        index = 0

                    # Vai para a página de dashboard
                    logging.info("Navigating to the dashboard page")
                    page.get('https://app.lotusmais.com.br/fgts/new')
                    time.sleep(2)

                    def safe_click(xpath):
                        for _ in range(MAX_RETRIES):
                            try:
                                element = WebDriverWait(page, TIME_WAIT).until(
                                    EC.visibility_of_element_located((By.XPATH, xpath))
                                )
                                element.click()
                                break
                            except Exception:
                                logging.warning(f"Retry clicking element: {xpath}")
                                continue

                    def safe_send_keys(xpath, data):
                        for _ in range(MAX_RETRIES):
                            try:
                                element = WebDriverWait(page, TIME_WAIT).until(
                                    EC.visibility_of_element_located((By.XPATH, xpath))
                                )
                                
                                for char in data:
                                    element.send_keys(char)
                                    time.sleep(DELAY_BETWEEN_KEYS)
                                    
                                break
                            except Exception:
                                logging.warning(f"Retry sending keys to element: {xpath}")
                                continue

                    # Digita o cpf
                    logging.info(f"Entering CPF for document: {document['cpf']}")
                    safe_click('/html/body/main/div[3]/div/div/div[2]/div/div[1]/div/div[1]/input')
                    safe_send_keys('/html/body/main/div[3]/div/div/div[2]/div/div[1]/div/div[1]/input', document['cpf'])

                    # Clica em consultar
                    logging.info("Clicking on consult button")
                    safe_click('/html/body/main/div[3]/div/div/div[2]/div/div[1]/div/div[2]/button[1]')

                    time.sleep(10)
                    print('a')
                    # Seleciona a tabela XX
                    logging.info("Selecting agreement")
                    safe_click('/html/body/main/div[3]/div/div/div[2]/div/div[3]/div/div/div[1]/div[1]/div[1]/div/button[2]')
                    
                    time.sleep(10)
                    print('z')
                    # Desmarcar Seguro
                    logging.info("Input Select")
                    checkbox = WebDriverWait(page, TIME_WAIT).until(
                      EC.element_to_be_clickable((By.ID, 'hasInsurance'))
                    )

                    is_checked = checkbox.is_selected()

                    if is_checked:
                      safe_click('/html/body/main/div[3]/div/div/div[2]/div/div[3]/div/div/div[1]/div[1]/div[1]/div/button[2]')

                    time.sleep(10)
                    print('b')
                    # Captura o valor reserva
                    logging.info("Capturing guarantee value")
                    div_guarantee_value = WebDriverWait(page, TIME_WAIT).until(
                        EC.visibility_of_element_located((By.CSS_SELECTOR, 'rates__value'))
                    )
                    print('c')
                    guarantee_value = div_guarantee_value.text

                    print("guarantee_value: " + guarantee_value);
                    # Captura o valor liberado
                    logging.info("Capturing available value")
                    div_released_value = WebDriverWait(page, TIME_WAIT).until(
                        EC.visibility_of_element_located((By.CSS_SELECTOR, 'd-flex.mt-2'))
                    )
                    print('d')
                    released_value = div_released_value.text

                    time.sleep(5)

                    obj_success = {
                        "company": company,
                        "document": document['cpf'],
                        "name": name,
                        "phone": phone,
                        "guarantee_value": guarantee_value,
                        "released_value": released_value,
                        "consultation_date": formatted_date,
                        "status": "Sucesso"
                    }

                    logging.info(f"Appending success object for document: {document['cpf']}")
                    array_consult.append(obj_success)
                    index += 1

                except Exception as e:
                    error_name = type(e).__name__
                    logging.error(f"Error list: {error_name}")

                    status = determine_status(page)
                    logging.error(f"Error while processing document {document['cpf']}, Status: {status}")

                    obj_error = {
                        "company": company,
                        "document": document['cpf'],
                        "name": name,
                        "phone": phone,
                        "guarantee_value": guarantee_value,
                        "released_value": released_value,
                        "consultation_date": formatted_date,
                        "status": status
                    }

                    logging.info(f"Appending error object for document: {document['cpf']}")
                    array_consult.append(obj_error)
                    index += 1
                    
                    db.session.rollback()
                    continue
                finally:
                    logging.info(f"Processed document {document['cpf']}, index: {index}")

        except Exception as e:
            logging.critical(f"Critical error in main process")
            handle_selenium_exception(db.session, page, e, instance, id_campaign)

        finally:
            logging.info("Finalizing campaign")
            finalize_campaign(db.session, instance, id_campaign, array_consult)

            db.session.close()
            logging.info("Database session closed")
            page.quit()
            logging.info("Closed Selenium page")
