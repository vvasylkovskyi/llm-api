import logging
from typing import Optional

from llm_api.databases.relational_database.database_manager import DatabaseEngineManager
from llm_api.instrumentation.setup import InstrumentationSetup
from llm_api.search.blog_posts_indexer import BlogPostsIndexer
from llm_api.search.blog_search import BlogSearch
from llm_api.settings.app import AppSettings

logger = logging.getLogger(__name__)


class AppContext:
    _instance: Optional["AppContext"] = None

    def __init__(self, app_settings: AppSettings, blog_search: BlogSearch | None) -> None:
        self._app_settings = app_settings
        self.blog_search = blog_search

    @classmethod
    async def initialize(cls, app_settings: AppSettings) -> "AppContext":
        if cls._instance is None:
            try:
                blog_search: BlogSearch | None = await BlogPostsIndexer(DatabaseEngineManager.get_engine()).index()
            except Exception:
                logger.exception("Blog post indexing failed — blog search will be unavailable")
                blog_search = None
            if app_settings.enable_instrumentation:
                InstrumentationSetup.setup_arize_traces(app_settings)
                InstrumentationSetup.setup_otel(app_settings)
            cls._instance = cls(app_settings, blog_search)
        return cls._instance

    @classmethod
    async def close(cls) -> None:
        await DatabaseEngineManager.dispose()

    @classmethod
    def get_instance(cls) -> "AppContext":
        if cls._instance is None:
            raise RuntimeError("AppContext has not been initialized")
        return cls._instance
