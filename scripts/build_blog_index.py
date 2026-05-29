#!/usr/bin/env python3
"""Build a JSON search index from MDX blog post files.

Usage:
    uv run python scripts/build_blog_index.py --posts-dir /path/to/blog --output data/blog_index.json
"""

import argparse
import json
import pathlib
import re

import frontmatter


def strip_images(text: str) -> str:
    """Remove image markdown and JSX image tags from body text."""
    # Standard markdown images: ![alt text](path)
    text = re.sub(r"!\[.*?\]\(.*?\)", "", text)
    # MDX JSX self-closing image tags: <Image .../> and <img .../>
    text = re.sub(r"<[Ii]mage\s[^>]*/?>", "", text, flags=re.DOTALL)
    text = re.sub(r"<img\s[^>]*/?>", "", text, flags=re.DOTALL)
    return text


def index_posts(posts_dir: pathlib.Path, output: pathlib.Path) -> int:
    """Index all .mdx files found recursively under posts_dir.

    Returns the number of posts indexed.
    """
    entries = []
    for mdx_file in sorted(posts_dir.rglob("*.mdx")):
        post = frontmatter.load(str(mdx_file))
        body = strip_images(post.content)

        slug = mdx_file.stem
        title = str(post.metadata.get("title", slug))
        date = str(post.metadata.get("date", ""))
        tags = list(post.metadata.get("tags", []))
        excerpt = body[:300]

        entries.append({"slug": slug, "title": title, "date": date, "tags": tags, "excerpt": excerpt, "body": body})

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(entries, indent=2, ensure_ascii=False))
    return len(entries)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build BM25 blog index from MDX files.")
    parser.add_argument("--posts-dir", required=True, type=pathlib.Path, help="Directory containing .mdx blog posts")
    parser.add_argument(
        "--output",
        default="data/blog_index.json",
        type=pathlib.Path,
        help="Output JSON file path (default: data/blog_index.json)",
    )
    args = parser.parse_args()

    if not args.posts_dir.exists():
        raise SystemExit(f"Error: --posts-dir does not exist: {args.posts_dir}")

    n = index_posts(args.posts_dir, args.output)
    print(f"Indexed {n} posts to {args.output}")


if __name__ == "__main__":
    main()
