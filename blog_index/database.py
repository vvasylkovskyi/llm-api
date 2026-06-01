import asyncpg


def _asyncpg_url(database_url: str) -> str:
    return database_url.replace("postgresql+psycopg://", "postgresql://")


class BlogDatabase:
    def __init__(self, database_url: str) -> None:
        self._url = _asyncpg_url(database_url)
        self._conn: asyncpg.Connection | None = None

    async def connect(self) -> None:
        self._conn = await asyncpg.connect(self._url)

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def __aenter__(self) -> "BlogDatabase":
        await self.connect()
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()

    async def ping(self) -> None:
        assert self._conn is not None, "Not connected — call connect() first"
        await self._conn.execute("SELECT 1")

    async def upsert_post(self, post: dict) -> None:
        assert self._conn is not None, "Not connected — call connect() first"
        await self._conn.execute(
            """
            INSERT INTO blog_posts (slug, title, date, tags, excerpt, body, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, NOW())
            ON CONFLICT (slug) DO UPDATE
              SET title      = EXCLUDED.title,
                  date       = EXCLUDED.date,
                  tags       = EXCLUDED.tags,
                  excerpt    = EXCLUDED.excerpt,
                  body       = EXCLUDED.body,
                  updated_at = NOW()
            """,
            post["slug"],
            post["title"],
            post["date"],
            post["tags"],
            post["excerpt"],
            post["body"],
        )
