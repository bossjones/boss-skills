"""Focused recursive secret-redaction tests for hook log payloads."""

from __future__ import annotations

import pytest
from hook_loader import load_hook

log_writer = load_hook("utils/log_writer.py")


@pytest.mark.parametrize("key", ["api_token", "API_KEY", "client_secret", "db_password", "authorization"])
def test_redact_payload_redacts_sensitive_key_names(key: str) -> None:
    assert log_writer.redact_payload({key: "ordinary-value"}) == {key: log_writer.REDACTED_VALUE}


@pytest.mark.parametrize("value", ["sk-live-secret", "ghp_secret", "xoxb-secret", "******masked"])
def test_redact_payload_redacts_known_token_prefixes(value: str) -> None:
    assert log_writer.redact_payload({"message": value}) == {"message": log_writer.REDACTED_VALUE}


def test_redact_payload_recurses_without_changing_ordinary_values() -> None:
    payload = {
        "message": "sketch a feature",
        "count": 3,
        "nested": [{"github_token": "hidden"}, {"text": "ordinary text"}],
    }

    assert log_writer.redact_payload(payload) == {
        "message": "sketch a feature",
        "count": 3,
        "nested": [{"github_token": log_writer.REDACTED_VALUE}, {"text": "ordinary text"}],
    }


def test_redact_payload_removes_token_values_embedded_in_command_text() -> None:
    payload = {"tool_input": {"command": 'echo "export FAKE_TOKEN=sk-abc123"'}}

    redacted = log_writer.redact_payload(payload)

    assert "sk-abc123" not in redacted["tool_input"]["command"]
    assert log_writer.REDACTED_VALUE in redacted["tool_input"]["command"]


def test_redact_payload_removes_bearer_tokens_embedded_in_command_text() -> None:
    payload = {"tool_input": {"command": "curl -H 'Authorization: Bearer abc123' https://api.example.com"}}

    redacted = log_writer.redact_payload(payload)

    assert "abc123" not in redacted["tool_input"]["command"]
    assert log_writer.REDACTED_VALUE in redacted["tool_input"]["command"]
