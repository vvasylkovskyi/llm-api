import logging
from typing import Optional

from fastapi import FastAPI

from llm_api.settings.app import AppSettings
from llm_api.instrumentation.setup import setup_instrumentation

logger = logging.getLogger(__name__)


class AppContext:
    _instance: Optional["AppContext"] = None

    def __init__(self, app_settings: AppSettings) -> None:
        self._app_settings = app_settings

    @classmethod
    def initialize(cls, app_settings: AppSettings) -> "AppContext":
        if cls._instance is None:
            cls._instance = cls(app_settings)
            if app_settings.enable_instrumentation:
                setup_instrumentation(app_settings)
        return cls._instance

    @classmethod
    def get_instance(cls) -> "AppContext":
        """Get the singleton instance of AppContext.

        Returns:
            The singleton AppContext instance

        Raises:
            RuntimeError: If the AppContext has not been initialized
        """
        if cls._instance is None:
            raise RuntimeError("AppContext has not been initialized")
        return cls._instance
