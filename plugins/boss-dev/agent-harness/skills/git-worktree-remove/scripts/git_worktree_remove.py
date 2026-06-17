#!/usr/bin/env -S uv run --script --quiet
# /// script
# requires-python = ">=3.13"
# dependencies = ["rich"]
# ///
"""Safely remove a single git worktree with branch-cleanup safety checks.

Standalone PEP 723 script — run it from anywhere in the repo::

    uv run git_worktree_remove.py <name_or_path> [--force] [--keep-branch] [--keep-remote]

Safety checks run before removal: protected branches are blocked, uncommitted
changes are warned about (use ``--force`` to override git's guard), and merge
status decides whether the local branch is deleted with ``-d`` or ``-D``.

Target resolution and safety predicates are pure functions (unit tested); the
IO layer runs git.
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


# ---------------------------------------------------------------------------
# Pure functions
# ---------------------------------------------------------------------------


def resolve_target(name_or_path: str, worktrees: list[WorktreeRecord]) -> WorktreeRecord | None:
    """Resolve a name/path/branch to a worktree record, or ``None`` if no match.

    Matches (in order): exact path, directory basename, exact branch name, then
    the bare-name form ``worktree-<name_or_path>``.
    """
    branch_form = f"worktree-{name_or_path}"
    for entry in worktrees:
        path = entry["path"]
        branch = entry["branch"]
        if name_or_path in (path, Path(path).name, branch) or branch == branch_form:
            return entry
    return None


def is_protected(branch: str | None, protected: tuple[str, ...]) -> bool:
    """Return ``True`` if the branch is in the protected set."""
    return branch is not None and branch in protected


def deletion_flag(*, merged: bool) -> str:
    """Return ``-d`` for a merged branch, ``-D`` to force-delete an unmerged one."""
    return "-d" if merged else "-D"


def parse_worktree_list_porcelain(text: str) -> list[WorktreeRecord]:
    """Parse ``git worktree list --porcelain`` into records (path/head/branch/detached)."""
    entries: list[WorktreeRecord] = []
    current: WorktreeRecord | None = None
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.startswith("worktree "):
            if current is not None:
                entries.append(current)
            current = {"path": line[len("worktree ") :], "head": None, "branch": None, "detached": False}
        elif line.startswith("HEAD ") and current is not None:
            current["head"] = line[len("HEAD ") :]
        elif line.startswith("branch ") and current is not None:
            current["branch"] = line[len("branch ") :].removeprefix("refs/heads/")
        elif line == "detached" and current is not None:
            current["detached"] = True
    if current is not None:
        entries.append(current)
    return entries


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


def has_uncommitted_changes(worktree_path: str) -> bool:
    """Return ``True`` if the worktree has uncommitted changes."""
    code, out, _ = run_git(["status", "--porcelain"], cwd=Path(worktree_path))
    return code == 0 and bool(out)


def remote_branch_exists(branch: str, root: Path) -> bool:
    """Return ``True`` if ``origin/<branch>`` exists on the remote."""
    code, out, _ = run_git(["ls-remote", "--heads", "origin", branch], cwd=root)
    return code == 0 and bool(out)


def main(argv: list[str] | None = None) -> int:  # noqa: C901
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Safely remove a single git worktree and clean up its branch.",
    )
    parser.add_argument("target", help="Worktree name, directory basename, branch, or path.")
    parser.add_argument("--force", action="store_true", help="Skip the uncommitted-changes guard.")
    parser.add_argument("--keep-branch", action="store_true", help="Remove the worktree but keep the branch.")
    parser.add_argument("--keep-remote", action="store_true", help="Do not delete the remote branch.")
    args = parser.parse_args(argv)

    console = Console()
    code, toplevel, _ = run_git(["rev-parse", "--show-toplevel"])
    if code != 0:
        console.print("[red]Not a git repository.[/red]")
        return 1
    root = Path(toplevel).resolve()

    _, porcelain, _ = run_git(["worktree", "list", "--porcelain"], cwd=root)
    worktrees = parse_worktree_list_porcelain(porcelain)
    target = resolve_target(args.target, worktrees)
    if target is None:
        console.print(f"[red]No worktree matches '[bold]{args.target}[/bold]'.[/red]")
        return 1

    path = target["path"]
    branch = target["branch"]

    if is_protected(branch, PROTECTED_BRANCHES):
        console.print(f"[red]BLOCKED:[/red] '{branch}' is a protected branch.")
        return 1

    if has_uncommitted_changes(path) and not args.force:
        console.print(f"[yellow]WARNING:[/yellow] worktree has uncommitted changes: {path}")
        console.print("  Commit them, or re-run with [bold]--force[/bold].")
        return 1

    base = main_branch(root)
    merged = bool(branch) and is_merged(str(branch), base, root)
    if branch and not merged:
        console.print(f"[yellow]Branch '{branch}' is NOT merged into {base}.[/yellow] Changes may be lost.")

    remove_args = ["worktree", "remove"]
    if args.force:
        remove_args.append("--force")
    remove_args.append(path)
    rc, _, err = run_git(remove_args, cwd=root)
    if rc != 0:
        console.print(f"[red]Failed to remove worktree:[/red] {err}")
        return 1
    console.print(f"[green]Removed worktree:[/green] {path}")

    if branch and not args.keep_branch:
        flag = deletion_flag(merged=merged)
        run_git(["branch", flag, str(branch)], cwd=root)
        console.print(f"  Local branch [cyan]{branch}[/cyan]: deleted ({'merged' if merged else 'forced'})")

    if branch and not args.keep_remote and remote_branch_exists(str(branch), root):
        run_git(["push", "origin", "--delete", str(branch)], cwd=root)
        console.print(f"  Remote branch [cyan]origin/{branch}[/cyan]: deleted")

    run_git(["worktree", "prune"], cwd=root)
    console.print("  References: pruned")
    return 0


if __name__ == "__main__":
    sys.exit(main())
