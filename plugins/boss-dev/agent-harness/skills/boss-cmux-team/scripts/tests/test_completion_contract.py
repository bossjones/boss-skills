"""Regression tests for the boss-cmux-team completion sentinel contract."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent.parent
LEAD = (ROOT / "assets" / "roles" / "lead.md").read_text(encoding="utf-8")
WORKER_ROLES = ("plan", "build-be", "build-fe", "test")


def _bash(script: str, stdin: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.run(["bash", "-c", script], input=stdin, capture_output=True, text=True, check=False)


def _documented_pattern() -> str:
    """The exact double-quoted ``grep -Eq`` pattern from the lead's wait loop."""
    match = re.search(r'grep -Eq "(TASK-DONE: build-be [^"]+)"', LEAD)
    assert match, "wait-loop grep pattern not found in lead.md"
    assert not match.group(1).startswith("^"), "agents render output indented or bulleted"
    return match.group(1)


def _matches(screen: str, attempt_id: str, pattern: str | None = None) -> bool:
    result = _bash(f'ID="{attempt_id}"; grep -Eq "{pattern or _documented_pattern()}"', stdin=screen)
    assert result.returncode in (0, 1), result.stderr
    return result.returncode == 0


def test_stale_marker_from_previous_attempt_does_not_complete_a_new_dispatch() -> None:
    first, second = "1700000000-111", "1700000090-222"
    screen = (
        f"TASK-DONE: build-be #{first} | shipped /health, verified with curl\n"
        "> fix the failing test_health case. Attempt id: " + second + ". When finished, use ...\n"
        "working...\n"
    )

    assert _matches(screen, first)  # the old attempt's own marker still matches its id
    assert not _matches(screen, second)  # but cannot satisfy the new dispatch


def test_marker_for_the_current_attempt_completes_the_wait() -> None:
    first, second = "1700000000-111", "1700000090-222"
    screen = (
        f"TASK-DONE: build-be #{first} | shipped /health, verified with curl\n"
        "working on the retry...\n"
        f"TASK-DONE: build-be #{second} | fixed test_health — endpoints: GET /health, verified\n"
    )

    assert _matches(screen, second)


def test_marker_without_an_attempt_id_never_matches() -> None:
    assert not _matches("TASK-DONE: build-be | shipped\n", "1700000090-222")


@pytest.mark.parametrize("prefix", [" ", "  ", "⏺ ", "● ", "│ "])
def test_marker_rendered_with_agent_prefix_still_matches(prefix: str) -> None:
    """pi pads assistant text, Claude Code prefixes ``⏺ ``, Copilot CLI prefixes ``● ``."""
    screen = f"{prefix}TASK-DONE: build-be #1700000090-222 | shipped /health, verified with curl\n"
    assert _matches(screen, "1700000090-222")


def test_wait_loop_reads_enough_lines_to_see_the_marker() -> None:
    match = re.search(r'read-screen --surface "<ref>" --lines (\d+) \| grep -Eq', LEAD)
    assert match, "wait-loop read-screen not found in lead.md"
    assert int(match.group(1)) >= 20


def test_marker_from_another_worker_with_the_same_id_does_not_match() -> None:
    assert not _matches("TASK-DONE: build-fe #1700000090-222 | shipped\n", "1700000090-222")


def test_dispatched_prompt_echo_does_not_match_the_pattern() -> None:
    """The task message carries the id but must not spell a completion line."""
    send = re.search(r'cmux send --surface "<ref>" "(.+)"', LEAD)
    assert send, "dispatch line not found in lead.md"
    echoed = send.group(1).replace("$ID", "1700000090-222")

    assert not _matches(f"> {echoed}\n", "1700000090-222")
    assert "TASK-DONE" not in send.group(1)


def test_attempt_id_assignment_is_fresh_shell_syntax() -> None:
    assignment = re.search(r"^(ID=.+?)\s+#", LEAD, re.MULTILINE)
    assert assignment, "ID assignment not found in lead.md"

    result = _bash(f'{assignment.group(1)}; printf "%s" "$ID"')

    assert re.fullmatch(r"\d+-\d+", result.stdout), result.stdout


@pytest.mark.parametrize("role", WORKER_ROLES)
def test_worker_contract_requires_the_attempt_id(role: str) -> None:
    text = (ROOT / "assets" / "roles" / f"{role}.md").read_text(encoding="utf-8")

    assert f"TASK-DONE: {role} #<attempt-id> |" in text
    assert "copy it verbatim" in text
