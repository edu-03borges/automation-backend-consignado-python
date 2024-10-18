from flask import request, jsonify, current_app as app
import threading
from app.automation.webdriver_chrome_mercantil import webdriver_chrome_mercantil
from app.automation.webdriver_chrome_lotus import webdriver_chrome_lotus
from app.db.models import TbCampaigns, TbInstances, TbCompanies
from app.utils import split_into_parts, find_differences
from app import db
import json
import uuid

@app.before_request
def before_request():
    """Abre a sessão do banco de dados antes de cada requisição."""
    db.session()

@app.teardown_request
def teardown_request(exception=None):
    """Fecha a sessão do banco de dados após cada requisição."""
    db.session.remove()

@app.route('/start', methods=['POST'])
def start_simulation():
    try:
        data = request.json

        # Validação de campos obrigatórios
        required_fields = ['continue', 'instances']
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Missing required fields"}), 400
        
        # Obtenção da empresa associada ao usuário
        company = db.session.query(TbCompanies).filter_by(iduser=data['idUser']).first()

        if not company:
            return jsonify({"error": "Company not found"}), 404

        # Tratamento de campanha existente ou nova
        campaign, array_response = handle_campaign(data, company)

        # Dividir os dados em partes para cada instância
        split_parts = split_into_parts(array_response, len(data['instances']))

        # Iniciar threads para cada instância
        start_threads(data['instances'], company, campaign, split_parts)

        return jsonify({"message": "Simulação iniciada"}), 200

    except Exception as e:
        app.logger.error(f"Erro ao iniciar a simulação: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

def handle_campaign(data, company):
    """Trata a lógica de campanha existente ou nova."""

    if data['continue']:
        # Continuação de uma campanha existente
        campaign = db.session.query(TbCampaigns).filter_by(uuid=data['uuid']).first()
        if not campaign:
            raise ValueError("Campaign not found")
        campaign.status = "PROCESSANDO"
        db.session.commit()
        array_response = find_differences(campaign.file_data, campaign.query_data)
    else:
        # Criação de uma nova campanha
        array_response = json.loads(data['file_data'])
        campaign = TbCampaigns(
            uuid=uuid.uuid4(),
            iduser=data['idUser'],
            name=data['name'],
            records=data['records'],
            file_data=data['file_data'],
            query_data="[]",
        )
        db.session.add(campaign)
        db.session.commit()
    return campaign, array_response

def start_threads(instances, company, campaign, split_parts):
    """Inicia threads para cada instância de simulação."""

    for index, instance in enumerate(instances):
        instance_select = db.session.query(TbInstances).filter_by(uuid=instance['uuid']).first()
        if not instance_select:
            raise ValueError(f"Instance {instance['uuid']} not found")
        instance_select.status = "EM USO"
        db.session.commit()

        threading.Thread(
            target=webdriver_chrome_lotus,
            args=(
                app._get_current_object(),
                instance['user'],
                instance['password'],
                company.name,
                instance_select.id,
                campaign.id,
                split_parts[index],
            )
        ).start()

if __name__ == '__main__':
    app.run(debug=True)
