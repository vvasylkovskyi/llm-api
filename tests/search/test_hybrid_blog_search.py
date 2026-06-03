"""Unit tests for HybridBlogSearch with RRF fusion."""
import asyncio

import pytest

from llm_api.search.hybrid_blog_search import HybridBlogSearch, _rrf_score
from llm_api.search.blog_search import BlogPost
from llm_api.search.vector_blog_search import BlogChunk


def make_post(slug: str, body: str = "", title: str = "", tags: list[str] | None = None) -> BlogPost:
    return BlogPost(slug=slug, title=title or slug, date="2024-01-01", tags=tags or [], excerpt="", body=body or slug)


def make_chunk(post_slug: str, content: str) -> BlogChunk:
    return BlogChunk(post_slug=post_slug, content=content)


class MockBlogSearch:
    def __init__(self, posts: list[BlogPost]) -> None:
        self._posts = posts

    async def search(self, query: str, **kwargs: object) -> list[BlogPost]:
        return self._posts


class MockVectorSearch:
    def __init__(self, chunks: list[BlogChunk]) -> None:
        self._chunks = chunks

    async def search(self, query: str, **kwargs: object) -> list[BlogChunk]:
        return self._chunks


def test_rrf_score_decreases_with_rank() -> None:
    """Higher rank (worse position) should produce lower RRF score."""
    assert _rrf_score(0) > _rrf_score(1) > _rrf_score(2)


def test_rrf_score_formula() -> None:
    """RRF score should be 1/(k + rank + 1)."""
    assert _rrf_score(rank=0, k=60) == pytest.approx(1.0 / 61)
    assert _rrf_score(rank=1, k=60) == pytest.approx(1.0 / 62)
    assert _rrf_score(rank=0, k=10) == pytest.approx(1.0 / 11)


def test_rrf_promotes_overlapping_results() -> None:
    """
    An item ranked by both vector and BM25 retrievers should outscore
    an item ranked only by one retriever.

    Setup:
    - "monitoring-post" is ranked 0 by vector (best chunk) and rank 1 by BM25
    - "grafana-post" is ranked 0 by BM25 only (not returned by vector)

    Expected: "monitoring-post" total RRF score > "grafana-post" score
    because it accumulates scores from both lists.
    """
    monitoring_body = "Setting up monitoring with Grafana and Prometheus on Kubernetes"
    grafana_body = "Grafana dashboard configuration and alert management best practices"

    vector_chunks = [
        make_chunk("monitoring-post", monitoring_body),  # rank 0 in vector
    ]
    bm25_posts = [
        make_post("grafana-post", grafana_body),         # rank 0 in BM25
        make_post("monitoring-post", monitoring_body),   # rank 1 in BM25
    ]

    bm25_search = MockBlogSearch(bm25_posts)
    vector_search = MockVectorSearch(vector_chunks)
    hybrid = HybridBlogSearch(bm25_search=bm25_search, vector_search=vector_search)  # type: ignore[arg-type]

    results = asyncio.get_event_loop().run_until_complete(
        hybrid.search("monitoring grafana", top_k=5, rrf_k=60)
    )

    assert len(results) == 2
    slugs = [r.post_slug for r in results]
    # monitoring-post should come first because it appears in both lists
    assert slugs[0] == "monitoring-post", (
        f"Expected 'monitoring-post' first (ranked by both retrievers), got {slugs}"
    )


def test_empty_bm25_returns_vector_results() -> None:
    """When BM25 returns nothing, vector results should still be returned."""
    vector_chunks = [
        make_chunk("post-a", "content about AI agents"),
        make_chunk("post-b", "content about LLMs"),
    ]

    bm25_search = MockBlogSearch([])
    vector_search = MockVectorSearch(vector_chunks)
    hybrid = HybridBlogSearch(bm25_search=bm25_search, vector_search=vector_search)  # type: ignore[arg-type]

    results = asyncio.get_event_loop().run_until_complete(
        hybrid.search("AI agents", top_k=5, rrf_k=60)
    )

    assert len(results) == 2
    slugs = {r.post_slug for r in results}
    assert slugs == {"post-a", "post-b"}


def test_empty_vector_returns_bm25_results() -> None:
    """When vector search returns nothing, BM25 results should still be returned."""
    bm25_posts = [
        make_post("post-a", "content about kubernetes deployment"),
    ]

    bm25_search = MockBlogSearch(bm25_posts)
    vector_search = MockVectorSearch([])
    hybrid = HybridBlogSearch(bm25_search=bm25_search, vector_search=vector_search)  # type: ignore[arg-type]

    results = asyncio.get_event_loop().run_until_complete(
        hybrid.search("kubernetes", top_k=5, rrf_k=60)
    )

    assert len(results) == 1
    assert results[0].post_slug == "post-a"


def test_top_k_limits_results() -> None:
    """top_k should cap the number of results returned."""
    vector_chunks = [make_chunk(f"post-{i}", f"content {i}") for i in range(5)]
    bm25_posts = [make_post(f"bm25-{i}", f"body {i}") for i in range(5)]

    bm25_search = MockBlogSearch(bm25_posts)
    vector_search = MockVectorSearch(vector_chunks)
    hybrid = HybridBlogSearch(bm25_search=bm25_search, vector_search=vector_search)  # type: ignore[arg-type]

    results = asyncio.get_event_loop().run_until_complete(
        hybrid.search("content", top_k=3, rrf_k=60)
    )

    assert len(results) == 3
