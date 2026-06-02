import asyncpg


class VectorDatabase:
    def __init__(self, database_url: str) -> None:
        self._url = database_url
        self._conn: asyncpg.Connection | None = None

    async def connect(self) -> None:
        self._conn = await asyncpg.connect(self._url)

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def __aenter__(self) -> "VectorDatabase":
        await self.connect()
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()

    async def ping(self) -> None:
        assert self._conn is not None, "Not connected"
        await self._conn.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector'")

    async def upsert_chunks(self, post_slug: str, chunks: list[tuple[int, str, list[float]]]) -> None:
        assert self._conn is not None, "Not connected"
        for chunk_index, content, embedding in chunks:
            await self._conn.execute(
                """
                INSERT INTO blog_chunks (post_slug, chunk_index, content, embedding, updated_at)
                VALUES ($1, $2, $3, $4::vector, NOW())
                ON CONFLICT (post_slug, chunk_index) DO UPDATE
                  SET content    = EXCLUDED.content,
                      embedding  = EXCLUDED.embedding,
                      updated_at = NOW()
                """,
                post_slug,
                chunk_index,
                content,
                str(embedding),
            )
