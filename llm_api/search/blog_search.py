import asyncio
import json
import logging
import os
import pathlib
from dataclasses import dataclass

import asyncpg
from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)

BLOG_INDEX_PATH = os.getenv("BLOG_INDEX_PATH", "data/blog_index.json")
BLOG_SEARCH_TOP_K = int(os.getenv("BLOG_SEARCH_TOP_K", "3"))


@dataclass
class BlogPost:
    slug: str
    title: str
    date: str
    tags: list[str]
    excerpt: str
    body: str


class BlogSearch:
    def __init__(self) -> None:
        self._posts: list[BlogPost] | None = None
        self._bm25: BM25Okapi | None = None

    async def _load_from_db(self) -> None:
        """Load all blog posts from Postgres."""
        database_url = os.environ["DATABASE_URL"]
        # asyncpg requires plain postgresql:// scheme — strip +psycopg driver suffix if present
        asyncpg_url = database_url.replace("postgresql+psycopg://", "postgresql://")
        conn = await asyncpg.connect(asyncpg_url)
        try:
            rows = await conn.fetch(
                "SELECT slug, title, date, tags, excerpt, body FROM blog_posts"
            )
            self._posts = [
                BlogPost(
                    slug=r["slug"],
                    title=r["title"],
                    date=str(r["date"]),
                    tags=list(r["tags"] or []),
                    excerpt=r["excerpt"] or "",
                    body=r["body"],
                )
                for r in rows
            ]
        finally:
            await conn.close()

    def _load(self, index_path: str = BLOG_INDEX_PATH) -> None:
        db_url = os.environ.get("DATABASE_URL")
        if db_url:
            asyncio.run(self._load_from_db())
        else:
            path = pathlib.Path(index_path)
            if not path.exists():
                logger.warning(f"Blog index not found at {path}. Search will return no results.")
                self._posts = []
                self._bm25 = None
                return
            raw = json.loads(path.read_text())
            self._posts = [BlogPost(**p) for p in raw]

        corpus = [
            (p.title + " " + " ".join(p.tags) + " " + p.body).lower().split()
            for p in self._posts
        ]
        self._bm25 = BM25Okapi(corpus)
        logger.info(f"Blog search index loaded: {len(self._posts)} posts")

    def search(self, query: str, top_k: int = BLOG_SEARCH_TOP_K) -> list[BlogPost]:
        if self._posts is None:
            self._load()
        if not self._bm25 or not self._posts:
            return []
        scores = self._bm25.get_scores(query.lower().split())
        ranked = sorted(zip(scores, self._posts), key=lambda x: x[0], reverse=True)
        return [post for score, post in ranked[:top_k] if score > 0]
