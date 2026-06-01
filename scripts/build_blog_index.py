#!/usr/bin/env python3
"""Build a JSON search index from MDX blog post files fetched via GitHub API.

Usage:
    # Write to JSON file (local dev)
    uv run python scripts/build_blog_index.py \
        --remote-url https://github.com/owner/repo/tree/main/content/blog \
        --output data/blog_index.json

    # Write to Postgres (CI / production)
    DATABASE_URL=postgresql://postgres:pass@host:5432/mydb \
    uv run python scripts/build_blog_index.py \
        --remote-url https://github.com/owner/repo/tree/main/content/blog \
        --db
"""

import argparse
import asyncio
import base64
import json
import os
import pathlib
import re
import time
from urllib.parse import urlparse

import asyncpg
import frontmatter
import httpx

MIN_REMAINING = 10
MAX_RETRIES = 3


def strip_images(text: str) -> str:
    """Remove image markdown and JSX image tags from body text."""
    # Standard markdown images: ![alt text](path)
    text = re.sub(r"!\[.*?\]\(.*?\)", "", text)
    # MDX JSX self-closing image tags: <Image .../> and <img .../>
    text = re.sub(r"<[Ii]mage\s[^>]*/?>", "", text, flags=re.DOTALL)
    text = re.sub(r"<img\s[^>]*/?>", "", text, flags=re.DOTALL)
    return text


def parse_remote_url(url: str) -> tuple[str, str, str, str]:
    """Return (owner, repo, ref, path) from a GitHub tree URL.

    Input:  https://github.com/vvasylkovskyi/vvasylkovskyi.github.io/tree/main/content/blog
    Output: ('vvasylkovskyi', 'vvasylkovskyi.github.io', 'main', 'content/blog')
    """
    parts = urlparse(url).path.strip("/").split("/")
    if len(parts) < 4 or parts[2] != "tree":
        raise ValueError(
            f"Expected a GitHub tree URL (https://github.com/owner/repo/tree/ref/path), got: {url}"
        )
    owner = parts[0]
    repo = parts[1]
    ref = parts[3]
    path = "/".join(parts[4:])
    return owner, repo, ref, path


def github_get(client: httpx.Client, url: str, headers: dict | None = None) -> httpx.Response:
    """GET with rate-limit awareness and retry on 403/429."""
    for attempt in range(MAX_RETRIES):
        response = client.get(url, headers=headers or {})

        # Check rate limit headers after every response
        remaining = int(response.headers.get("X-RateLimit-Remaining", 9999))
        reset_at = int(response.headers.get("X-RateLimit-Reset", 0))
        print(f"  [rate limit] {remaining} requests remaining", flush=True)

        if response.status_code in (403, 429):
            retry_after = int(response.headers.get("Retry-After", 60))
            print(f"  Rate limited. Waiting {retry_after}s (attempt {attempt + 1}/{MAX_RETRIES})")
            time.sleep(retry_after)
            continue

        response.raise_for_status()

        if remaining <= MIN_REMAINING:
            wait = max(0, reset_at - time.time()) + 1
            print(f"  Rate limit low ({remaining} remaining). Sleeping {wait:.0f}s until reset.")
            time.sleep(wait)

        return response

    raise RuntimeError(f"Failed after {MAX_RETRIES} retries: {url}")


def list_mdx_files(
    client: httpx.Client, owner: str, repo: str, ref: str, path: str, auth_headers: dict
) -> list[dict]:
    """Return list of {path, sha} for all .mdx files under path using Git Trees API."""
    url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{ref}?recursive=1"
    response = github_get(client, url, auth_headers)
    tree = response.json()["tree"]

    prefix = path.rstrip("/") + "/"
    return [
        item
        for item in tree
        if item["type"] == "blob" and item["path"].startswith(prefix) and item["path"].endswith(".mdx")
    ]


def fetch_file(
    client: httpx.Client,
    owner: str,
    repo: str,
    ref: str,
    file_path: str,
    auth_headers: dict,
    etag_cache: dict,
) -> tuple[str, str | None]:
    """Fetch file content. Returns (content, new_etag). Uses ETag cache for 304 responses."""
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}?ref={ref}"

    headers = dict(auth_headers)
    cached = etag_cache.get(file_path)
    if cached and "etag" in cached:
        headers["If-None-Match"] = cached["etag"]

    response = client.get(url, headers=headers)

    # Check rate limit even for 304
    remaining = int(response.headers.get("X-RateLimit-Remaining", 9999))
    reset_at = int(response.headers.get("X-RateLimit-Reset", 0))
    print(f"  [rate limit] {remaining} requests remaining", flush=True)

    if response.status_code == 304:
        # Not modified — use cached content, does not count against rate limit
        print(f"    304 cached: {file_path}", flush=True)
        return cached["content"], None

    if response.status_code in (403, 429):
        # Fall back to github_get for retry logic
        response = github_get(client, url, headers)
    else:
        response.raise_for_status()
        if remaining <= MIN_REMAINING:
            wait = max(0, reset_at - time.time()) + 1
            print(f"  Rate limit low ({remaining} remaining). Sleeping {wait:.0f}s until reset.")
            time.sleep(wait)

    data = response.json()
    content = base64.b64decode(data["content"]).decode("utf-8")
    new_etag = response.headers.get("ETag")
    return content, new_etag


async def upsert_post(conn: asyncpg.Connection, post: dict) -> None:
    """Upsert a single blog post into the blog_posts table."""
    await conn.execute(
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


def get_asyncpg_url(database_url: str) -> str:
    """Convert a SQLAlchemy DATABASE_URL to a plain asyncpg connection string.

    Strips the '+psycopg' driver suffix if present so asyncpg can use it.
    e.g. 'postgresql+psycopg://...' -> 'postgresql://...'
    """
    return database_url.replace("postgresql+psycopg://", "postgresql://")


async def index_posts_to_db(
    remote_url: str, database_url: str, etag_cache_path: pathlib.Path
) -> tuple[int, int, int]:
    """Download blog posts from GitHub and upsert them into Postgres."""
    owner, repo, ref, path = parse_remote_url(remote_url)

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("Warning: GITHUB_TOKEN not set. Using unauthenticated requests (60/hour limit).")

    auth_headers: dict[str, str] = {"Authorization": f"Bearer {token}"} if token else {}
    auth_headers["Accept"] = "application/vnd.github+json"
    auth_headers["X-GitHub-Api-Version"] = "2022-11-28"

    # Load ETag cache
    etag_cache: dict = {}
    if etag_cache_path.exists():
        etag_cache = json.loads(etag_cache_path.read_text())

    asyncpg_url = get_asyncpg_url(database_url)
    conn = await asyncpg.connect(asyncpg_url)
    try:
        with httpx.Client() as client:
            print(f"Listing .mdx files in {owner}/{repo}/{path} @ {ref}...")
            files = list_mdx_files(client, owner, repo, ref, path, auth_headers)
            print(f"Found {len(files)} .mdx files")

            total = 0
            fetched = 0
            cached_count = 0

            for item in files:
                file_path = item["path"]
                slug = pathlib.Path(file_path).stem
                print(f"  Fetching {file_path}...", flush=True)

                content, new_etag = fetch_file(
                    client, owner, repo, ref, file_path, auth_headers, etag_cache
                )

                if new_etag:
                    etag_cache[file_path] = {"etag": new_etag, "content": content}
                    fetched += 1
                else:
                    cached_count += 1

                # Parse with python-frontmatter
                post = frontmatter.loads(content)
                body = strip_images(post.content)

                post_dict = {
                    "slug": slug,
                    "title": str(post.metadata.get("title", slug)),
                    "date": str(post.metadata.get("date", "")),
                    "tags": list(post.metadata.get("tags", [])),
                    "excerpt": body[:300].strip(),
                    "body": body,
                }

                await upsert_post(conn, post_dict)
                print(f"    Upserted post: {slug}", flush=True)
                total += 1
    finally:
        await conn.close()

    etag_cache_path.parent.mkdir(parents=True, exist_ok=True)
    etag_cache_path.write_text(json.dumps(etag_cache, indent=2, ensure_ascii=False))

    return total, fetched, cached_count


def index_posts_from_github(
    remote_url: str, output: pathlib.Path, etag_cache_path: pathlib.Path
) -> tuple[int, int, int]:
    """Download and index blog posts from GitHub. Returns (total, fetched, cached_count)."""
    owner, repo, ref, path = parse_remote_url(remote_url)

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("Warning: GITHUB_TOKEN not set. Using unauthenticated requests (60/hour limit).")

    auth_headers: dict[str, str] = {"Authorization": f"Bearer {token}"} if token else {}
    auth_headers["Accept"] = "application/vnd.github+json"
    auth_headers["X-GitHub-Api-Version"] = "2022-11-28"

    # Load ETag cache
    etag_cache: dict = {}
    if etag_cache_path.exists():
        etag_cache = json.loads(etag_cache_path.read_text())

    with httpx.Client() as client:
        print(f"Listing .mdx files in {owner}/{repo}/{path} @ {ref}...")
        files = list_mdx_files(client, owner, repo, ref, path, auth_headers)
        print(f"Found {len(files)} .mdx files")

        entries = []
        fetched = 0
        cached_count = 0

        for item in files:
            file_path = item["path"]
            slug = pathlib.Path(file_path).stem
            print(f"  Fetching {file_path}...", flush=True)

            content, new_etag = fetch_file(client, owner, repo, ref, file_path, auth_headers, etag_cache)

            if new_etag:
                etag_cache[file_path] = {"etag": new_etag, "content": content}
                fetched += 1
            else:
                cached_count += 1

            # Parse with python-frontmatter
            post = frontmatter.loads(content)
            body = strip_images(post.content)

            entries.append(
                {
                    "slug": slug,
                    "title": str(post.metadata.get("title", slug)),
                    "date": str(post.metadata.get("date", "")),
                    "tags": list(post.metadata.get("tags", [])),
                    "excerpt": body[:300].strip(),
                    "body": body,
                }
            )

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(entries, indent=2, ensure_ascii=False))

    etag_cache_path.parent.mkdir(parents=True, exist_ok=True)
    etag_cache_path.write_text(json.dumps(etag_cache, indent=2, ensure_ascii=False))

    return len(entries), fetched, cached_count


def main() -> None:
    parser = argparse.ArgumentParser(description="Build BM25 blog index from MDX files fetched via GitHub API.")

    remote_url = os.environ.get("GITHUB_REMOTE_URL", "")

    parser.add_argument(
        "--remote-url",
        default=remote_url,
        help="GitHub tree URL to the blog content folder (or set GITHUB_REMOTE_URL env var)",
    )
    parser.add_argument(
        "--output",
        default="data/blog_index.json",
        type=pathlib.Path,
        help="Output JSON file path (default: data/blog_index.json)",
    )
    parser.add_argument(
        "--etag-cache",
        default="data/blog_index_etags.json",
        type=pathlib.Path,
        help="Path to ETag cache file for incremental updates (default: data/blog_index_etags.json)",
    )
    parser.add_argument(
        "--db",
        action="store_true",
        default=False,
        help="Upsert posts into Postgres (requires DATABASE_URL env var) instead of writing JSON",
    )
    args = parser.parse_args()

    effective_remote_url = args.remote_url or remote_url
    if not effective_remote_url:
        raise SystemExit("Error: --remote-url argument or GITHUB_REMOTE_URL environment variable is required.")

    # Validate URL before making any API calls
    try:
        parse_remote_url(effective_remote_url)
    except ValueError as e:
        raise SystemExit(f"Error: {e}") from e

    if args.db:
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            raise SystemExit(
                "Error: --db flag requires DATABASE_URL environment variable to be set. "
                "Example: DATABASE_URL=postgresql://user:pass@host:5432/dbname"
            )
        total, fetched, cached_count = asyncio.run(
            index_posts_to_db(effective_remote_url, database_url, args.etag_cache)
        )
        print(f"Indexed {total} posts to Postgres ({fetched} fetched, {cached_count} from cache)")
    else:
        total, fetched, cached_count = index_posts_from_github(
            effective_remote_url, args.output, args.etag_cache
        )
        print(f"Indexed {total} posts to {args.output} ({fetched} fetched, {cached_count} from cache)")


if __name__ == "__main__":
    main()
