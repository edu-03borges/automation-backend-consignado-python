from app import create_app
from dotenv import load_dotenv
import os

load_dotenv()

app = create_app()

if __name__ == '__main__':

    port = int(os.getenv('FLASK_RUN_PORT', 5000))
    host = os.getenv('FLASK_RUN_HOST', 'localhost')

    app.run(debug=True, host=host, port=port)
