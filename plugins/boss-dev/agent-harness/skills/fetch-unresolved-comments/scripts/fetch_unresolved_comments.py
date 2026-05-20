#!/usr/bin/env -S uv run --script --quiet
# /// script
# requires-python = ">=3.13"
# dependencies = ["aiohttp", "pydantic"]
# ///
"""Fetch unresolved PR review comments via the GitHub GraphQL API.

Standalone PEP 723 script — run it with::

    uv run fetch_unresolved_comments.py <pr_url>

`uv` resolves the inline ``aiohttp`` / ``pydantic`` dependencies on demand, so
the script is fully self-contained. The trimmed GitHub client (token discovery,
PR-URL parsing, and the async GraphQL call) is inlined for that reason.

Adapted from the mlflow ``fetch-unresolved-comments`` skill (Apache-2.0).
"""

from __future__ import annotations

import argparse
import asyncio
import os
import re
import subprocess
import sys
from typing import Any, Self, cast

import aiohttp
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# GitHub client (trimmed subset, inlined)
# ---------------------------------------------------------------------------

GITHUB_API = "https://api.github.com"


def get_github_token() -> str:
    """Return a GitHub token from ``GH_TOKEN`` or, failing that, the ``gh`` CLI."""
    if token := os.environ.get("GH_TOKEN"):
        return token
    try:
        return subprocess.check_output(["gh", "auth", "token"], text=True).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: GH_TOKEN not found (set env var or install gh CLI)", file=sys.stderr)
        sys.exit(1)


def parse_pr_url(url: str) -> tuple[str, str, int]:
    """Parse ``https://github.com/<owner>/<repo>/pull/<n>`` into its parts."""
    if m := re.match(r"https://github\.com/([^/]+)/([^/]+)/pull/(\d+)", url):
        return m.group(1), m.group(2), int(m.group(3))
    raise ValueError(f"Invalid PR URL: {url}")


class ReviewComment(BaseModel):
    id: int  # noqa: A003 — field name mirrors the GitHub API response
    body: str
    author: str
    createdAt: str


class ReviewThread(BaseModel):
    thread_id: str
    line: int | None
    startLine: int | None
    diffHunk: str | None
    comments: list[ReviewComment]


class GitHubClient:
    """Minimal async GitHub client — only the GraphQL call this skill needs."""

    def __init__(self, token: str | None = None) -> None:
        self.token = token or get_github_token()
        self._session: aiohttp.ClientSession | None = None

    async def __aenter__(self) -> Self:
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
        }
        self._session = aiohttp.ClientSession(base_url=GITHUB_API, headers=headers)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        if self._session:
            await self._session.close()

    async def graphql(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        if self._session is None:
            raise RuntimeError("GitHubClient must be used as an async context manager")
        payload = {"query": query, "variables": variables}
        async with self._session.post("/graphql", json=payload) as resp:
            resp.raise_for_status()
            return cast(dict[str, Any], await resp.json())


# ---------------------------------------------------------------------------
# Unresolved-comment formatting
# ---------------------------------------------------------------------------


class UnresolvedCommentsResult(BaseModel):
    total: int
    by_file: dict[str, list[ReviewThread]]


REVIEW_THREADS_QUERY = """
query($owner: String!, $repo: String!, $prNumber: Int!) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $prNumber) {
      reviewThreads(first: 100) {
        nodes {
          id
          isResolved
          comments(first: 100) {
            nodes {
              id
              databaseId
              body
              path
              line
              startLine
              diffHunk
              author {
                login
              }
              createdAt
              updatedAt
            }
          }
        }
      }
    }
  }
}
"""


def format_comments(data: dict[str, Any]) -> UnresolvedCommentsResult:
    """Group unresolved review-thread comments by file.

    Resolved threads, threads with no comments, and threads whose first comment
    has no ``path`` are skipped. ``total`` counts every comment across the kept
    threads.
    """
    threads = data["data"]["repository"]["pullRequest"]["reviewThreads"]["nodes"]

    by_file: dict[str, list[ReviewThread]] = {}
    total_comments = 0

    for thread in threads:
        if thread["isResolved"]:
            continue

        comments: list[ReviewComment] = []
        path: str | None = None
        line: int | None = None
        start_line: int | None = None
        diff_hunk: str | None = None

        for comment in thread["comments"]["nodes"]:
            if path is None:
                path = comment["path"]
                line = comment["line"]
                start_line = comment.get("startLine")
                diff_hunk = comment.get("diffHunk")

            comments.append(
                ReviewComment(
                    id=comment["databaseId"],
                    body=comment["body"],
                    author=comment["author"]["login"] if comment["author"] else "unknown",
                    createdAt=comment["createdAt"],
                )
            )
            total_comments += 1

        if path and comments:
            by_file.setdefault(path, []).append(
                ReviewThread(
                    thread_id=thread["id"],
                    line=line,
                    startLine=start_line,
                    diffHunk=diff_hunk,
                    comments=comments,
                )
            )

    return UnresolvedCommentsResult(total=total_comments, by_file=by_file)


async def fetch_unresolved_comments(pr_url: str) -> UnresolvedCommentsResult:
    """Fetch and format the unresolved review comments for a PR."""
    owner, repo, pr_number = parse_pr_url(pr_url)

    async with GitHubClient() as client:
        data = await client.graphql(
            REVIEW_THREADS_QUERY,
            {"owner": owner, "repo": repo, "prNumber": pr_number},
        )

    return format_comments(data)


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Fetch unresolved PR review comments via the GitHub GraphQL API.",
    )
    parser.add_argument(
        "pr_url",
        help="GitHub PR URL, e.g. https://github.com/owner/repo/pull/123",
    )
    args = parser.parse_args()
    result = asyncio.run(fetch_unresolved_comments(args.pr_url))
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
