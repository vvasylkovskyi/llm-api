import logging
from functools import lru_cache

from pydantic import computed_field
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class AppSettings(BaseSettings):
    model_path: str = ""
    base_url: str = "http://localhost:10000"
    enable_instrumentation: bool = False
    phoenix_collector_endpoint: str = "http://localhost:4318/v1/traces"
    alloy_host: str = "localhost"
    db_user: str = "postgres"
    db_password: str = "secret123"
    db_name: str = "postgres"
    db_host: str = "localhost"
    db_port: str = "5432"
    db_vector_user: str = "pgvector"
    db_vector_password: str = "Test1234"
    db_vector_name: str = "mydb"
    db_vector_host: str = "localhost"
    db_vector_port: str = "5433"

    @computed_field
    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @computed_field
    @property
    def vector_database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.db_vector_user}:{self.db_vector_password}"
            f"@{self.db_vector_host}:{self.db_vector_port}/{self.db_vector_name}"
        )


@lru_cache
def get_settings():
    return AppSettings()
