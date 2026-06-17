#!/usr/bin/env -S uv run --script --quiet
# /// script
# requires-python = ">=3.13"
# dependencies = ["rich"]
# ///
"""Analyze a repo and suggest a ``.worktreeinclude`` for worktree isolation.

Standalone PEP 723 script — run it from anywhere in the repo::

    uv run worktree_doctor.py          # print a suggestion (default)
    uv run worktree_doctor.py --write  # also write .worktreeinclude if absent

It scans the repo's gitignored files for env/secret/local-config candidates,
detects the project type(s), and prints a suggested ``.worktreeinclude`` plus
whether ``.claude/worktrees/`` is gitignored. By default it only *suggests*;
``--write`` opts in to creating the file (it never overwrites an existing one).

The scan/detect/suggest logic is pure and unit tested; the IO layer runs git
and reads/writes files.
"""

from __future__ import annotations

import argparse
import fnmatch
import subprocess
import sys
from pathlib import Path

from rich.console import Console

# Patterns for files that typically should follow a repo into each worktree.
DEFAULT_CANDIDATE_PATTERNS: tuple[str, ...] = (
    ".env",
    ".env.*",
    ".envrc",
    "*.local",
    "*.local.json",
    "settings.local.json",
    "secrets",
    "secrets.*",
    "secrets/*",
)

# Path segments that mark vendored / build output — never worktreeinclude candidates.
VENDOR_SEGMENTS: frozenset[str] = frozenset({
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "site-packages",
    "dist",
    "build",
    "target",
    "__pycache__",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
})

# Marker file -> project type, in canonical (Python-first) order.
_PROJECT_MARKERS: tuple[tuple[str, str], ...] = (
    ("pyproject.toml", "python"),
    ("package.json", "node"),
    ("Cargo.toml", "rust"),
    ("go.mod", "go"),
)


# ---------------------------------------------------------------------------
# Pure functions
# ---------------------------------------------------------------------------


def is_vendored_path(path: str) -> bool:
    """Return ``True`` if any path segment is a vendored / build-output dir."""
    return any(segment in VENDOR_SEGMENTS for segment in path.split("/"))


def scan_gitignored_candidates(gitignored_files: list[str], candidate_patterns: tuple[str, ...]) -> list[str]:
    """Return gitignored files matching a candidate pattern (deduped, order kept).

    Each pattern is matched against both the full repo-relative path and the
    file's basename, so ``*.local`` catches ``app.local`` and
    ``**/.claude/...`` style nesting is caught via the basename too. Vendored
    and build-output paths (``.venv``, ``node_modules``, …) are excluded.
    """
    matched: list[str] = []
    seen: set[str] = set()
    for path in gitignored_files:
        if is_vendored_path(path):
            continue
        basename = path.rsplit("/", 1)[-1]
        if any(fnmatch.fnmatch(path, pat) or fnmatch.fnmatch(basename, pat) for pat in candidate_patterns):
            if path not in seen:
                seen.add(path)
                matched.append(path)
    return matched


def detect_project_types(repo_files: list[str]) -> list[str]:
    """Return all detected project types from top-level marker files (canonical order)."""
    present = set(repo_files)
    return [project_type for marker, project_type in _PROJECT_MARKERS if marker in present]


def build_worktreeinclude_suggestion(candidates: list[str]) -> str:
    """Render a suggested ``.worktreeinclude`` from detected candidates."""
    header = (
        "# .worktreeinclude — files copied into each worktree (.gitignore glob syntax).\n"
        "# Only files BOTH matched here AND gitignored are copied.\n"
    )
    if candidates:
        body = "\n".join(candidates)
    else:
        body = (
            "# No gitignored env/secret/local-config files detected.\n"
            "# Common starting entries:\n"
            ".env\n"
            ".env.local\n"
            ".envrc"
        )
    return f"{header}{body}\n"


def gitignore_has_worktrees(gitignore_text: str) -> bool:
    """Return ``True`` if ``.gitignore`` already ignores ``.claude/worktrees/``."""
    for raw in gitignore_text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.lstrip("/").rstrip("/") == ".claude/worktrees":
            return True
    return False


# ---------------------------------------------------------------------------
# IO layer
# ---------------------------------------------------------------------------


def run_git(args: list[str], cwd: Path | None = None) -> tuple[int, str]:
    """Run a read-only git command, returning ``(returncode, stdout)``."""
    proc = subprocess.run(  # noqa: S603
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode, proc.stdout.strip()


def list_gitignored_files(root: Path) -> list[str]:
    """Return repo-relative paths of gitignored files."""
    code, out = run_git(["ls-files", "--others", "--ignored", "--exclude-standard"], cwd=root)
    if code != 0:
        return []
    return [line for line in out.splitlines() if line]


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Analyze the repo and suggest a .worktreeinclude for worktree isolation.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write .worktreeinclude if it does not already exist (default: suggest only).",
    )
    args = parser.parse_args(argv)

    console = Console()
    code, toplevel = run_git(["rev-parse", "--show-toplevel"])
    if code != 0:
        console.print("[red]Not a git repository.[/red]")
        return 1
    root = Path(toplevel).resolve()

    gitignored = list_gitignored_files(root)
    candidates = scan_gitignored_candidates(gitignored, DEFAULT_CANDIDATE_PATTERNS)
    project_types = detect_project_types([p.name for p in root.iterdir()])
    suggestion = build_worktreeinclude_suggestion(candidates)

    gitignore_path = root / ".gitignore"
    gitignore_text = gitignore_path.read_text(encoding="utf-8") if gitignore_path.is_file() else ""
    worktrees_ignored = gitignore_has_worktrees(gitignore_text)

    console.print()
    console.print("[bold]worktree-doctor[/bold]")
    types_label = ", ".join(project_types) if project_types else "none detected"
    console.print(f"  Project type(s): {types_label}")
    if worktrees_ignored:
        console.print("  .claude/worktrees/ in .gitignore: [green]yes[/green]")
    else:
        console.print("  .claude/worktrees/ in .gitignore: [yellow]no — add it[/yellow]")
    console.print(f"  Candidate files found: [bold]{len(candidates)}[/bold]")
    console.print()
    console.print("[bold]Suggested .worktreeinclude:[/bold]")
    console.print(suggestion.rstrip("\n"))

    include_path = root / ".worktreeinclude"
    if args.write:
        if include_path.exists():
            console.print("\n[yellow].worktreeinclude already exists — not overwriting.[/yellow]")
        else:
            include_path.write_text(suggestion, encoding="utf-8")
            console.print(f"\n[green]Wrote[/green] {include_path}")
    else:
        console.print("\n[dim]Run with --write to create .worktreeinclude.[/dim]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
