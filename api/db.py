import os

import psycopg2
from dotenv import load_dotenv

# Local development reads api/.env (which is gitignored).
# On Azure App Service the same names come from the app's configuration,
# so no password is ever stored in the code or in the repository.
load_dotenv()


def get_connection():
    return psycopg2.connect(
        host=os.environ["DB_HOST"],
        dbname=os.environ.get("DB_NAME", "soberlink"),
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        port=int(os.environ.get("DB_PORT", "5432")),
        sslmode=os.environ.get("DB_SSLMODE", "require"),
        connect_timeout=10,
    )
