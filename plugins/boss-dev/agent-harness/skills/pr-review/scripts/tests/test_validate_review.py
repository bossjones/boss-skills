"""Tests for validate_review.py — schema validation of pr-review payloads.

Each test validates a payload against the real review-payload.schema.json that
ships beside the skill, so the tests also confirm the schema itself is loadable.
"""

from __future__ import annotations

import json
from typing import Any

from validate_review import DEFAULT_SCHEMA, format_path, validate_payload

SCHEMA: dict[str, Any] = json.loads(DEFAULT_SCHEMA.read_text())

FOOTER = "🤖 Generated with Claude"


def test_default_schema_path_resolves_to_sibling() -> None:
    """The default schema is the sibling review-payload.schema.json."""
    assert DEFAULT_SCHEMA.name == "review-payload.schema.json"
    assert DEFAULT_SCHEMA.exists()


class TestValidPayloads:
    """Payloads that satisfy the schema produce no errors."""

    def test_minimal_approve(self) -> None:
        payload = {
            "event": "APPROVE",
            "body": f"The change is sound and well tested.\n\n{FOOTER}",
            "comments": [],
        }
        assert validate_payload(payload, SCHEMA) == []

    def test_comment_with_one_inline_comment(self) -> None:
        payload = {
            "event": "COMMENT",
            "body": f"A few concerns worth addressing.\n\n{FOOTER}",
            "comments": [
                {
                    "path": "src/app.py",
                    "body": "🟡 **MODERATE:** consider extracting this branch.",
                    "line": 12,
                    "side": "RIGHT",
                }
            ],
        }
        assert validate_payload(payload, SCHEMA) == []

    def test_multi_line_comment_with_start_side(self) -> None:
        payload = {
            "event": "COMMENT",
            "body": f"Range comment.\n\n{FOOTER}",
            "comments": [
                {
                    "path": "src/app.py",
                    "body": "🟢 **NIT:** tidy this block.",
                    "line": 20,
                    "side": "RIGHT",
                    "start_line": 18,
                    "start_side": "RIGHT",
                }
            ],
        }
        assert validate_payload(payload, SCHEMA) == []


class TestInvalidPayloads:
    """Malformed payloads each produce at least one error."""

    def test_missing_footer(self) -> None:
        payload = {"event": "APPROVE", "body": "No footer here.", "comments": []}
        assert validate_payload(payload, SCHEMA)

    def test_comment_body_missing_severity_prefix(self) -> None:
        payload = {
            "event": "COMMENT",
            "body": f"Body.\n\n{FOOTER}",
            "comments": [{"path": "a.py", "body": "just a plain comment", "line": 1, "side": "RIGHT"}],
        }
        assert validate_payload(payload, SCHEMA)

    def test_event_not_in_enum(self) -> None:
        payload = {"event": "MERGE", "body": f"Body.\n\n{FOOTER}", "comments": []}
        assert validate_payload(payload, SCHEMA)

    def test_approve_with_critical_comment(self) -> None:
        payload = {
            "event": "APPROVE",
            "body": f"Body.\n\n{FOOTER}",
            "comments": [
                {
                    "path": "a.py",
                    "body": "🔴 **CRITICAL:** this leaks a file handle.",
                    "line": 5,
                    "side": "RIGHT",
                }
            ],
        }
        assert validate_payload(payload, SCHEMA)

    def test_start_line_without_start_side(self) -> None:
        payload = {
            "event": "COMMENT",
            "body": f"Body.\n\n{FOOTER}",
            "comments": [
                {
                    "path": "a.py",
                    "body": "🟢 **NIT:** small thing.",
                    "line": 9,
                    "side": "RIGHT",
                    "start_line": 7,
                }
            ],
        }
        assert validate_payload(payload, SCHEMA)


class TestFormatPath:
    """JSON-pointer rendering for error messages."""

    def test_root_path(self) -> None:
        assert format_path([]) == "<root>"

    def test_nested_path_with_index(self) -> None:
        assert format_path(["comments", 0, "body"]) == "comments[0].body"
