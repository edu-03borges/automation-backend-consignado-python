from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from app.db.config import Config
from flask_cors import CORS

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    CORS(app, resources={r"/start": {"origins": "*"}})
    app.config.from_object(Config)
    db.init_app(app)

    with app.app_context():
        from app import routes
        db.create_all()

    return app
