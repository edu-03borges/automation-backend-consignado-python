import uuid
from app import db
from datetime import datetime

class TbCampaigns(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String, nullable=True)
    name = db.Column(db.String, nullable=True)
    company = db.Column(db.String, nullable=True)
    records = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String, nullable=True, default='PROCESSANDO')
    file_data = db.Column(db.String, nullable=True)
    query_data = db.Column(db.String, nullable=True)
    records_consulted = db.Column(db.Integer, nullable=True, default=0)
    count = db.Column(db.Integer, nullable=True, default=0)
    instances = db.Column(db.String, nullable=True)
    created_at = db.Column(db.DateTime, nullable=True, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=True, default=datetime.utcnow, onupdate=datetime.utcnow)

class TbInstances(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String, nullable=True)
    time_logged_in = db.Column(db.Float, nullable=True)
    user = db.Column(db.String, nullable=True, default='LIVRE')
    password = db.Column(db.String, nullable=True)
    status = db.Column(db.String, nullable=True)
    instance = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, nullable=True, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=True, default=datetime.utcnow, onupdate=datetime.utcnow)