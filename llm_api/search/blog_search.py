import logging
import os
from pydantic import BaseModel
from rank_bm25 import BM25Okapi
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)

BLOG_SEARCH_TOP_K = int(os.getenv("BLOG_SEARCH_TOP_K", "3"))


class BlogPost(BaseModel):
    slug: str
    title: str
    date: str
    tags: list[str]
    excerpt: str
    body: str


class BlogSearch:
    def __init__(self, posts: list[BlogPost], engine: AsyncEngine | None = None) -> None:
        self._engine = engine
        self._rebuild(posts)

    def _rebuild(self, posts: list[BlogPost]) -> None:
        self._posts = posts
        if posts:
            corpus = [
                (f"{p.title} " + " ".join(p.tags) + " " + p.body).lower().split()
                for p in posts
            ]
            self._bm25: BM25Okapi | None = BM25Okapi(corpus)
        else:
            self._bm25 = None
        logger.info(f"Blog search index loaded: {len(posts)} posts")

    async def _reindex(self) -> None:
        if self._engine is None:
            return
        from llm_api.search.blog_posts_indexer import BlogPostsIndexer
        logger.info("No posts in index — retrying indexing from database")
        try:
            refreshed = await BlogPostsIndexer(self._engine).index()
            self._rebuild(refreshed._posts)
        except Exception:
            logger.exception("Re-index attempt failed")

    async def search(self, query: str, top_k: int = BLOG_SEARCH_TOP_K) -> list[BlogPost]:
        if not self._posts:
            await self._reindex()
        if not self._bm25 or not self._posts:
            return []
        scores = self._bm25.get_scores(query.lower().split())
        ranked = sorted(zip(scores, self._posts), key=lambda x: x[0], reverse=True)
        return [post for score, post in ranked[:top_k] if score > 0]
