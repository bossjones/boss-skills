"""Tests for the shared hook config resolver (``hooks/utils/config.py``).

Covers the TTS on/off switch and engineer-name resolution, including the
``CLAUDE_PLUGIN_OPTION_*`` precedence over bare env vars.
"""

from __future__ import annotations

import pytest
from hook_loader import load_hook

config = load_hook("utils/config.py")


@pytest.fixture(autouse=True)
def _clean_tts_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure no ambient ENABLE_TTS / ENGINEER_NAME leaks into a test."""
    for var in (
        "ENABLE_TTS",
        "CLAUDE_PLUGIN_OPTION_ENABLE_TTS",
        "ENGINEER_NAME",
        "CLAUDE_PLUGIN_OPTION_ENGINEER_NAME",
    ):
        monkeypatch.delenv(var, raising=False)


def test_tts_enabled_default_on_when_unset() -> None:
    assert config.tts_enabled() is True


@pytest.mark.parametrize("value", ["0", "false", "no", "off", "FALSE", "Off", "  no  "])
def test_tts_disabled_via_bare_env(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("ENABLE_TTS", value)
    assert config.tts_enabled() is False


@pytest.mark.parametrize("value", ["0", "false", "no", "off"])
def test_tts_disabled_via_plugin_option(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("CLAUDE_PLUGIN_OPTION_ENABLE_TTS", value)
    assert config.tts_enabled() is False


@pytest.mark.parametrize("value", ["1", "true", "yes", "on", "anything"])
def test_tts_enabled_for_truthy_values(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("ENABLE_TTS", value)
    assert config.tts_enabled() is True


def test_plugin_option_takes_precedence_over_bare_env(monkeypatch: pytest.MonkeyPatch) -> None:
    # Option says off, bare env says on -> option wins (off).
    monkeypatch.setenv("CLAUDE_PLUGIN_OPTION_ENABLE_TTS", "false")
    monkeypatch.setenv("ENABLE_TTS", "true")
    assert config.tts_enabled() is False


def test_engineer_name_empty_when_unset() -> None:
    assert config.engineer_name() == ""


def test_engineer_name_reads_and_trims(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENGINEER_NAME", "  Malcolm  ")
    assert config.engineer_name() == "Malcolm"


def test_engineer_name_plugin_option_precedence(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLAUDE_PLUGIN_OPTION_ENGINEER_NAME", "FromOption")
    monkeypatch.setenv("ENGINEER_NAME", "FromBareEnv")
    assert config.engineer_name() == "FromOption"
