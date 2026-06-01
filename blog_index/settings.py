from functools import lru_cache

from pydantic import computed_field
from pydantic_settings import BaseSettings


class BlogIndexSettings(BaseSettings):
    db_user: str = "postgres"
    db_password: str = "secret123"
    db_name: str = "postgres"
    db_host: str = "localhost"
    db_port: str = "5432"
    github_token: str = ""
    github_remote_url: str = ""

    @computed_field
    @property
    def database_url(self) -> str:
        return (
            f"postgresql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


@lru_cache
def get_settings() -> BlogIndexSettings:
    return BlogIndexSettings()
