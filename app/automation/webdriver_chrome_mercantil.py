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

TIME_WAIT = 30

def type_like_human(element, text, min_delay=0.1, max_delay=0.3):
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(min_delay, max_delay))

def webdriver_chrome_mercantil(flask_app, user, password, company, id_instance, array_documents, new_campaign_id):

    with flask_app.app_context():

        instance = db.session.query(TbInstances).filter_by(id=id_instance).first()
        db.session.refresh(instance)
        
        # Configura o serviço do ChromeDriver
        service = Service(ChromeDriverManager().install())

        # Configura as opções do Chrome
        options = webdriver.ChromeOptions()
        # options.add_experimental_option("detach", True)
        options.add_argument("disable-infobars");
        options.add_argument("--disable-application-cache")

        # Inicializa o driver do Chrome com o serviço e as opções configuradas
        page = webdriver.Chrome(service=service, options=options)

        page.delete_all_cookies()

        try:
            # Navega até a página de login
            page.get('https://meu.bancomercantil.com.br/login')

            # Realiza o preenchimento dos dados de login
            login_element = page.find_element(By.XPATH, '//*[@id="mat-input-0"]')
            password_element = page.find_element(By.XPATH, '//*[@id="mat-input-1"]')

            # Preencher login e senha com atraso entre cada letra
            type_like_human(login_element, user)
            type_like_human(password_element, password)

            # Aguarda até que a página de dashboard carregue
            WebDriverWait(page, 1000).until(EC.url_to_be('https://meu.bancomercantil.com.br/dashboard'))

            current_datetime = datetime.now()
            formatted_date = current_datetime.strftime("%d/%m/%Y %H:%M:%S")

            array_consult = []
            index = 0

            for document in array_documents:
                try:
                    
                    name = ""
                    phone = ""
                    guarantee_value = 0
                    released_value = 0
                    status = "Ocorreu uma falha na consulta aos dados do cliente"

                    campaign = db.session.query(TbCampaigns).filter_by(id=new_campaign_id).first()
                    db.session.refresh(campaign)

                    if index == 100:

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

                        campaign.records_consulted = campaign.records_consulted + index

                        db.session.commit()

                    # Vai para a página de dashboard
                    page.get('https://meu.bancomercantil.com.br/simular-proposta')

                    # Seleciona o convênio
                    WebDriverWait(page, TIME_WAIT).until(
                        EC.visibility_of_element_located((By.XPATH, '//*[@id="mat-select-0"]'))
                    ).click()

                    WebDriverWait(page, TIME_WAIT).until(
                        EC.visibility_of_element_located((By.XPATH, '//*[@id="mat-option-6"]/span'))
                    ).click()

                    # Seleciona a instituição
                    WebDriverWait(page, TIME_WAIT).until(
                        EC.visibility_of_element_located((By.XPATH, '//*[@id="mat-select-4"]'))
                    ).click()

                    WebDriverWait(page, TIME_WAIT).until(
                        EC.visibility_of_element_located((By.XPATH, '//*[@id="mat-option-4"]/span'))
                    ).click()

                    # Seleciona a uf
                    WebDriverWait(page, TIME_WAIT).until(
                        EC.visibility_of_element_located((By.XPATH, '//*[@id="mat-select-2"]'))
                    ).click()

                    WebDriverWait(page, TIME_WAIT).until(
                        EC.visibility_of_element_located((By.XPATH, '//*[@id="mat-option-32"]/span'))
                    ).click()

                    # Digita o cpf
                    page.find_element(By.XPATH, '//*[@id="mat-input-1"]').send_keys(document['cpf'])

                    # Clica em consultar
                    WebDriverWait(page, TIME_WAIT).until(
                        EC.visibility_of_element_located((By.XPATH, '/html/body/app-root/div/app-main-layout/main/app-simular-proposta/div/div/mat-card/mat-card-content/div/div[1]/div[3]/button'))
                    ).click()

                    # Clica em operação
                    WebDriverWait(page, TIME_WAIT).until(
                        EC.visibility_of_element_located((By.XPATH, '/html/body/app-root/div/app-main-layout/main/app-simular-proposta/div/div/mat-card/mat-card-content/div[2]/a'))
                    ).click()
                    
                    # Captura o nome
                    name_div = WebDriverWait(page, TIME_WAIT).until(
                        EC.visibility_of_element_located((By.XPATH, '/html/body/app-root/div/app-main-layout/main/app-fgts/div/app-container-header/div/mat-card/mat-card-header/div/mat-card-subtitle/span[1]'))
                    )
                    
                    name = name_div.text

                    # Captura o telefone
                    phone_div = WebDriverWait(page, TIME_WAIT).until(
                        EC.visibility_of_element_located((By.XPATH, '/html/body/app-root/div/app-main-layout/main/app-fgts/div/app-container-header/div/mat-card/mat-card-header/div/mat-card-subtitle/span[3]'))
                    )
                    
                    phone = phone_div.text.replace("Telefone : ", "")

                    # Captura o valor garantia antes da simulação
                    guarantee_value_element = WebDriverWait(page, TIME_WAIT).until(
                        EC.visibility_of_element_located((By.XPATH, '/html/body/app-root/div/app-main-layout/main/app-fgts/div/div/mat-card[2]/mat-card-content/div/ul/li/div/div/strong'))
                    )
  
                    guarantee_value_before_simulation = guarantee_value_element.text
                    pattern_guarantee = guarantee_value_before_simulation.replace(",", ".").replace("R$", "").replace(" ", "")

                    guarantee_value = float(pattern_guarantee)

                    if guarantee_value < 150:
                        status = "Saldo insuficiente para simular"
                        raise Exception(status)

                    # Clica em iniciar
                    WebDriverWait(page, TIME_WAIT).until(
                        EC.visibility_of_element_located((By.XPATH, '/html/body/app-root/div/app-main-layout/main/app-fgts/div/div/mat-card[2]/mat-card-content/div/ul/li/a'))
                    ).click()
  
                    # Clica em simular
                    element = WebDriverWait(page, TIME_WAIT).until(
                        EC.visibility_of_element_located((By.CSS_SELECTOR, 'button.mat-focus-indicator.pcb-button'))
                    )
                    page.execute_script("arguments[0].click();", element)

                    # Pega os valores simulados
                    div_guarantee_value = WebDriverWait(page, TIME_WAIT).until(
                        EC.visibility_of_element_located((By.CSS_SELECTOR, '.taxaMedia strong'))
                    )

                    div_released_value = WebDriverWait(page, TIME_WAIT).until(
                        EC.visibility_of_element_located((By.CLASS_NAME, 'valorLiberado'))
                    )

                    # Obtém o texto dos elementos
                    guarantee_value = div_guarantee_value.text
                    released_value = div_released_value.text

                    # Retorna os valores
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

                    array_consult.append(obj_success)
                except Exception as e:
                    body_text = page.find_element(By.TAG_NAME, "body").text.lower()

                    if "Cliente não autorizou a instituição a realizar a operação fiduciária".lower() in body_text:
                        status = "Cliente não autorizou a instituição a realizar a operação fiduciária"
                    if "Mudanças cadastrais na conta do FGTS foram realizadas, que impedem a constratação.".lower() in body_text:
                        status = "Mudanças cadastrais na conta do FGTS foram realizadas, que impedem a constratação."
                    if "De acordo com as politicas do banco Mercantil, não é possível digitar uma operação para o CPF informado.".lower() in body_text:
                        status = "De acordo com as politicas do banco Mercantil, não é possível digitar uma operação para o CPF informado."

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

                    array_consult.append(obj_error)
                    continue
                finally:
                  index += 1

        except Exception as e:
            instance.status = "LIVRE"
            campaign.status = "CANCELADA"

            db.session.commit()
            
        finally:
            # Final da automação
            campaign = db.session.query(TbCampaigns).filter_by(id=new_campaign_id).first()
            db.session.refresh(campaign)

            if campaign.status != "CANCELADA":
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
                campaign.status = "CONCLUÍDA"
                campaign.records_consulted = campaign.records_consulted + index
                
                instance.status = "LIVRE"

                db.session.commit()
            page.quit()