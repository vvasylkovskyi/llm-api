"""Creates the application database if it does not already exist."""

import sqlalchemy
from sqlalchemy import text

from llm_api.settings.app import get_settings

settings = get_settings()
admin_url = settings.database_url.replace(f"/{settings.db_name}", "/postgres")

engine = sqlalchemy.create_engine(admin_url, isolation_level="AUTOCOMMIT")
with engine.connect() as conn:
    if conn.execute(
        text("SELECT 1 FROM pg_database WHERE datname = :name"),
        {"name": settings.db_name},
    ).fetchone():
        print(f"Database '{settings.db_name}' already exists.")
    else:
        conn.execute(text(f'CREATE DATABASE "{settings.db_name}"'))
        print(f"Database '{settings.db_name}' created.")
