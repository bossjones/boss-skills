"""Build redacted hook-event records and append them to JSON Lines files."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    import fcntl
except ImportError:  # pragma: no cover - exercised on non-POSIX platforms
    fcntl = None  # type: ignore[assignment]

SCHEMA_VERSION = 1
REDACTED_VALUE = "[REDACTED]"

PROMOTED_FIELDS: tuple[str, ...] = (
    "session_id",
    "cwd",
    "permission_mode",
    "tool_name",
    "tool_use_id",
    "error_type",
    "error_message",
    "task_id",
    "task_status",
    "command_name",
    "classifier_decision",
    "tools_used",
    "prompt_id",
    "agent_id",
)

_SENSITIVE_KEY_SUFFIXES: tuple[str, ...] = ("_TOKEN", "_KEY", "_SECRET", "_PASSWORD")
_SENSITIVE_KEY_NAMES: frozenset[str] = frozenset({"AUTHORIZATION", "PASSWORD", "SECRET", "TOKEN"})
_TOKEN_PREFIXES: tuple[str, ...] = (
    "sk-",
    "ghp_",
    "gho_",
    "ghu_",
    "ghs_",
    "ghv_",
    "xoxb-",
    "xoxp-",
    "xoxa-",
    "xoxr-",
    "xoxs-",
    "******",
)
_EMBEDDED_TOKEN_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_-])(?:sk-|ghp_|gho_|ghu_|ghs_|ghv_|xoxb-|xoxp-|xoxa-|xoxr-|xoxs-)[A-Za-z0-9_-]+",
    re.IGNORECASE,
)


def _is_sensitive_key(key: object) -> bool:
    if not isinstance(key, str):
        return False
    normalized = key.upper()
    return normalized in _SENSITIVE_KEY_NAMES or normalized.endswith(_SENSITIVE_KEY_SUFFIXES)


def _has_token_prefix(value: str) -> bool:
    return value.lstrip().lower().startswith(_TOKEN_PREFIXES)


def redact_payload(payload: Any) -> Any:
    """Recursively redact known secret fields and token-shaped string values."""
    if isinstance(payload, Mapping):
        return {
            key: REDACTED_VALUE if _is_sensitive_key(key) else redact_payload(value) for key, value in payload.items()
        }
    if isinstance(payload, list | tuple):
        return [redact_payload(value) for value in payload]
    if isinstance(payload, str):
        if _has_token_prefix(payload):
            return REDACTED_VALUE
        return _EMBEDDED_TOKEN_PATTERN.sub(REDACTED_VALUE, payload)
    return payload


def build_record(event_type: str, payload: Any, *, now: datetime | None = None) -> dict[str, Any]:
    """Build a schema-versioned event record with redacted payload data."""
    recorded_at = (now or datetime.now(UTC)).astimezone(UTC)
    redacted_payload = redact_payload(payload)
    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "timestamp": int(recorded_at.timestamp() * 1000),
        "ts_iso": recorded_at.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        "source_app": "agent-harness",
        "hook_event_type": event_type,
        "payload": redacted_payload,
    }
    if isinstance(redacted_payload, Mapping):
        for field in PROMOTED_FIELDS:
            if field in redacted_payload:
                record[field] = redacted_payload[field]
    return record


def append_jsonl(path: Path, record: Mapping[str, Any]) -> None:
    """Append one schema-versioned JSON record using one locked file write."""
    if record.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"JSONL records must use schema_version {SCHEMA_VERSION}")

    line = json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as log_file:
        if fcntl is not None:
            fcntl.flock(log_file.fileno(), fcntl.LOCK_EX)
        try:
            log_file.write(line)
            log_file.flush()
        finally:
            if fcntl is not None:
                fcntl.flock(log_file.fileno(), fcntl.LOCK_UN)
