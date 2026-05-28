import logging
from functools import lru_cache

from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class AppSettings(BaseSettings):
    model_path: str = ""
    base_url: str = "http://localhost:10000"
    enable_instrumentation: bool = False
    phoenix_collector_endpoint: str = "http://localhost:4318/v1/traces"
    alloy_host: str = "localhost"


@lru_cache
def get_settings():
    return AppSettings()


app_settings = AppSettings()
