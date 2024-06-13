from flask import request, jsonify, current_app as app
import threading
from app.automation.webdriver_chrome_mercantil import webdriver_chrome_mercantil
from app.db.models import TbCampaigns, TbInstances
from app.utils import split_into_parts
from app import db
import json
import uuid
import time

@app.route('/start', methods=['POST'])
def start_simulation():

    data = request.json
    
    required_fields = ['name', 'company', 'records', 'file_data']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400
    
    new_campaign = TbCampaigns(
        uuid=uuid.uuid4(),
        name=data['name'],
        company=data['company'],
        records=data['records'],
        file_data=data['file_data']
    )

    db.session.add(new_campaign)

    db.session.commit()

    split_parts = split_into_parts(json.loads(data['file_data']), len(data['instances']))

    index = 0

    for instance in data['instances']:

        instanceSelect = db.session.query(TbInstances).filter_by(id=instance['id']).first()

        instanceSelect.status = "EM USO"
        db.session.commit()
        
        # Inicia a função em um novo thread
        time.sleep(2)
        threading.Thread(target=webdriver_chrome_mercantil, args=(app._get_current_object(), instance['user'], instance['password'], data['company'], instanceSelect.id, split_parts[index], new_campaign.id)).start()

        index += 1
    return jsonify({"message": "Simulação iniciada"}), 200

if __name__ == '__main__':
    app.run(debug=True)
