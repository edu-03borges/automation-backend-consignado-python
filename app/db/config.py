import os
from dotenv import load_dotenv

load_dotenv()

DB_HOST = 'consign-crm.c1mq88q6qt0m.us-east-1.rds.amazonaws.com'
DB_PORT = 5432
DB_USER = 'postgres'
DB_PASSWORD = 'Consign!www'
DB_DATABASE = 'postgres'

class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_DATABASE}')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
