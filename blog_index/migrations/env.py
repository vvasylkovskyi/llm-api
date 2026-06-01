import os
from logging.config import fileConfig
from urllib.parse import urlparse, urlunparse

from alembic import context
from sqlalchemy import MetaData, engine_from_config, pool

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# No SQLModel — blog_index migrations are written as raw SQL via op.*
target_metadata = MetaData()

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL environment variable must be set to run blog index migrations.\n"
        "Example: DATABASE_URL=postgresql://postgres:pass@host:5432/viktor_blog"
    )


def get_psycopg_url(url: str) -> str:
    """Ensure URL uses the postgresql+psycopg:// scheme that SQLAlchemy+psycopg3 requires.

    Alembic uses SQLAlchemy under the hood. asyncpg (used by the scraper) needs plain
    postgresql://, but Alembic needs postgresql+psycopg://.
    """
    parsed = urlparse(url)
    if parsed.scheme == "postgresql":
        parsed = parsed._replace(scheme="postgresql+psycopg")
    return urlunparse(parsed)


SQLALCHEMY_URL = get_psycopg_url(DATABASE_URL)


def run_migrations_offline() -> None:
    context.configure(
        url=SQLALCHEMY_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        url=SQLALCHEMY_URL,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
