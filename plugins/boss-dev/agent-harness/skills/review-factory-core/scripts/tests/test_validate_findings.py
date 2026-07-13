"""Tests for validate_findings.py — the gate that stops hallucinated anchors.

The single most important behavior here: a finding citing a line that does not exist
in the diff must be rejected. If that ever regresses, the factory starts posting
authoritative-looking comments on unrelated lines of someone's code.
"""

from __future__ import annotations

import json
from typing import Any

import validate_findings as vf

# a.py has real lines 10-12 on the RIGHT and 10 on the LEFT. Nothing else exists.
ANCHORS: vf.Anchors = {"a.py": {"LEFT": [10], "RIGHT": [10, 11, 12]}}


def finding(**over: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "role": "security",
        "file": "a.py",
        "line": 11,
        "side": "RIGHT",
        "severity": "critical",
        "title": "t",
        "body": "b",
    }
    base.update(over)
    return base


def jsonl(*records: dict[str, Any]) -> str:
    return "\n".join(json.dumps(r) for r in records) + "\n"


DONE: dict[str, Any] = {"type": "done", "counts": {"critical": 0, "moderate": 0, "nit": 0}}


class TestAnchorValidation:
    """The reason this script exists."""

    def test_real_anchor_is_accepted(self) -> None:
        assert vf.validate_record(finding(line=11), ANCHORS, "security") is None

    def test_line_outside_the_diff_is_rejected(self) -> None:
        err = vf.validate_record(finding(line=9999), ANCHORS, "security")
        assert err is not None and "hallucinated" in err

    def test_line_just_past_the_hunk_is_rejected(self) -> None:
        """Off-by-one is the most likely hallucination, so pin the boundary."""
        assert vf.validate_record(finding(line=12), ANCHORS, "security") is None
        assert vf.validate_record(finding(line=13), ANCHORS, "security") is not None

    def test_right_only_line_rejected_on_the_left_side(self) -> None:
        """Line 11 exists on RIGHT but not LEFT. Side is part of the anchor."""
        assert vf.validate_record(finding(line=11, side="LEFT"), ANCHORS, "security") is not None

    def test_unknown_file_is_rejected(self) -> None:
        err = vf.validate_record(finding(file="never/seen.py"), ANCHORS, "security")
        assert err is not None and "not in the diff" in err


class TestRecordValidation:
    def test_invalid_severity_is_rejected(self) -> None:
        err = vf.validate_record(finding(severity="warning"), ANCHORS, "security")
        assert err is not None and "invalid severity" in err

    def test_missing_required_field_is_rejected(self) -> None:
        record = finding()
        del record["title"]
        err = vf.validate_record(record, ANCHORS, "security")
        assert err is not None and "title" in err

    def test_bool_is_not_a_valid_line_number(self) -> None:
        """bool is a subclass of int in Python — reject it explicitly."""
        assert vf.validate_record(finding(line=True), ANCHORS, "security") is not None

    def test_role_must_match_its_findings_file(self) -> None:
        """A specialist writing findings attributed to another role breaks attribution."""
        err = vf.validate_record(finding(role="docs"), ANCHORS, "security")
        assert err is not None and "does not match" in err


class TestParseFindings:
    def test_malformed_line_does_not_discard_its_neighbors(self) -> None:
        """JSONL tolerance is the crash-survivability property. One bad line, not a lost file."""
        text = json.dumps(finding(line=10)) + "\n{ broken\n" + json.dumps(finding(line=12)) + "\n" + json.dumps(DONE)
        result = vf.parse_findings(text, ANCHORS, "security")
        assert len(result.valid) == 2
        assert len(result.errors) == 1
        assert result.done is True

    def test_missing_done_record_marks_the_role_unfinished(self) -> None:
        result = vf.parse_findings(jsonl(finding()), ANCHORS, "security")
        assert result.done is False
        assert result.ok is False
        assert any("did not finish" in e for e in result.errors)

    def test_empty_findings_with_done_is_a_complete_clean_review(self) -> None:
        """Finding nothing is a valid, successful outcome — not a failure."""
        result = vf.parse_findings(jsonl(DONE), ANCHORS, "security")
        assert result.ok is True
        assert result.valid == []

    def test_counts_are_by_severity(self) -> None:
        text = jsonl(
            finding(line=10, severity="critical"),
            finding(line=11, severity="nit"),
            finding(line=12, severity="nit"),
            DONE,
        )
        result = vf.parse_findings(text, ANCHORS, "security")
        assert result.counts() == {"critical": 1, "moderate": 0, "nit": 2}

    def test_rejected_records_are_not_counted(self) -> None:
        text = jsonl(finding(line=9999, severity="critical"), DONE)
        result = vf.parse_findings(text, ANCHORS, "security")
        assert result.counts()["critical"] == 0
        assert result.valid == []
