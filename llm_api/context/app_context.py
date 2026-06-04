import logging
from typing import Optional

from llm_api.databases.relational_database.database_manager import DatabaseEngineManager
from llm_api.databases.vector_database.database_manager import VectorDatabaseEngineManager
from llm_api.instrumentation.setup import InstrumentationSetup
from llm_api.search.blog_posts_indexer import BlogPostsIndexer
from llm_api.search.blog_search import BlogSearch
from llm_api.search.hybrid_blog_search import HybridBlogSearch
from llm_api.search.vector_blog_search import VectorBlogSearch
from llm_api.settings.app import AppSettings

logger = logging.getLogger(__name__)


class AppContext:
    _instance: Optional["AppContext"] = None

    def __init__(self, app_settings: AppSettings, hybrid_search: HybridBlogSearch | None) -> None:
        self._app_settings = app_settings
        self.hybrid_search = hybrid_search

    @classmethod
    async def initialize(cls, app_settings: AppSettings) -> "AppContext":
        if cls._instance is None:
            hybrid_search: HybridBlogSearch | None = None
            try:
                blog_search: BlogSearch | None = await BlogPostsIndexer(DatabaseEngineManager.get_engine()).index()
                vector_search = VectorBlogSearch(
                    engine=VectorDatabaseEngineManager.get_engine(),
                    openai_api_key=app_settings.openai_api_key,
                    ssl_ca_bundle=app_settings.ssl_ca_bundle or None,
                )
                if blog_search is not None:
                    hybrid_search = HybridBlogSearch(bm25_search=blog_search, vector_search=vector_search)
            except Exception:
                logger.exception("Blog search initialization failed — search will be unavailable")

            if app_settings.enable_instrumentation:
                InstrumentationSetup.setup_arize_traces(app_settings)
                InstrumentationSetup.setup_otel(app_settings)

            cls._instance = cls(app_settings, hybrid_search)
        return cls._instance

    @classmethod
    async def close(cls) -> None:
        await DatabaseEngineManager.dispose()
        await VectorDatabaseEngineManager.dispose()

    @classmethod
    def get_instance(cls) -> "AppContext":
        if cls._instance is None:
            raise RuntimeError("AppContext has not been initialized")
        return cls._instance
