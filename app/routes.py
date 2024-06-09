from flask import request, jsonify, current_app as app
from app import db
import threading
from app.automation.webdriver_chrome import webdriver_chrome
from app.db.models import TbCampaigns, TbInstances
import json
import uuid

def split_into_parts(array, num_parts):
    part_size = len(array) // num_parts
    parts = [array[i * part_size: (i + 1) * part_size] for i in range(num_parts)]
    parts[-1].extend(array[num_parts * part_size:])

    return parts

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
        threading.Thread(target=webdriver_chrome, args=(app._get_current_object(), instance['user'], instance['password'], instanceSelect.id, split_parts[index], new_campaign.id)).start()

        index += 1
    return jsonify({"message": "Simulação iniciada"}), 200

if __name__ == '__main__':
    app.run(debug=True)
