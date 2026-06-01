"""Creates the application database if it does not already exist."""


import sqlalchemy
from sqlalchemy import text

from llm_api.database.config import DATABASE_URL, DB_NAME

# Connect to the default 'postgres' database to issue CREATE DATABASE
admin_url = DATABASE_URL.replace(f"/{DB_NAME}", "/postgres")

engine = sqlalchemy.create_engine(admin_url, isolation_level="AUTOCOMMIT")
with engine.connect() as conn:
    if exists := conn.execute(
        text("SELECT 1 FROM pg_database WHERE datname = :name"),
        {"name": DB_NAME},
    ).fetchone():
        print(f"Database '{DB_NAME}' already exists.")
    else:
        conn.execute(text(f'CREATE DATABASE "{DB_NAME}"'))
        print(f"Database '{DB_NAME}' created.")
