#!/usr/bin/env -S uv run --script --quiet
# /// script
# requires-python = ">=3.13"
# dependencies = ["aiohttp", "pydantic"]
# ///
"""Fetch a GitHub PR diff with filtering and line numbers for code review.

Standalone PEP 723 script — run it with::

    uv run fetch_diff.py <pr_url> [--files <pattern> ...]

`uv` resolves the inline ``aiohttp`` / ``pydantic`` dependencies on demand, so
the script is fully self-contained: it has no dependency on any repository
layout or workspace package. The trimmed GitHub client (token discovery,
PR-URL parsing, and the async ``GitHubClient``) is inlined for that reason.

Adapted from the mlflow ``fetch-diff`` skill (Apache-2.0).
"""

from __future__ import annotations

import argparse
import asyncio
import fnmatch
import os
import re
import subprocess
import sys
from pathlib import Path
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


class GitRef(BaseModel):
    sha: str
    ref: str


class PullRequest(BaseModel):
    title: str
    body: str | None
    head: GitRef


class GitHubClient:
    """Minimal async GitHub REST client — only the calls fetch-diff needs."""

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

    async def _get_text(self, endpoint: str, accept: str) -> str:
        if self._session is None:
            raise RuntimeError("GitHubClient must be used as an async context manager")
        async with self._session.get(endpoint, headers={"Accept": accept}) as resp:
            resp.raise_for_status()
            return await resp.text()

    async def _get_json(self, endpoint: str) -> dict[str, Any]:
        if self._session is None:
            raise RuntimeError("GitHubClient must be used as an async context manager")
        async with self._session.get(endpoint) as resp:
            resp.raise_for_status()
            return cast(dict[str, Any], await resp.json())

    async def get_pr(self, owner: str, repo: str, pr_number: int) -> PullRequest:
        data = await self._get_json(f"/repos/{owner}/{repo}/pulls/{pr_number}")
        return PullRequest.model_validate(data)

    async def get_pr_diff(self, owner: str, repo: str, pr_number: int) -> str:
        return await self._get_text(
            f"/repos/{owner}/{repo}/pulls/{pr_number}",
            accept="application/vnd.github.v3.diff",
        )

    async def get_compare_diff(self, owner: str, repo: str, base: str, head: str) -> str:
        return await self._get_text(
            f"/repos/{owner}/{repo}/compare/{base}...{head}",
            accept="application/vnd.github.v3.diff",
        )


# ---------------------------------------------------------------------------
# Diff filtering and line-number annotation
# ---------------------------------------------------------------------------

_MASKED_DIFF_MESSAGE = "[Auto-generated file - diff masked]"
_DELETED_DIFF_MESSAGE = "[Deleted file - diff masked]"


def extract_stacked_pr_base_sha(pr_body: str | None, head_ref: str) -> str | None:
    """Extract the base SHA from a stacked-PR incremental-diff link.

    This keys off a literal "Stacked PR" section in the PR body — an
    mlflow-flavored convention. In a repo that does not use stacked PRs the
    marker is simply absent and this returns ``None``, so the caller falls back
    to the full PR diff.

    In stacked-PR descriptions the current PR is marked in bold. Example::

        ## Stacked PR
        - [branch_a](url) [Files changed](url)
          - [**branch_b**](url) [Files changed](url/files/abc1234..def5678)

    The bold entry matching ``head_ref`` yields the base SHA from
    ``/files/<base>..<head>``.
    """
    if not pr_body or "Stacked PR" not in pr_body:
        return None

    marker = f"[**{head_ref}**]"
    for line in pr_body.split("\n"):
        if marker in line:  # noqa: SIM102
            if m := re.search(r"/files/(?P<base>[a-f0-9]{7,40})\.\.(?P<head>[a-f0-9]{7,40})", line):
                return m.group("base")

    return None


def is_autogenerated_file(file_path: str) -> bool:
    """Return ``True`` if the file is auto-generated and its diff should be masked.

    Recognizes common lock files and protobuf-generated Java sources. Masking
    keeps review focused on hand-written changes.
    """
    path = Path(file_path)

    if path.name in {"uv.lock", "yarn.lock", "package-lock.json"}:
        return True

    if path.suffix == ".java" and path.exists():
        with path.open() as f:
            first_line = f.readline()
        if "Generated by the protocol buffer compiler" in first_line:
            return True

    return False


def filter_diff(full_diff: str, file_patterns: list[str] | None = None) -> str:
    """Filter a diff by file globs, mask auto-generated files, and add line numbers."""
    lines = full_diff.split("\n")
    filtered_diff: list[str] = []
    in_included_file = False
    is_masked = False
    is_deleted = False

    for line in lines:
        if line.startswith("diff --git"):
            if match := re.match(r"diff --git a/(.*?) b/(.*?)$", line):
                file_path = match.group(2)

                if file_patterns and not any(fnmatch.fnmatch(file_path, pat) for pat in file_patterns):
                    in_included_file = False
                    is_masked = False
                    is_deleted = False
                else:
                    in_included_file = True
                    is_deleted = False
                    is_masked = is_autogenerated_file(file_path)
            else:
                in_included_file = False
                is_masked = False
                is_deleted = False

            if in_included_file:
                filtered_diff.append(line)
        elif in_included_file:
            if line.startswith("deleted file mode"):
                is_deleted = True
                is_masked = True
                filtered_diff.append(line)
            elif is_masked:
                mask_message = _DELETED_DIFF_MESSAGE if is_deleted else _MASKED_DIFF_MESSAGE
                if line.startswith("@@"):
                    # Only emit the mask message once (for the first hunk).
                    if not filtered_diff or filtered_diff[-1] != mask_message:
                        filtered_diff.append(mask_message)
                elif line.startswith(("--- ", "+++ ")):
                    # Preserve diff file headers for masked files.
                    filtered_diff.append(line)
                elif not line.startswith(("+", "-", " ", "\\")):
                    # Other metadata lines (index, mode changes, rename info) pass through.
                    filtered_diff.append(line)
                # Skip hunk content lines.
            else:
                filtered_diff.append(line)

    # Add line numbers.
    result_lines: list[str] = []
    old_line = 0
    new_line = 0
    in_header = False

    for line in filtered_diff:
        if line.startswith("diff --git"):
            in_header = True
            if result_lines:
                result_lines.append("")
            result_lines.append(line)
        elif line.startswith("@@"):
            in_header = False
            if match := re.match(r"@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@", line):
                old_line = int(match.group(1))
                new_line = int(match.group(2))
            result_lines.append(line)
        elif in_header or line in (_MASKED_DIFF_MESSAGE, _DELETED_DIFF_MESSAGE):
            result_lines.append(line)
        elif line.startswith("-"):
            result_lines.append(f"{old_line:5d}       | {line}")
            old_line += 1
        elif line.startswith("+"):
            result_lines.append(f"      {new_line:5d} | {line}")
            new_line += 1
        else:
            result_lines.append(f"{old_line:5d} {new_line:5d} | {line}")
            old_line += 1
            new_line += 1

    return "\n".join(result_lines)


async def fetch_diff(pr_url: str, file_patterns: list[str] | None = None) -> str:
    """Fetch a PR diff (or stacked-PR incremental diff) and annotate it."""
    owner, repo, pr_number = parse_pr_url(pr_url)

    async with GitHubClient() as client:
        pr = await client.get_pr(owner, repo, pr_number)
        head_sha = pr.head.sha
        head_ref = pr.head.ref

        if base_sha := extract_stacked_pr_base_sha(pr.body, head_ref):
            print(
                f"Detected stacked PR, fetching incremental diff: {base_sha[:7]}..{head_sha[:7]}",
                file=sys.stderr,
            )
            diff = await client.get_compare_diff(owner, repo, base_sha, head_sha)
        else:
            diff = await client.get_pr_diff(owner, repo, pr_number)

    return filter_diff(diff, file_patterns)


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Fetch a GitHub PR diff with line numbers for code review.",
    )
    parser.add_argument(
        "pr_url",
        help="GitHub PR URL, e.g. https://github.com/owner/repo/pull/123",
    )
    parser.add_argument(
        "--files",
        nargs="+",
        metavar="PATTERN",
        help="Glob patterns to filter files (e.g. '*.py' 'src/server/*')",
    )
    args = parser.parse_args()
    result = asyncio.run(fetch_diff(args.pr_url, args.files))
    print(result)


if __name__ == "__main__":
    main()
