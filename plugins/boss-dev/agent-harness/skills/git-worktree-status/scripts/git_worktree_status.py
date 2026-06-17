#!/usr/bin/env -S uv run --script --quiet
# /// script
# requires-python = ">=3.13"
# dependencies = ["rich"]
# ///
"""Report the status of background verification jobs in a git worktree.

Standalone PEP 723 script — run it from inside a worktree::

    uv run git_worktree_status.py

It reads the ``.worktree-logs/*.log`` files written by the language setup in
the ``git-worktree`` skill (e.g. ``tests.log``, ``typecheck.log``,
``build.log``) and reports each as ``PASS``/``FAIL``/``RUNNING``/``NOT_RUN``
using language-neutral markers — no JS/TS assumptions.

The parsing (``parse_log_status``) and detection (``in_worktree``) logic is
pure and unit tested; the IO layer locates the worktree and reads the logs.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from rich.console import Console

LOG_DIR = ".worktree-logs"

# Log filename -> human label, in display order.
LOG_LABELS: tuple[tuple[str, str], ...] = (
    ("typecheck.log", "Type check"),
    ("tests.log", "Tests"),
    ("build.log", "Build"),
)

_STATUS_STYLE = {
    "PASS": "green",
    "FAIL": "red",
    "RUNNING": "yellow",
    "NOT_RUN": "dim",
}


# ---------------------------------------------------------------------------
# Pure functions
# ---------------------------------------------------------------------------


def in_worktree(git_common_dir: str) -> bool:
    """Return ``True`` if the common git dir indicates we are inside a worktree."""
    return ".git/worktrees" in git_common_dir.replace("\\", "/")


def parse_log_status(log_text: str) -> str:
    """Classify a verification log as ``PASS``/``FAIL``/``RUNNING``/``NOT_RUN``.

    Uses language-neutral markers so it works across pytest, vitest, tsc,
    basedpyright, cargo, and go output. Empty text means the job never ran.
    """
    text = log_text.strip()
    if not text:
        return "NOT_RUN"
    lowered = text.lower()

    # Numeric counts decide first: "0 failed" / "0 errors" are passes.
    for pattern in (r"(\d+)\s+failed", r'"numfailedtests"\s*:\s*(\d+)', r"(\d+)\s+errors?\b"):
        if match := re.search(pattern, lowered):
            return "FAIL" if int(match.group(1)) > 0 else "PASS"

    # Non-numeric hard-failure signals.
    fail_markers = (
        "traceback (most recent call last)",
        "error ts",
        "panic:",
        "fatal:",
        "build failed",
        "failed",
    )
    if any(marker in lowered for marker in fail_markers):
        return "FAIL"

    # Success signals.
    pass_markers = ("passed", "build succeeded", "success", "no issues", " ok")
    if any(marker in lowered for marker in pass_markers):
        return "PASS"

    # Log exists but shows no terminal marker yet.
    return "RUNNING"


def format_status_report(*, worktree_path: str, branch: str, results: dict[str, str]) -> str:
    """Format a plain-text status report for the given check results."""
    lines = [
        f"Worktree status: {worktree_path}",
        f"Branch: {branch}",
        "",
        "Checks:",
    ]
    if not results:
        lines.append("  (no background jobs found — NOT_RUN)")
    else:
        width = max(len(label) for label in results)
        for label, status in results.items():
            lines.append(f"  {label:<{width}}  {status}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# IO layer
# ---------------------------------------------------------------------------


def _git(args: list[str]) -> str | None:
    """Run a read-only git command, returning stripped stdout or ``None`` on error."""
    import subprocess

    proc = subprocess.run(  # noqa: S603
        ["git", *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return None
    return proc.stdout.strip()


def collect_results(log_dir: Path) -> dict[str, str]:
    """Map each known log's label to its parsed status (``NOT_RUN`` if absent)."""
    results: dict[str, str] = {}
    for filename, label in LOG_LABELS:
        log_path = log_dir / filename
        if log_path.is_file():
            results[label] = parse_log_status(log_path.read_text(encoding="utf-8", errors="replace"))
        else:
            results[label] = "NOT_RUN"
    return results


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    argparse.ArgumentParser(
        description="Report background verification status for the current worktree.",
    ).parse_args(argv)

    console = Console()
    common_dir = _git(["rev-parse", "--git-common-dir"])
    if common_dir is None:
        console.print("[red]Not a git repository.[/red]")
        return 1
    if not in_worktree(common_dir):
        console.print("[yellow]Not inside a worktree.[/yellow] Run this from a worktree directory.")
        return 1

    toplevel = _git(["rev-parse", "--show-toplevel"]) or "."
    branch = _git(["rev-parse", "--abbrev-ref", "HEAD"]) or "(detached)"
    results = collect_results(Path(toplevel) / LOG_DIR)

    console.print()
    console.print(f"[bold]Worktree status:[/bold] {toplevel}")
    console.print(f"Branch: [cyan]{branch}[/cyan]")
    console.print()
    console.print("Checks:")
    width = max(len(label) for _, label in LOG_LABELS)
    for _, label in LOG_LABELS:
        status = results[label]
        style = _STATUS_STYLE[status]
        console.print(f"  {label:<{width}}  [{style}]{status}[/{style}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
