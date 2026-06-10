"""Tests for the user_prompt_submit prompt validator.

``validate_prompt`` ships with an empty blocked-pattern list, so it is currently
a pass-through. These tests pin that contract: every prompt is accepted. If a
future change adds blocked patterns, these tests must be updated deliberately —
that is the signal we want.
"""

from __future__ import annotations

import pytest
from hook_loader import load_hook

user_prompt_submit = load_hook("user_prompt_submit.py")


@pytest.mark.parametrize(
    "prompt",
    [
        "",
        "Please refactor the auth module",
        "rm -rf /",  # not currently blocked — documents the no-op contract
        "DROP TABLE users;",
    ],
)
def test_validate_prompt_accepts_everything(prompt: str) -> None:
    is_valid, reason = user_prompt_submit.validate_prompt(prompt)
    assert is_valid is True
    assert reason is None
