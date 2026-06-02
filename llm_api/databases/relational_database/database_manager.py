from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from llm_api.settings.app import get_settings


class DatabaseEngineManager:
    _engine: AsyncEngine = create_async_engine(get_settings().database_url, pool_pre_ping=True)

    @classmethod
    def get_engine(cls) -> AsyncEngine:
        return cls._engine

    @classmethod
    async def dispose(cls) -> None:
        await cls._engine.dispose()

    @classmethod
    async def ping(cls) -> bool:
        async with cls._engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            return result.scalar() == 1
