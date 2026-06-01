import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from llm_api.search.blog_search import BlogPost, BlogSearch

logger = logging.getLogger(__name__)


class BlogPostsIndexer:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def index(self) -> BlogSearch:
        async with self._engine.connect() as conn:
            result = await conn.execute(
                text("SELECT slug, title, date, tags, excerpt, body FROM blog_posts")
            )
            rows = result.fetchall()
        posts = [
            BlogPost(
                slug=r.slug,
                title=r.title,
                date=str(r.date),
                tags=list(r.tags or []),
                excerpt=r.excerpt or "",
                body=r.body,
            )
            for r in rows
        ]
        return BlogSearch(posts, engine=self._engine)
