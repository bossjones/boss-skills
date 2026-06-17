#!/usr/bin/env -S uv run --script --quiet
# /// script
# requires-python = ">=3.13"
# dependencies = ["rich"]
# ///
"""Clean up stale git worktrees: remove merged ones, review unmerged ones.

Standalone PEP 723 script — run it from anywhere in the repo::

    uv run git_worktree_clean.py [--dry-run] [--all] [--force]

Default (no flags) removes only worktrees whose branch is merged into the main
branch. ``--all`` also removes unmerged worktrees (use with care), ``--force``
skips git's dirty-state guard, and ``--dry-run`` previews without changes.

The porcelain parsing, classification, and size formatting are pure functions
(unit tested); the IO layer runs git and walks directories. Disk-size
accounting is language-neutral: it skips symlinks (e.g. a shared
``node_modules``) and the ``.git`` metadata, with no hardcoded stack excludes.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import TypedDict

from rich.console import Console

PROTECTED_BRANCHES = ("main", "master", "develop", "staging", "production")


class WorktreeRecord(TypedDict):
    """A single entry from ``git worktree list --porcelain``."""

    path: str
    head: str | None
    branch: str | None
    detached: bool
    is_main: bool


# ---------------------------------------------------------------------------
# Pure functions
# ---------------------------------------------------------------------------


def parse_worktree_list_porcelain(text: str) -> list[WorktreeRecord]:
    """Parse ``git worktree list --porcelain`` into worktree records.

    Each record has ``path``, ``head``, ``branch`` (short name or ``None`` when
    detached), ``detached`` (bool), and ``is_main`` (bool — the first entry).
    """
    entries: list[WorktreeRecord] = []
    current: WorktreeRecord | None = None
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.startswith("worktree "):
            if current is not None:
                entries.append(current)
            current = {
                "path": line[len("worktree ") :],
                "head": None,
                "branch": None,
                "detached": False,
                "is_main": False,
            }
        elif line.startswith("HEAD ") and current is not None:
            current["head"] = line[len("HEAD ") :]
        elif line.startswith("branch ") and current is not None:
            current["branch"] = line[len("branch ") :].removeprefix("refs/heads/")
        elif line == "detached" and current is not None:
            current["detached"] = True
    if current is not None:
        entries.append(current)
    for index, entry in enumerate(entries):
        entry["is_main"] = index == 0
    return entries


def classify_worktree(branch: str | None, is_merged: bool, protected: tuple[str, ...]) -> str:
    """Classify a worktree as ``protected``/``merged``/``unmerged``."""
    if branch is not None and branch in protected:
        return "protected"
    if branch is None:
        return "unmerged"
    return "merged" if is_merged else "unmerged"


def format_size(num_bytes: int) -> str:
    """Format a byte count as a human-readable size (B/KB/MB/GB)."""
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


# ---------------------------------------------------------------------------
# IO layer
# ---------------------------------------------------------------------------


def run_git(args: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
    """Run a git command, returning ``(returncode, stdout, stderr)``."""
    proc = subprocess.run(  # noqa: S603
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def main_branch(root: Path) -> str:
    """Return the main branch name (``origin/HEAD`` short name, else ``main``)."""
    code, out, _ = run_git(["rev-parse", "--abbrev-ref", "origin/HEAD"], cwd=root)
    if code == 0 and out and out != "origin/HEAD":
        return out.removeprefix("origin/")
    return "main"


def is_merged(branch: str, base: str, root: Path) -> bool:
    """Return ``True`` if ``branch`` is an ancestor of ``base``."""
    code, _, _ = run_git(["merge-base", "--is-ancestor", branch, base], cwd=root)
    return code == 0


def directory_size(path: Path) -> int:
    """Return on-disk size in bytes, skipping symlinks and ``.git`` metadata."""
    total = 0
    for entry in path.rglob("*"):
        if entry.is_symlink():
            continue
        if ".git" in entry.parts:
            continue
        if entry.is_file():
            try:
                total += entry.stat().st_size
            except OSError:
                continue
    return total


def remove_worktree(path: str, branch: str | None, *, force: bool, merged: bool, root: Path) -> None:
    """Remove a worktree and delete its local branch."""
    args = ["worktree", "remove"]
    if force:
        args.append("--force")
    args.append(path)
    run_git(args, cwd=root)
    if branch:
        run_git(["branch", "-d" if merged else "-D", branch], cwd=root)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Clean up stale git worktrees (merged auto, unmerged with --all).",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview without making changes.")
    parser.add_argument("--all", action="store_true", help="Also remove unmerged worktrees.")
    parser.add_argument("--force", action="store_true", help="Skip git's dirty-state guard.")
    args = parser.parse_args(argv)

    console = Console()
    code, toplevel, _ = run_git(["rev-parse", "--show-toplevel"])
    if code != 0:
        console.print("[red]Not a git repository.[/red]")
        return 1
    root = Path(toplevel).resolve()
    base = main_branch(root)

    _, porcelain, _ = run_git(["worktree", "list", "--porcelain"], cwd=root)
    entries = parse_worktree_list_porcelain(porcelain)

    removed: list[tuple[str, str, int]] = []
    kept_unmerged: list[tuple[str, str | None]] = []
    kept_protected: list[tuple[str, str | None]] = []
    reclaimed = 0

    for entry in entries:
        if entry["is_main"]:
            continue
        path = entry["path"]
        branch = entry["branch"]
        merged = branch is not None and is_merged(branch, base, root)
        kind = classify_worktree(branch, merged, PROTECTED_BRANCHES)
        size = directory_size(Path(path)) if Path(path).exists() else 0

        if kind == "protected":
            kept_protected.append((path, branch))
            continue
        if kind == "unmerged" and not args.all:
            kept_unmerged.append((path, branch))
            continue
        # merged, or unmerged with --all
        if args.dry_run:
            removed.append((path, str(branch), size))
            reclaimed += size
            continue
        remove_worktree(path, branch, force=args.force, merged=merged, root=root)
        removed.append((path, str(branch), size))
        reclaimed += size

    if not args.dry_run:
        run_git(["worktree", "prune"], cwd=root)

    _print_report(console, removed, kept_unmerged, kept_protected, reclaimed, dry_run=args.dry_run)
    return 0


def _print_report(
    console: Console,
    removed: list[tuple[str, str, int]],
    kept_unmerged: list[tuple[str, str | None]],
    kept_protected: list[tuple[str, str | None]],
    reclaimed: int,
    *,
    dry_run: bool,
) -> None:
    """Print the cleanup summary."""
    console.print()
    header = "Dry run — no changes made" if dry_run else "Worktree cleanup report"
    console.print(f"[bold]=== {header} ===[/bold]")
    verb = "Would remove" if dry_run else "Removed"
    console.print(f"\n{verb} ({len(removed)}):")
    for path, branch, size in removed:
        console.print(f"  {path} ([cyan]{branch}[/cyan]) — {format_size(size)}")
    if kept_unmerged:
        console.print(f"\nKept (unmerged, {len(kept_unmerged)}) — use --all or /git-worktree-remove:")
        for path, branch in kept_unmerged:
            console.print(f"  {path} ([yellow]{branch}[/yellow])")
    if kept_protected:
        console.print(f"\nKept (protected, {len(kept_protected)}):")
        for path, branch in kept_protected:
            console.print(f"  {path} ({branch})")
    console.print(f"\n{'Potential space savings' if dry_run else 'Space reclaimed'}: {format_size(reclaimed)}")


if __name__ == "__main__":
    sys.exit(main())
