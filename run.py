from app import create_app
from app.ngrok import ngrok
from waitress import serve
from dotenv import load_dotenv
from art import *
from colorama import Fore, Style
import os

load_dotenv()

app = create_app()

if __name__ == '__main__':

    Art2=text2art("BOT",font='block',chr_ignore=True)
    print(Art2)

    print("Server: " + Fore.GREEN + 'Online')

    port = int(os.getenv('FLASK_RUN_PORT', 5000))
    host = os.getenv('FLASK_RUN_HOST', 'localhost')

    # ngrok.ngrok_http(port)

    # Desenvolvimento
    # app.run(debug=False, host=host, port=port)

    # Produção

    serve(app, host=host, port=port)
