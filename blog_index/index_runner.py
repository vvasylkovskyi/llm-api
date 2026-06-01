import argparse
import asyncio
import json
import pathlib

from database import BlogDatabase
from github_scraper import GitHubBlogScraper, parse_remote_url
from settings import get_settings


class IndexRunner:
    def __init__(
        self,
        scraper: GitHubBlogScraper,
        database_url: str | None = None,
        output: pathlib.Path | None = None,
    ) -> None:
        self._scraper = scraper
        self._database_url = database_url
        self._output = output

    async def run_db(self) -> int:
        assert self._database_url, "database_url is required for DB mode"
        async with BlogDatabase(self._database_url) as db:
            await db.ping()
            print("Database connection OK", flush=True)
            posts = self._scraper.scrape()
            for post in posts:
                await db.upsert_post(post)
                print(f"    Upserted: {post['slug']}", flush=True)
        return len(posts)

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
        "--db",
        action="store_true",
        default=False,
        help="Upsert posts into Postgres (requires DB credentials via env vars)",
    )
    args = parser.parse_args()

    if not args.remote_url:
        raise SystemExit("Error: --remote-url argument or GITHUB_REMOTE_URL env var is required.")

    try:
        parse_remote_url(args.remote_url)
    except ValueError as e:
        raise SystemExit(f"Error: {e}") from e

    scraper = GitHubBlogScraper(
        remote_url=args.remote_url,
        token=settings.github_token or None,
    )

    if args.db:
        runner = IndexRunner(scraper, database_url=settings.database_url)
        total = asyncio.run(runner.run_db())
        print(f"Indexed {total} posts to Postgres")
    else:
        runner = IndexRunner(scraper, output=args.output)
        total = runner.run_json()
        print(f"Indexed {total} posts to {args.output}")
