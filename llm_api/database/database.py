from sqlalchemy import text
from sqlmodel import create_engine

from llm_api.database.config import DATABASE_URL

print("DATABASE_URL:", DATABASE_URL)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)


def ping_db() -> bool:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        return result.scalar() == 1
