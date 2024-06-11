# My API Project

This is a simple API built with Flask and PostgreSQL.

## Dev

1. Create a virtual environment and activate it.
2. Install dependencies:
    ```sh
    pip install -r requirements.txt
    ```
3. Set up the database URL in the `.env` file.
4. Run the application:
    ```sh
    python run.py
    ```

## Generate executable

1. Manual control:
    ```
      pyinstaller --onefile --icon=robot.ico --name="Bank Automation" run.py
    ```
2. Automatic command:
    ```
      pyinstaller '.\Bank Automation.spec'
    ```