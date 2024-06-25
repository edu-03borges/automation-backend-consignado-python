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

TIME_WAIT = 35  # Aumentar o tempo de espera
MAX_RETRIES = 3  # Máximo de tentativas para encontrar um elemento

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

    if len(json.loads(campaign.query_data)) == campaign.records:
        campaign.status = "CONCLUÍDA"
    else:
        campaign.status = "PARCIAL"

    append_to_campaign_data(session, campaign, array_consult)

    session.commit()

def determine_status(page):
    body_text = page.find_element(By.TAG_NAME, "body").text.lower()

    if (
        "cliente não autorizou a instituição a realizar a operação fiduciária.".lower()
        in body_text
    ):
        status = "Cliente não autorizou a instituição a realizar a operação fiduciária."
    elif (
        "mudanças cadastrais na conta do fgts foram realizadas, que impedem a contratação.".lower()
        in body_text
    ):
        status = "Mudanças cadastrais na conta do FGTS foram realizadas, que impedem a contratação. Entre em contato com o setor de FGTS da Caixa."
    elif (
        "de acordo com as politicas do banco mercantil, não é possivel digitar uma operação para o cpf informado.".lower()
        in body_text
    ):
        status = "De acordo com as politicas do banco Mercantil, não é possivel digitar uma operação para o cpf informado."
    elif (
        "valor da operação menor que o valor mínimo para emprestimo do produto/convenio.".lower()
        in body_text
    ):
        status = "Valor da Operação menor que o Valor Mínimo para Emprestimo do Produto/Convenio."
    elif "cpf inválido".lower() in body_text:
        status = "CPF inválido"
    elif (
        "código 03 - dados inconsistentes na validação do recaptcha. tente novamente.".lower()
        in body_text
        or "por favor, tente novamente mais tarde!".lower() in body_text
    ):
        status = "Erro no reCAPTCHA. Tente novamente mais tarde."
    else:
        status = "Ocorreu uma falha na consulta aos dados do cliente"
    
    logging.info(f"Determined status: {status}")
    return status

@contextmanager
def webdriver_chrome_mercantil(flask_app, user, password, company, id_instance, array_documents, id_campaign):
    logging.info("Starting webdriver_chrome_mercantil context")

    with flask_app.app_context():
        instance = db.session.query(TbInstances).filter_by(id=id_instance).first()
        db.session.refresh(instance)

        # Configura o serviço do ChromeDriver
        service = Service(ChromeDriverManager().install())

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
        success = False

        try:
            # Navega até a página de login
            logging.info("Navigating to the login page")
            page.get('https://meu.bancomercantil.com.br/login')

            # Realiza o preenchimento dos dados de login
            logging.info("Filling in login details")
            login_element = page.find_element(By.XPATH, '//*[@id="mat-input-0"]')
            password_element = page.find_element(By.XPATH, '//*[@id="mat-input-1"]')

            type_like_human(login_element, user)
            type_like_human(password_element, password)

            logging.info("Waiting for the dashboard page to load")
            WebDriverWait(page, 2000).until(EC.url_to_be('https://meu.bancomercantil.com.br/dashboard'))

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
                    page.get('https://meu.bancomercantil.com.br/simular-proposta')
                    time.sleep(random.uniform(1, 3))

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
                                element.send_keys(data)
                                break
                            except Exception:
                                logging.warning(f"Retry sending keys to element: {xpath}")
                                continue

                    # Seleciona o convênio
                    logging.info("Selecting agreement")
                    safe_click('//*[@id="mat-select-0"]')
                    safe_click('//*[@id="mat-option-6"]/span')

                    # Seleciona a instituição
                    logging.info("Selecting institution")
                    safe_click('//*[@id="mat-select-4"]')
                    safe_click('//*[@id="mat-option-4"]/span')

                    # Seleciona a uf
                    logging.info("Selecting state")
                    safe_click('//*[@id="mat-select-2"]')
                    safe_click('//*[@id="mat-option-32"]/span')

                    # Digita o cpf
                    logging.info(f"Entering CPF for document: {document['cpf']}")
                    safe_send_keys('//*[@id="mat-input-1"]', document['cpf'])

                    time.sleep(random.uniform(1, 3))

                    # Clica em consultar
                    logging.info("Clicking on consult button")
                    safe_click('/html/body/app-root/div/app-main-layout/main/app-simular-proposta/div/div/mat-card/mat-card-content/div/div[1]/div[3]/button')

                    # Clica em nova operação
                    logging.info("Clicking on new operation button")
                    safe_click('/html/body/app-root/div/app-main-layout/main/app-simular-proposta/div/div/mat-card/mat-card-content/div[2]/a')
                    
                    WebDriverWait(page, TIME_WAIT).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))

                    # Captura o telefone
                    logging.info("Capturing phone number")
                    phone_div = WebDriverWait(page, TIME_WAIT).until(
                        EC.visibility_of_element_located((By.XPATH, '/html/body/app-root/div/app-main-layout/main/app-fgts/div/app-container-header/div/mat-card/mat-card-header/div/mat-card-subtitle/span[3]'))
                    )
                    phone = phone_div.text.replace("Telefone : ", "")

                    # Captura o nome
                    logging.info("Capturing name")
                    name_div = WebDriverWait(page, TIME_WAIT).until(
                        EC.visibility_of_element_located((By.XPATH, '/html/body/app-root/div/app-main-layout/main/app-fgts/div/app-container-header/div/mat-card/mat-card-header/div/mat-card-subtitle/span[1]'))
                    )
                    name = name_div.text

                    # Captura o valor garantia da tela inicial
                    logging.info("Capturing initial guarantee value")
                    guarantee_value_element = WebDriverWait(page, TIME_WAIT).until(
                        EC.visibility_of_element_located((By.XPATH, '/html/body/app-root/div/app-main-layout/main/app-fgts/div/div/mat-card[2]/mat-card-content/div/ul/li/div/div/strong'))
                    )

                    guarantee_value_before_simulation = guarantee_value_element.text
                    pattern_guarantee = guarantee_value_before_simulation.replace(",", ".").replace("R$", "").replace(" ", "")
                    guarantee_value = float(pattern_guarantee)

                    if guarantee_value < 150:
                        status = "Saldo insuficiente para simular"
                        raise Exception(status)

                    time.sleep(random.uniform(1, 3))

                    # Clica em iniciar
                    logging.info("Clicking on start button")
                    safe_click('/html/body/app-root/div/app-main-layout/main/app-fgts/div/div/mat-card[2]/mat-card-content/div/ul/li/a')

                    # Clica em simular
                    logging.info("Clicking on simulate button")
                    element_simulation = WebDriverWait(page, TIME_WAIT).until(
                        EC.visibility_of_element_located((By.CSS_SELECTOR, 'button.mat-focus-indicator.pcb-button'))
                    )
                    page.execute_script("arguments[0].click();", element_simulation)

                    # Captura o valor garantia
                    logging.info("Capturing guarantee value")
                    div_guarantee_value = WebDriverWait(page, TIME_WAIT).until(
                        EC.visibility_of_element_located((By.CSS_SELECTOR, '.taxaMedia strong'))
                    )

                    guarantee_value = div_guarantee_value.text

                    # Captura o valor dísponivel
                    logging.info("Capturing available value")
                    div_released_value = WebDriverWait(page, TIME_WAIT).until(
                        EC.visibility_of_element_located((By.CLASS_NAME, 'valorLiberado'))
                    )

                    released_value = div_released_value.text

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

                    status = status = determine_status(page)
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

            success = True

        except Exception as e:
            logging.critical(f"Critical error in main process")
            handle_selenium_exception(db.session, page, e, instance, id_campaign)

        finally:
            if success:
                logging.info("Finalizing campaign")
                finalize_campaign(db.session, instance, id_campaign, array_consult)

            db.session.close()
            logging.info("Database session closed")
            page.quit()
            logging.info("Closed Selenium page")
