import base64
import json
import pathlib
import re
import time
from urllib.parse import urlparse

import frontmatter
import httpx

MIN_REMAINING = 10
MAX_RETRIES = 3


def strip_images(text: str) -> str:
    text = re.sub(r"!\[.*?\]\(.*?\)", "", text)
    text = re.sub(r"<[Ii]mage\s[^>]*/?>", "", text, flags=re.DOTALL)
    text = re.sub(r"<img\s[^>]*/?>", "", text, flags=re.DOTALL)
    return text


def parse_remote_url(url: str) -> tuple[str, str, str, str]:
    """Return (owner, repo, ref, path) from a GitHub tree URL."""
    parts = urlparse(url).path.strip("/").split("/")
    if len(parts) < 4 or parts[2] != "tree":
        raise ValueError(
            f"Expected a GitHub tree URL (https://github.com/owner/repo/tree/ref/path), got: {url}"
        )
    return parts[0], parts[1], parts[3], "/".join(parts[4:])


def _github_get(client: httpx.Client, url: str, headers: dict | None = None) -> httpx.Response:
    for attempt in range(MAX_RETRIES):
        response = client.get(url, headers=headers or {})
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


def _list_mdx_files(
    client: httpx.Client, owner: str, repo: str, ref: str, path: str, auth_headers: dict
) -> list[dict]:
    url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{ref}?recursive=1"
    tree = _github_get(client, url, auth_headers).json()["tree"]
    prefix = path.rstrip("/") + "/"
    return [
        item
        for item in tree
        if item["type"] == "blob" and item["path"].startswith(prefix) and item["path"].endswith(".mdx")
    ]


def _fetch_file(
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
    remaining = int(response.headers.get("X-RateLimit-Remaining", 9999))
    reset_at = int(response.headers.get("X-RateLimit-Reset", 0))
    print(f"  [rate limit] {remaining} requests remaining", flush=True)

    if response.status_code == 304:
        print(f"    304 cached: {file_path}", flush=True)
        return cached["content"], None

    if response.status_code in (403, 429):
        response = _github_get(client, url, headers)
    else:
        response.raise_for_status()
        if remaining <= MIN_REMAINING:
            wait = max(0, reset_at - time.time()) + 1
            print(f"  Rate limit low ({remaining} remaining). Sleeping {wait:.0f}s until reset.")
            time.sleep(wait)

    content = base64.b64decode(response.json()["content"]).decode("utf-8")
    return content, response.headers.get("ETag")


class GitHubBlogScraper:
    def __init__(
        self,
        remote_url: str,
        token: str | None = None,
        etag_cache_path: pathlib.Path | None = None,
    ) -> None:
        self._remote_url = remote_url
        self._token = token
        self._etag_cache_path = etag_cache_path or pathlib.Path("data/blog_index_etags.json")

    def scrape(self) -> list[dict]:
        owner, repo, ref, path = parse_remote_url(self._remote_url)

        auth_headers: dict[str, str] = (
            {"Authorization": f"Bearer {self._token}"} if self._token else {}
        )
        auth_headers["Accept"] = "application/vnd.github+json"
        auth_headers["X-GitHub-Api-Version"] = "2022-11-28"

        etag_cache: dict = {}
        if self._etag_cache_path.exists():
            etag_cache = json.loads(self._etag_cache_path.read_text())

        posts: list[dict] = []
        with httpx.Client() as client:
            print(f"Listing .mdx files in {owner}/{repo}/{path} @ {ref}...")
            files = _list_mdx_files(client, owner, repo, ref, path, auth_headers)
            print(f"Found {len(files)} .mdx files")

            for item in files:
                file_path = item["path"]
                slug = pathlib.Path(file_path).stem
                print(f"  Fetching {file_path}...", flush=True)

                content, new_etag = _fetch_file(
                    client, owner, repo, ref, file_path, auth_headers, etag_cache
                )
                if new_etag:
                    etag_cache[file_path] = {"etag": new_etag, "content": content}

                post = frontmatter.loads(content)
                body = strip_images(post.content)
                posts.append({
                    "slug": slug,
                    "title": str(post.metadata.get("title", slug)),
                    "date": str(post.metadata.get("date", "")),
                    "tags": list(post.metadata.get("tags", [])),
                    "excerpt": body[:300].strip(),
                    "body": body,
                })
                print(f"    Parsed: {slug}", flush=True)

        self._etag_cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._etag_cache_path.write_text(json.dumps(etag_cache, indent=2, ensure_ascii=False))

        return posts
