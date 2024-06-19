from flask import request, jsonify, current_app as app
import threading
from app.automation.webdriver_chrome_mercantil import webdriver_chrome_mercantil
from app.db.models import TbCampaigns, TbInstances
from app.utils import split_into_parts, find_differences
from app import db
import json
import uuid
import time

@app.route('/start', methods=['POST'])
def start_simulation():

    data = request.json

    required_fields = ['continue']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400
    
    array_response = []
    campaign = TbCampaigns()

    if data['continue']:
      campaign = db.session.query(TbCampaigns).filter_by(uuid=data['uuid']).first()
      db.session.refresh(campaign)
    
      campaign.count = 0
      db.session.commit()

      array_response = find_differences(campaign.file_data, campaign.query_data)
    else:
      array_response = json.loads(data['file_data'])

      new_campaign = TbCampaigns(
          uuid=uuid.uuid4(),
          name=data['name'],
          company=data['company'],
          records=data['records'],
          file_data=data['file_data'],
          instances=json.dumps(data['instances']),
          count=0
      )

      db.session.add(new_campaign)

      db.session.commit()

      campaign = new_campaign
    
    split_parts = split_into_parts(array_response, len(campaign.instances))

    index = 0

    for instance in campaign.instances:

        instanceSelect = db.session.query(TbInstances).filter_by(id=instance['id']).first()

        instanceSelect.status = "EM USO"
        db.session.commit()
        
        time.sleep(0.1)
        # Inicia a função em um novo thread
        threading.Thread(target=webdriver_chrome_mercantil, args=(app._get_current_object(), instance['user'], instance['password'], campaign.company, instanceSelect.id, split_parts[index], campaign.id)).start()

        index += 1
    return jsonify({"message": "Simulação iniciada"}), 200

if __name__ == '__main__':
    app.run(debug=True)
