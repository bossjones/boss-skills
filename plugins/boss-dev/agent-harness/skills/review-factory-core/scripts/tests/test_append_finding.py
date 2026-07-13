"""Tests for append_finding.py — the only sanctioned write path for specialist findings.

Written against CLI semantics (exit codes, stderr, what lands on disk), so the script is
invoked via subprocess per the repo testing convention for stdlib-only PEP 723 CLIs. The
contract under test is the fix for the write-path deadlock: an agent gets exactly one
deterministic command shape, a hallucinated anchor is rejected *at write time* (before it
lands), and the terminal done-record's counts come from the file, never the agent's say-so.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "append_finding.py"

MANIFEST: dict[str, Any] = {
    "review_id": "r1",
    "roles": ["security", "docs"],
    "anchors": {"src/db/queries.py": {"LEFT": [5], "RIGHT": [7, 8]}},
}


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "manifest.json").write_text(json.dumps(MANIFEST))
    return ws


def run(ws: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(ws), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def append_good(ws: Path, **over: str) -> subprocess.CompletedProcess[str]:
    base = {
        "--role": "security",
        "--file": "src/db/queries.py",
        "--line": "7",
        "--side": "RIGHT",
        "--severity": "critical",
        "--title": "SQL injection",
        "--body": "f-string into cursor.execute",
    }
    base.update(over)
    flat = [item for pair in base.items() for item in pair]
    return run(ws, *flat)


def findings_lines(ws: Path, role: str = "security") -> list[dict[str, Any]]:
    path = ws / "findings" / f"{role}.jsonl"
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


class TestGoodAnchor:
    def test_appends_exactly_one_json_line(self, workspace: Path) -> None:
        proc = append_good(workspace)
        assert proc.returncode == 0, proc.stderr
        [record] = findings_lines(workspace)
        assert record["file"] == "src/db/queries.py"
        assert record["line"] == 7
        assert record["severity"] == "critical"
        assert record["role"] == "security"

    def test_append_is_additive(self, workspace: Path) -> None:
        """Two calls -> two lines. Truncation here would silently lose findings."""
        assert append_good(workspace).returncode == 0
        assert append_good(workspace, **{"--line": "8", "--severity": "nit"}).returncode == 0
        assert len(findings_lines(workspace)) == 2

    def test_optional_fields_are_carried(self, workspace: Path) -> None:
        proc = append_good(workspace, **{"--confidence": "low", "--suggestion-patch": "    safe(query)"})
        assert proc.returncode == 0
        [record] = findings_lines(workspace)
        assert record["confidence"] == "low"
        assert record["suggestion_patch"] == "    safe(query)"

    def test_left_side_anchor_is_accepted(self, workspace: Path) -> None:
        proc = append_good(workspace, **{"--line": "5", "--side": "LEFT"})
        assert proc.returncode == 0, proc.stderr


class TestRejection:
    """The point of the script: a bad record never lands, and the agent is told why."""

    def test_hallucinated_anchor_rejected_nonzero_and_nothing_written(self, workspace: Path) -> None:
        proc = append_good(workspace, **{"--line": "9999"})
        assert proc.returncode == 1
        assert "not in the diff" in proc.stderr
        assert findings_lines(workspace) == []

    def test_right_only_line_rejected_on_the_left(self, workspace: Path) -> None:
        proc = append_good(workspace, **{"--side": "LEFT"})  # line 7 exists only on RIGHT
        assert proc.returncode == 1
        assert findings_lines(workspace) == []

    def test_file_not_in_the_diff_is_rejected(self, workspace: Path) -> None:
        proc = append_good(workspace, **{"--file": "never/seen.py", "--line": "1"})
        assert proc.returncode == 1
        assert "not in the diff" in proc.stderr

    def test_invalid_severity_is_rejected(self, workspace: Path) -> None:
        proc = append_good(workspace, **{"--severity": "warning"})
        assert proc.returncode == 1
        assert "severity" in proc.stderr
        assert findings_lines(workspace) == []

    def test_role_not_on_the_roster_is_refused(self, workspace: Path) -> None:
        proc = append_good(workspace, **{"--role": "performance"})
        assert proc.returncode == 1
        assert "roster" in proc.stderr
        assert findings_lines(workspace, "performance") == []

    def test_rejection_does_not_corrupt_earlier_findings(self, workspace: Path) -> None:
        assert append_good(workspace).returncode == 0
        assert append_good(workspace, **{"--line": "9999"}).returncode == 1
        assert len(findings_lines(workspace)) == 1

    def test_missing_manifest_is_workspace_unusable(self, tmp_path: Path) -> None:
        proc = append_good(tmp_path / "nowhere")
        assert proc.returncode == 2


class TestDone:
    def test_counts_computed_from_the_file_not_the_agent(self, workspace: Path) -> None:
        append_good(workspace)  # critical
        append_good(workspace, **{"--line": "8", "--severity": "nit"})
        proc = run(workspace, "--role", "security", "--done")
        assert proc.returncode == 0, proc.stderr
        done = findings_lines(workspace)[-1]
        assert done["type"] == "done"
        assert done["counts"] == {"critical": 1, "moderate": 0, "nit": 1}

    def test_done_with_no_findings_is_a_valid_clean_review(self, workspace: Path) -> None:
        proc = run(workspace, "--role", "security", "--done")
        assert proc.returncode == 0, proc.stderr
        [done] = findings_lines(workspace)
        assert done == {"type": "done", "counts": {"critical": 0, "moderate": 0, "nit": 0}}

    def test_done_output_satisfies_the_downstream_gate(self, workspace: Path) -> None:
        """The full write path must produce a file validate_findings.py accepts verbatim."""
        append_good(workspace)
        run(workspace, "--role", "security", "--done")
        gate = subprocess.run(
            [sys.executable, str(SCRIPT.parent / "validate_findings.py"), str(workspace), "--role", "security"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert gate.returncode == 0, gate.stdout + gate.stderr
