"""Tests for score_run.py — the instrument that decides the bake-off.

If the cost math is wrong, the bake-off's verdict is wrong, so the arithmetic is
pinned here against hand-computed values rather than against the code's own output.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import score_run as sr

PRICING: dict[str, Any] = json.loads(Path(sr.PRICING).read_text())


class TestPricing:
    def test_longest_matching_prefix_wins(self) -> None:
        assert sr.rate_for("claude-opus-4-8", PRICING)["input"] == 15.0
        assert sr.rate_for("claude-sonnet-5", PRICING)["input"] == 3.0

    def test_unknown_model_prices_at_zero_rather_than_guessing(self) -> None:
        """A loud $0.00 says 'add this prefix'. A plausible invented rate says nothing."""
        assert sr.rate_for("some-future-model", PRICING) == {"input": 0.0, "output": 0.0}

    def test_cost_honors_cache_multipliers(self) -> None:
        """Hand-computed: cache reads are ~10x cheaper than fresh input. That's the whole point."""
        usage = sr.Usage(input=1_000_000, output=0, cache_write=0, cache_read=0)
        assert sr.cost_of(usage, "claude-sonnet-5", PRICING) == pytest.approx(3.0)

        cached = sr.Usage(input=0, output=0, cache_write=0, cache_read=1_000_000)
        assert sr.cost_of(cached, "claude-sonnet-5", PRICING) == pytest.approx(0.3)  # 3.0 * 0.1

        written = sr.Usage(input=0, output=0, cache_write=1_000_000, cache_read=0)
        assert sr.cost_of(written, "claude-sonnet-5", PRICING) == pytest.approx(3.75)  # 3.0 * 1.25

    def test_output_tokens_dominate(self) -> None:
        usage = sr.Usage(input=0, output=1_000_000)
        assert sr.cost_of(usage, "claude-opus-4-8", PRICING) == pytest.approx(75.0)


class TestCacheHitRate:
    """The metric that says whether context scoping is actually working."""

    def test_hit_rate_is_cache_reads_over_all_input(self) -> None:
        usage = sr.Usage(input=100, cache_write=100, cache_read=800)
        assert usage.cache_hit_rate == 0.8

    def test_no_input_is_zero_not_a_crash(self) -> None:
        assert sr.Usage().cache_hit_rate == 0.0


class TestUsageFromTranscript:
    def test_sums_assistant_usage_and_collects_models(self) -> None:
        lines = [
            json.dumps({
                "type": "assistant",
                "message": {
                    "model": "claude-sonnet-5",
                    "usage": {
                        "input_tokens": 10,
                        "output_tokens": 5,
                        "cache_creation_input_tokens": 2,
                        "cache_read_input_tokens": 100,
                    },
                },
            }),
            json.dumps({"type": "user", "message": {"content": "no usage here"}}),
            json.dumps({
                "type": "assistant",
                "message": {
                    "model": "claude-sonnet-5",
                    "usage": {"input_tokens": 1, "output_tokens": 3},
                },
            }),
        ]
        usage, models = sr.usage_from_transcript("\n".join(lines))
        assert usage.input == 11
        assert usage.output == 8
        assert usage.cache_read == 100
        assert models == {"claude-sonnet-5"}

    def test_partial_tail_line_is_skipped_not_fatal(self) -> None:
        """A transcript can be read while it is still being written."""
        text = json.dumps({"message": {"model": "m", "usage": {"output_tokens": 7}}}) + '\n{"partial": '
        usage, _ = sr.usage_from_transcript(text)
        assert usage.output == 7


class TestFindingsByRole:
    def test_counts_findings_per_role_ignoring_done_records(self, tmp_path: Path) -> None:
        findings = tmp_path / "findings"
        findings.mkdir()
        (findings / "security.jsonl").write_text(
            json.dumps({"severity": "critical"})
            + "\n"
            + json.dumps({"severity": "nit"})
            + "\n"
            + json.dumps({"type": "done", "counts": {}})
            + "\n"
        )
        (findings / "performance.jsonl").write_text(json.dumps({"type": "done", "counts": {}}) + "\n")

        yields = sr.findings_by_role(tmp_path)
        assert yields["security"] == {"critical": 1, "moderate": 0, "nit": 1}
        # The specialist that found nothing — the one that should get cut from the roster.
        assert yields["performance"] == {"critical": 0, "moderate": 0, "nit": 0}

    def test_missing_findings_dir_is_empty_not_an_error(self, tmp_path: Path) -> None:
        assert sr.findings_by_role(tmp_path) == {}
