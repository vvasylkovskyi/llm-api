import argparse
import asyncio
import json
import pathlib

from database import BlogDatabase
from embedder import Embedder
from github_scraper import GitHubBlogScraper, parse_remote_url
from settings import get_settings
from vector_database import VectorDatabase


class IndexRunner:
    def __init__(
        self,
        scraper: GitHubBlogScraper,
        database_url: str | None = None,
        output: pathlib.Path | None = None,
        vector_database_url: str | None = None,
        embedder: Embedder | None = None,
    ) -> None:
        self._scraper = scraper
        self._database_url = database_url
        self._output = output
        self._vector_database_url = vector_database_url
        self._embedder = embedder

    async def run_db(self) -> int:
        assert self._database_url, "database_url is required for DB mode"
        async with BlogDatabase(self._database_url) as db:
            await db.ping()
            print("Database connection OK", flush=True)
            posts = self._scraper.scrape()
            for post in posts:
                await db.upsert_post(post)
                print(f"    Upserted: {post['slug']}", flush=True)

        if self._embedder and self._vector_database_url:
            await self._run_embed(posts)

        return len(posts)

    async def _run_embed(self, posts: list[dict]) -> None:
        assert self._embedder is not None
        assert self._vector_database_url is not None
        async with VectorDatabase(self._vector_database_url) as vdb:
            await vdb.ping()
            print("Vector database connection OK", flush=True)
            for post in posts:
                chunks = self._embedder.embed_post(post)
                await vdb.upsert_chunks(post["slug"], chunks)
                print(f"    Embedded {len(chunks)} chunks: {post['slug']}", flush=True)

    def run_json(self) -> int:
        assert self._output, "output path is required for JSON mode"
        posts = self._scraper.scrape()
        self._output.parent.mkdir(parents=True, exist_ok=True)
        self._output.write_text(json.dumps(posts, indent=2, ensure_ascii=False))
        return len(posts)


def main() -> None:
    settings = get_settings()

    parser = argparse.ArgumentParser(
        description="Build BM25 blog index from MDX files fetched via GitHub API."
    )
    parser.add_argument(
        "--remote-url",
        default=settings.github_remote_url,
        help="GitHub tree URL to the blog content folder (or set GITHUB_REMOTE_URL env var)",
    )
    parser.add_argument(
        "--openai-api-key",
        default=settings.openai_api_key,
        help="OpenAI API key (or set OPENAI_API_KEY env var)",
    )
    parser.add_argument(
        "--db",
        action="store_true",
        default=False,
        help="Upsert posts into Postgres (requires DB credentials via env vars)",
    )
    parser.add_argument(
        "--embed",
        action="store_true",
        default=False,
        help="Chunk and embed posts into pgvector (requires --db and OPENAI_API_KEY env var)",
    )
    args = parser.parse_args()

    if not args.remote_url:
        raise SystemExit("Error: --remote-url argument or GITHUB_REMOTE_URL env var is required.")

    if args.embed and not args.db:
        raise SystemExit("Error: --embed requires --db")

    if args.embed and not settings.openai_api_key:
        raise SystemExit("Error: --embed requires OPENAI_API_KEY env var")

    try:
        parse_remote_url(args.remote_url)
    except ValueError as e:
        raise SystemExit(f"Error: {e}") from e

    scraper = GitHubBlogScraper(
        remote_url=args.remote_url,
        token=settings.github_token or None,
    )

    if args.db:
        embedder = Embedder(api_key=settings.openai_api_key, ssl_ca_bundle=settings.ssl_ca_bundle or None) if args.embed else None
        vector_database_url = settings.vector_database_url if args.embed else None
        runner = IndexRunner(
            scraper,
            database_url=settings.database_url,
            vector_database_url=vector_database_url,
            embedder=embedder,
        )
        total = asyncio.run(runner.run_db())
        print(f"Indexed {total} posts to Postgres" + (" (with embeddings)" if args.embed else ""))
    else:
        runner = IndexRunner(scraper, output=args.output)
        total = runner.run_json()
        print(f"Indexed {total} posts to {args.output}")
