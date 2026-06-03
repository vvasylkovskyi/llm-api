import logging
import os

from openai import OpenAI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)

VECTOR_SEARCH_TOP_K = int(os.getenv("VECTOR_SEARCH_TOP_K", "5"))
EMBEDDING_MODEL = "text-embedding-3-small"


class BlogChunk:
    def __init__(self, post_slug: str, content: str) -> None:
        self.post_slug = post_slug
        self.content = content


class VectorBlogSearch:
    def __init__(self, engine: AsyncEngine, openai_api_key: str, ssl_ca_bundle: str | None = None) -> None:
        self._engine = engine
        import httpx
        http_client = httpx.Client(verify=ssl_ca_bundle) if ssl_ca_bundle else None
        self._openai = OpenAI(api_key=openai_api_key, http_client=http_client)

    def _embed(self, text: str) -> list[float]:
        response = self._openai.embeddings.create(model=EMBEDDING_MODEL, input=text)
        return response.data[0].embedding

    async def search(self, query: str, top_k: int = VECTOR_SEARCH_TOP_K) -> list[BlogChunk]:
        try:
            query_vector = self._embed(query)
        except Exception:
            logger.exception("Failed to embed query — vector search skipped")
            return []

        vector_str = "[" + ",".join(str(x) for x in query_vector) + "]"

        async with self._engine.connect() as conn:
            result = await conn.execute(
                text("""
                    SELECT post_slug, content
                    FROM blog_chunks
                    ORDER BY embedding <=> CAST(:vec AS vector)
                    LIMIT :k
                """),
                {"vec": vector_str, "k": top_k},
            )
            rows = result.fetchall()

        # Rows are ordered by ascending distance (rank 0 = best match)
        return [BlogChunk(post_slug=row.post_slug, content=row.content) for row in rows]
