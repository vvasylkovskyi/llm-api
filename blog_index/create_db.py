"""Creates the viktor_blog database if it does not already exist."""
import os
from urllib.parse import urlparse, urlunparse

import psycopg

DATABASE_URL = os.environ.get("DATABASE_URL", "")
DB_NAME = os.environ.get("DB_NAME", "viktor_blog")

if not DATABASE_URL:
    raise SystemExit("DATABASE_URL environment variable must be set.")

# Replace the database name in the URL with 'postgres' to connect as admin
parsed = urlparse(DATABASE_URL)
admin_parsed = parsed._replace(
    scheme="postgresql",  # psycopg3 uses plain postgresql://
    path="/postgres",
)
admin_url = urlunparse(admin_parsed)

with psycopg.connect(admin_url, autocommit=True) as conn:
    exists = conn.execute(
        "SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,)
    ).fetchone()
    if exists:
        print(f"Database '{DB_NAME}' already exists.")
    else:
        conn.execute(f'CREATE DATABASE "{DB_NAME}"')
        print(f"Database '{DB_NAME}' created.")
