"""Unit tests for ``status_lines/status_line_v10.py`` (importlib load).

Covers the auth-badge layer added on top of v10: the single-pass transcript
scan (``scan_transcript``), the pure ``detect_auth_mode`` truth table, the
``format_auth_badge`` renderer, and the ``generate_status_line`` integration.
The PEP 723 script is loaded via ``importlib.util.spec_from_file_location`` (the
``if __name__ == "__main__"`` guard keeps import side-effect-free), matching the
pattern in ``tests/test_symlink_plugins.py``.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

SCRIPT = (
    Path(__file__).resolve().parent.parent
    / "plugins"
    / "boss-dev"
    / "agent-harness"
    / "status_lines"
    / "status_line_v10.py"
)


def _load(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(path.stem.replace("-", "_"), path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


sl = _load(SCRIPT)


# --------------------------------------------------------------------------- #
# Builders
# --------------------------------------------------------------------------- #


def _payload(**overrides: object) -> dict:
    """A minimal valid status-line stdin payload; override any key."""
    data: dict = {
        "model": {"display_name": "Opus 5"},
        "context_window": {"used_percentage": 12.5, "context_window_size": 200000},
    }
    data.update(overrides)
    return data


def _transcript(tmp_path: Path, entries: list[object]) -> Path:
    """Write ``entries`` as JSONL (raw strings kept verbatim) and return the path."""
    path = tmp_path / "transcript.jsonl"
    lines: list[str] = []
    for entry in entries:
        lines.append(entry if isinstance(entry, str) else json.dumps(entry))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _usage_entry(model: str, **usage: int) -> dict:
    return {"message": {"model": model, "usage": usage}}


# --------------------------------------------------------------------------- #
# detect_auth_mode (pure, table-driven)
# --------------------------------------------------------------------------- #


def test_detect_auth_mode_five_hour_only_is_max() -> None:
    payload = _payload(rate_limits={"five_hour": {"used_percentage": 42.0, "resets_at": 1}})
    assert sl.detect_auth_mode(payload, saw_usage=False) == "max"


def test_detect_auth_mode_seven_day_only_is_max() -> None:
    payload = _payload(rate_limits={"seven_day": {"used_percentage": 5.0, "resets_at": 1}})
    assert sl.detect_auth_mode(payload, saw_usage=True) == "max"


def test_detect_auth_mode_both_windows_is_max() -> None:
    payload = _payload(
        rate_limits={
            "five_hour": {"used_percentage": 42.0, "resets_at": 1},
            "seven_day": {"used_percentage": 5.0, "resets_at": 2},
        }
    )
    assert sl.detect_auth_mode(payload, saw_usage=True) == "max"


def test_detect_auth_mode_no_rate_limits_with_usage_is_api() -> None:
    assert sl.detect_auth_mode(_payload(), saw_usage=True) == "api"


def test_detect_auth_mode_no_rate_limits_no_usage_is_pending() -> None:
    assert sl.detect_auth_mode(_payload(), saw_usage=False) == "pending"


def test_detect_auth_mode_falsy_rate_limits_treated_as_absent() -> None:
    assert sl.detect_auth_mode(_payload(rate_limits={}), saw_usage=True) == "api"
    assert sl.detect_auth_mode(_payload(rate_limits=None), saw_usage=True) == "api"


def test_detect_auth_mode_sdk_shape_still_max() -> None:
    """Regression guard: a present ``rate_limits`` keyed off presence, not inner fields.

    The SDK ``RateLimitInfo`` shape (``status``/``utilization``) has no window
    keys, but it is still a truthy ``rate_limits`` dict ⇒ subscription.
    """
    payload = _payload(rate_limits={"status": "allowed", "utilization": 0.42})
    assert sl.detect_auth_mode(payload, saw_usage=False) == "max"


# --------------------------------------------------------------------------- #
# scan_transcript
# --------------------------------------------------------------------------- #


def test_scan_transcript_missing_inputs_return_zeros() -> None:
    for arg in (None, "", "/nonexistent/path/transcript.jsonl"):
        stats = sl.scan_transcript(arg)
        assert stats.cost_usd == 0.0
        assert stats.assistant_usage_count == 0


def test_scan_transcript_counts_usage_and_computes_cost(tmp_path: Path) -> None:
    path = _transcript(
        tmp_path,
        [
            _usage_entry("claude-opus-4-8", input_tokens=1000, output_tokens=500),
            _usage_entry(
                "claude-sonnet-5",
                input_tokens=2000,
                cache_creation_input_tokens=1000,
                cache_read_input_tokens=4000,
                output_tokens=100,
            ),
        ],
    )
    stats = sl.scan_transcript(str(path))
    assert stats.assistant_usage_count == 2
    # opus-4-8 ($5/$25): (1000*5 + 500*25)/1e6 = 0.0175
    # sonnet-5 ($2/$10): (2000*2 + 1000*2*1.25 + 4000*2*0.10 + 100*10)/1e6 = 0.0083
    assert stats.cost_usd == 0.0175 + 0.0083


def test_scan_transcript_skips_malformed_and_blank_lines(tmp_path: Path) -> None:
    path = _transcript(
        tmp_path,
        [
            "not json at all",
            "",
            "   ",
            _usage_entry("claude-opus-4-8", input_tokens=1000, output_tokens=0),
        ],
    )
    stats = sl.scan_transcript(str(path))
    assert stats.assistant_usage_count == 1
    assert stats.cost_usd == 0.005  # 1000*5/1e6


def test_scan_transcript_ignores_entries_without_usage(tmp_path: Path) -> None:
    path = _transcript(
        tmp_path,
        [
            {"message": {"model": "claude-opus-4-8"}},  # no usage
            {"type": "summary"},  # no message
            _usage_entry("claude-opus-4-8", input_tokens=1000, output_tokens=0),
        ],
    )
    stats = sl.scan_transcript(str(path))
    assert stats.assistant_usage_count == 1


# --------------------------------------------------------------------------- #
# format_auth_badge
# --------------------------------------------------------------------------- #


def test_format_auth_badge_labels_and_colors() -> None:
    subscription_badge = sl.format_auth_badge("max")
    api_badge = sl.format_auth_badge("api")
    pending_badge = sl.format_auth_badge("pending")

    assert "[auth:subscription]" in subscription_badge
    assert subscription_badge.startswith(sl.GREEN)
    assert "[auth:api]" in api_badge
    assert api_badge.startswith(sl.YELLOW)
    assert "[auth:pending]" in pending_badge
    assert pending_badge.startswith(sl.DIM)


# --------------------------------------------------------------------------- #
# generate_status_line (integration over the pure layer)
# --------------------------------------------------------------------------- #


def test_generate_status_line_subscription_badge_is_additive(tmp_path: Path) -> None:
    path = _transcript(tmp_path, [_usage_entry("claude-opus-4-8", input_tokens=1000, output_tokens=500)])
    payload = _payload(
        rate_limits={"five_hour": {"used_percentage": 42.0, "resets_at": 1}},
        transcript_path=str(path),
        session_id="abc123",
    )
    out = sl.generate_status_line(payload)
    # Badge precedes the model segment.
    assert out.index("[auth:subscription]") < out.index("[Opus 5]")
    # Nothing regressed: context bar, %, tokens-left, session id, and cost all still render.
    assert "12.5%" in out
    assert "used" in out
    assert "left" in out
    assert "abc123" in out
    assert "$" in out


def test_generate_status_line_api_badge(tmp_path: Path) -> None:
    path = _transcript(tmp_path, [_usage_entry("claude-opus-4-8", input_tokens=1000, output_tokens=500)])
    payload = _payload(transcript_path=str(path))
    out = sl.generate_status_line(payload)
    assert "[auth:api]" in out


def test_generate_status_line_empty_payload_renders_pending() -> None:
    out = sl.generate_status_line({})
    assert "[auth:pending]" in out


# --------------------------------------------------------------------------- #
# main robustness (CLI semantics — subprocess per CLAUDE.md carve-out)
# --------------------------------------------------------------------------- #


def test_main_invalid_json_exits_zero() -> None:
    result = subprocess.run(  # noqa: S603
        ["uv", "run", "--script", str(SCRIPT)],
        input="not json",
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert result.stdout.strip() != ""
