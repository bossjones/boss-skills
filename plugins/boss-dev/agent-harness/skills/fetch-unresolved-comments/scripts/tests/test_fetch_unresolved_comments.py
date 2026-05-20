"""Tests for fetch_unresolved_comments.py — the pure format_comments function.

format_comments is driven entirely by a hand-built GraphQL response dict, so
these tests run with no network access.
"""

from __future__ import annotations

from typing import Any

from fetch_unresolved_comments import format_comments


def _comment(
    database_id: int,
    *,
    path: str | None = "src/app.py",
    body: str = "a comment",
    author: str | None = "reviewer",
) -> dict[str, Any]:
    """Build one GraphQL review-comment node."""
    return {
        "id": f"PRRC_{database_id}",
        "databaseId": database_id,
        "body": body,
        "path": path,
        "line": 42,
        "startLine": None,
        "diffHunk": "@@ -1,2 +1,2 @@",
        "author": {"login": author} if author is not None else None,
        "createdAt": "2026-05-20T00:00:00Z",
        "updatedAt": "2026-05-20T00:00:00Z",
    }


def _thread(thread_id: str, *, resolved: bool, comments: list[dict[str, Any]]) -> dict[str, Any]:
    """Build one GraphQL review-thread node."""
    return {
        "id": thread_id,
        "isResolved": resolved,
        "comments": {"nodes": comments},
    }


def _response(threads: list[dict[str, Any]]) -> dict[str, Any]:
    """Wrap thread nodes in the GraphQL response envelope."""
    return {
        "data": {
            "repository": {
                "pullRequest": {"reviewThreads": {"nodes": threads}},
            }
        }
    }


class TestFormatComments:
    """format_comments grouping, filtering, and counting."""

    def test_resolved_threads_are_excluded(self) -> None:
        data = _response([
            _thread("T1", resolved=True, comments=[_comment(1, path="resolved.py")]),
            _thread("T2", resolved=False, comments=[_comment(2, path="open.py")]),
        ])
        result = format_comments(data)
        assert set(result.by_file) == {"open.py"}
        assert result.total == 1

    def test_unresolved_threads_grouped_by_file(self) -> None:
        data = _response([
            _thread("T1", resolved=False, comments=[_comment(1, path="a.py")]),
            _thread("T2", resolved=False, comments=[_comment(2, path="b.py")]),
        ])
        result = format_comments(data)
        assert set(result.by_file) == {"a.py", "b.py"}

    def test_total_counts_every_comment(self) -> None:
        data = _response([
            _thread(
                "T1",
                resolved=False,
                comments=[_comment(1, path="a.py"), _comment(2, path="a.py")],
            ),
            _thread("T2", resolved=False, comments=[_comment(3, path="b.py")]),
        ])
        result = format_comments(data)
        assert result.total == 3
        assert len(result.by_file["a.py"][0].comments) == 2

    def test_thread_with_no_comments_is_skipped(self) -> None:
        data = _response([_thread("T1", resolved=False, comments=[])])
        result = format_comments(data)
        assert result.by_file == {}
        assert result.total == 0

    def test_thread_with_no_path_is_skipped(self) -> None:
        data = _response([_thread("T1", resolved=False, comments=[_comment(1, path=None)])])
        result = format_comments(data)
        assert result.by_file == {}

    def test_zero_review_threads(self) -> None:
        result = format_comments(_response([]))
        assert result.total == 0
        assert result.by_file == {}

    def test_missing_author_falls_back_to_unknown(self) -> None:
        data = _response([_thread("T1", resolved=False, comments=[_comment(1, author=None)])])
        result = format_comments(data)
        thread = result.by_file["src/app.py"][0]
        assert thread.comments[0].author == "unknown"
