import logging
from collections import defaultdict

from llm_api.search.blog_search import BlogPost, BlogSearch
from llm_api.search.vector_blog_search import BlogChunk, VectorBlogSearch
from llm_api.settings.app import get_settings

logger = logging.getLogger(__name__)


def _rrf_score(rank: int, k: int = 60) -> float:
    """Reciprocal Rank Fusion score for a given rank (0-indexed, 0 = best)."""
    return 1.0 / (k + rank + 1)


class HybridSearchResult:
    """A result that carries either a full post (BM25) or a chunk (vector)."""

    def __init__(self, post_slug: str, content: str, title: str = "", tags: list[str] | None = None) -> None:
        self.post_slug = post_slug
        self.content = content
        self.title = title
        self.tags = tags or []


class HybridBlogSearch:
    def __init__(self, bm25_search: BlogSearch, vector_search: VectorBlogSearch) -> None:
        self._bm25 = bm25_search
        self._vector = vector_search

    async def search(self, query: str, top_k: int | None = None, rrf_k: int | None = None) -> list[HybridSearchResult]:
        settings = get_settings()
        top_k = top_k if top_k is not None else settings.hybrid_search_top_k
        rrf_k = rrf_k if rrf_k is not None else settings.rrf_k
        bm25_posts: list[BlogPost] = await self._bm25.search(query)
        vector_chunks: list[BlogChunk] = await self._vector.search(query)

        # Build score map and payload map keyed by stable identifier per passage
        scores: dict[str, float] = defaultdict(float)
        payloads: dict[str, HybridSearchResult] = {}

        for rank, chunk in enumerate(vector_chunks):
            key = f"{chunk.post_slug}::{chunk.content[:40]}"
            scores[key] += _rrf_score(rank, k=rrf_k)
            if key not in payloads:
                payloads[key] = HybridSearchResult(
                    post_slug=chunk.post_slug,
                    content=chunk.content,
                )

        for rank, post in enumerate(bm25_posts):
            key = f"{post.slug}::{post.body[:40]}"
            scores[key] += _rrf_score(rank, k=rrf_k)
            if key not in payloads:
                payloads[key] = HybridSearchResult(
                    post_slug=post.slug,
                    content=post.body,
                    title=post.title,
                    tags=post.tags,
                )

        # Sort by combined RRF score descending, take top-K
        top_keys = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)[:top_k]
        results = [payloads[k] for k in top_keys]

        logger.info(
            f"Hybrid search (RRF): {len(vector_chunks)} vector chunks + "
            f"{len(bm25_posts)} BM25 posts → {len(results)} results for query='{query}'"
        )
        return results
