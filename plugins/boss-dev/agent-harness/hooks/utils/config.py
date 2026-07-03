"""
Shared configuration resolver for agent-harness hooks.

Reads plugin user-config values (CLAUDE_PLUGIN_OPTION_<KEY>) with automatic
fallback to bare environment variables so existing .env / .envrc setups keep
working without changes.
"""

from __future__ import annotations

import os

_FALSE_VALUES = {"0", "false", "no", "off"}


def _option(key: str) -> str | None:
    """Return CLAUDE_PLUGIN_OPTION_<KEY>, falling back to the bare env var."""
    val = os.environ.get(f"CLAUDE_PLUGIN_OPTION_{key}")
    if val is None:
        val = os.environ.get(key)
    return val


def tts_enabled() -> bool:
    """Return True unless ENABLE_TTS resolves to a falsy value. Default on."""
    val = _option("ENABLE_TTS")
    if val is None:
        return True
    return val.strip().lower() not in _FALSE_VALUES


def engineer_name() -> str:
    """Return the configured engineer name, or an empty string."""
    return (_option("ENGINEER_NAME") or "").strip()


def snyk_enabled() -> bool:
    """Return True only if ENABLE_SNYK_AGENT_SCAN resolves truthy. Default off."""
    val = _option("ENABLE_SNYK_AGENT_SCAN")
    if val is None:
        return False
    return val.strip().lower() not in _FALSE_VALUES


def snyk_token() -> str:
    """Return the configured Snyk token, or an empty string."""
    return (_option("SNYK_TOKEN") or "").strip()
