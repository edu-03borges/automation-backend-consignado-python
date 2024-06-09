import os
from dotenv import load_dotenv

load_dotenv() 

class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'postgresql://postgres:1234@localhost/sys-pupib')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
