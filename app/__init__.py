from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from app.db.config import Config
from flask_cors import CORS
from app.ngrok import ngrok

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    CORS(app, resources={r"/start": {"origins": "*"}})
    app.config.from_object(Config)
    db.init_app(app)

    public_url = ngrok.ngrok_http(5000)
    print(public_url)

    with app.app_context():
        from app import routes
        from app.db.models import TbCompanys

        company = db.session.query(TbCompanys).filter_by(code=1).first()
        db.session.refresh(company)

        company.public_url = public_url
        
        db.session.commit()

        db.create_all()
        
    return app
