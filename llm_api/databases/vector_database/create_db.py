"""Creates the vector database if it does not already exist."""

import sqlalchemy
from sqlalchemy import text

from llm_api.settings.app import get_settings

settings = get_settings()
admin_url = settings.vector_database_url.replace(f"/{settings.db_vector_name}", "/postgres")

engine = sqlalchemy.create_engine(admin_url, isolation_level="AUTOCOMMIT")
with engine.connect() as conn:
    if conn.execute(
        text("SELECT 1 FROM pg_database WHERE datname = :name"),
        {"name": settings.db_vector_name},
    ).fetchone():
        print(f"Database '{settings.db_vector_name}' already exists.")
    else:
        conn.execute(text(f'CREATE DATABASE "{settings.db_vector_name}"'))
        print(f"Database '{settings.db_vector_name}' created.")
