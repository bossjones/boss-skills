#!/usr/bin/env -S uv run --script --quiet
# /// script
# requires-python = ">=3.13"
# dependencies = ["rich", "pathspec"]
# ///
"""Create an isolated git worktree under ``.claude/worktrees/<repo>-<name>/``.

Standalone PEP 723 script — run it with::

    uv run git_worktree.py <name> [--from <base>]

This mirrors Claude Code's native ``--worktree`` convention (worktrees live in
``.claude/worktrees/<value>/`` on branch ``worktree-<value>``) but prefixes the
directory with the repository name so multiple repos can share a flat layout.

It also replicates the ``.worktreeinclude`` copy step. A plain
``git worktree add`` does **not** process ``.worktreeinclude`` — only Claude's
native ``--worktree``/``EnterWorktree``/subagent worktrees do — so this script
copies the matched, gitignored files itself.

The logic is split into pure functions (naming, parsing, matching — unit
tested) and a thin IO layer around ``git``, file copies, and ``direnv``.

Note on secrets: ``.env`` / ``.envrc`` are copied byte-for-byte and never read,
printed, or logged. ``.envrc`` is a Claude protected path, so the copy may
prompt (or be declined) under ``default``/``acceptEdits``; the report calls that
out instead of failing silently.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

from rich.console import Console

# ---------------------------------------------------------------------------
# Shared conventions
# ---------------------------------------------------------------------------

PROTECTED_BRANCHES = ("main", "master", "develop", "staging", "production")
WORKTREE_ROOT = ".claude/worktrees"
GITIGNORE_ENTRY = ".claude/worktrees/"
NAME_PATTERN = re.compile(r"^[a-zA-Z0-9/_-]+$")

# Marker file -> project type, in priority order (Python first-class for this repo).
_PROJECT_MARKERS: tuple[tuple[str, str], ...] = (
    ("pyproject.toml", "python"),
    ("Cargo.toml", "rust"),
    ("go.mod", "go"),
    ("package.json", "node"),
)


# ---------------------------------------------------------------------------
# Pure functions (no side effects — unit tested)
# ---------------------------------------------------------------------------


def _origin_url(git_config_text: str) -> str | None:
    """Return the ``[remote "origin"] url`` from raw ``.git/config`` text, if any."""
    current_section = ""
    for raw in git_config_text.splitlines():
        line = raw.strip()
        if line.startswith("[") and line.endswith("]"):
            current_section = line
            continue
        if 'remote "origin"' in current_section and line.startswith("url"):
            _, _, value = line.partition("=")
            return value.strip()
    return None


def derive_repo_name(git_config_text: str, toplevel: str) -> str:
    """Derive the repo name from the origin URL, falling back to the toplevel basename.

    Handles ssh (``git@host:org/repo.git``) and https
    (``https://host/org/repo[.git]``) forms; the trailing ``.git`` is stripped.
    """
    url = _origin_url(git_config_text)
    if url:
        basename = re.split(r"[/:]", url.rstrip("/"))[-1]
        if basename.endswith(".git"):
            basename = basename[: -len(".git")]
        if basename:
            return basename
    return Path(toplevel).name


def build_worktree_dirname(repo: str, name: str) -> str:
    """Return ``<repo>-<name>``, avoiding a double ``<repo>-`` prefix."""
    prefix = f"{repo}-"
    if name.startswith(prefix):
        return name
    return f"{repo}-{name}"


def build_branch_name(name: str) -> str:
    """Return the worktree branch name ``worktree-<name>``."""
    return f"worktree-{name}"


def validate_name(name: str) -> bool:
    """Return ``True`` if ``name`` is a non-empty, safe worktree identifier."""
    return bool(name) and NAME_PATTERN.match(name) is not None


def gitignore_has_worktrees(gitignore_text: str) -> bool:
    """Return ``True`` if ``.gitignore`` already ignores ``.claude/worktrees/``."""
    for raw in gitignore_text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        normalized = line.lstrip("/").rstrip("/")
        if normalized == ".claude/worktrees":
            return True
    return False


def parse_worktreeinclude(text: str) -> list[str]:
    """Parse ``.worktreeinclude`` text into patterns (comments and blanks stripped)."""
    patterns: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        patterns.append(line)
    return patterns


def match_worktreeinclude(patterns: list[str], gitignored_files: list[str]) -> list[str]:
    """Return files that are **both** matched by a pattern and gitignored.

    Matching uses ``.gitignore`` glob semantics (via ``pathspec``), the same
    rules Claude's native ``.worktreeinclude`` processing uses. Iterating over
    ``gitignored_files`` enforces the "matched but not gitignored ⇒ skip" rule
    for free.
    """
    if not patterns:
        return []
    import pathspec

    spec = pathspec.PathSpec.from_lines("gitignore", patterns)
    return [path for path in gitignored_files if spec.match_file(path)]


def detect_project_type(filenames: list[str]) -> str:
    """Return the primary project type from top-level marker files.

    Returns one of ``python``/``rust``/``go``/``node``/``generic``. Python wins
    ties because it is first-class for this repo.
    """
    present = set(filenames)
    for marker, project_type in _PROJECT_MARKERS:
        if marker in present:
            return project_type
    return "generic"


# ---------------------------------------------------------------------------
# IO layer (git / filesystem / direnv) — thin wrappers
# ---------------------------------------------------------------------------


class WorktreeError(RuntimeError):
    """Raised when a worktree operation cannot proceed."""


def run_git(args: list[str], cwd: Path | None = None) -> str:
    """Run a git command and return its stripped stdout, raising on failure."""
    proc = subprocess.run(  # noqa: S603
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise WorktreeError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout.strip()


def repo_root() -> Path:
    """Return the repository toplevel as an absolute path."""
    return Path(run_git(["rev-parse", "--show-toplevel"])).resolve()


def read_git_config_text(root: Path) -> str:
    """Read raw ``.git/config`` text from the common git dir (worktree-safe)."""
    common_dir = run_git(["rev-parse", "--git-common-dir"], cwd=root)
    common_path = Path(common_dir)
    if not common_path.is_absolute():
        common_path = (root / common_path).resolve()
    config_path = common_path / "config"
    if not config_path.is_file():
        return ""
    return config_path.read_text(encoding="utf-8")


def list_gitignored_files(root: Path) -> list[str]:
    """Return repo-relative paths of gitignored files (not directories)."""
    out = run_git(
        ["ls-files", "--others", "--ignored", "--exclude-standard"],
        cwd=root,
    )
    return [line for line in out.splitlines() if line]


def resolve_base_ref(root: Path, override: str | None) -> str:
    """Return the base ref: explicit override, else ``origin/HEAD``, else ``HEAD``."""
    if override:
        return override
    try:
        origin_head = run_git(["rev-parse", "--abbrev-ref", "origin/HEAD"], cwd=root)
        if origin_head and origin_head != "origin/HEAD":
            return origin_head
    except WorktreeError:
        pass
    return "HEAD"


def branch_exists(root: Path, branch: str) -> bool:
    """Return ``True`` if a local branch already exists."""
    proc = subprocess.run(  # noqa: S603
        ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
        cwd=root,
        check=False,
    )
    return proc.returncode == 0


def ensure_gitignore_entry(root: Path) -> str:
    """Ensure ``.claude/worktrees/`` is gitignored. Return ``present``/``added``."""
    gitignore = root / ".gitignore"
    text = gitignore.read_text(encoding="utf-8") if gitignore.is_file() else ""
    if gitignore_has_worktrees(text):
        return "present"
    prefix = "" if text.endswith("\n") or not text else "\n"
    with gitignore.open("a", encoding="utf-8") as handle:
        handle.write(f"{prefix}{GITIGNORE_ENTRY}\n")
    return "added"


def create_worktree(root: Path, worktree_path: Path, branch: str, base_ref: str) -> None:
    """Create the worktree directory and branch from ``base_ref``."""
    worktree_path.parent.mkdir(parents=True, exist_ok=True)
    run_git(
        ["worktree", "add", str(worktree_path), "-b", branch, base_ref],
        cwd=root,
    )


def copy_worktreeinclude_files(root: Path, worktree_path: Path, files: list[str]) -> list[str]:
    """Copy matched gitignored files into the worktree, preserving structure.

    Files are copied byte-for-byte; their contents are never read or logged.
    """
    copied: list[str] = []
    for rel in files:
        src = root / rel
        if not src.is_file():
            continue
        dst = worktree_path / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied.append(rel)
    return copied


def run_direnv_allow(worktree_path: Path) -> bool:
    """Run ``direnv allow`` on the worktree if direnv is installed. Return success."""
    if shutil.which("direnv") is None:
        return False
    proc = subprocess.run(  # noqa: S603
        ["direnv", "allow", str(worktree_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode == 0


# ---------------------------------------------------------------------------
# Orchestration + report
# ---------------------------------------------------------------------------

_SETUP_REFERENCE = {
    "python": "references/setup-python.md",
    "node": "references/setup-node.md",
    "rust": "references/setup-rust.md",
    "go": "references/setup-go.md",
    "generic": "references/setup-generic.md",
}


def create(name: str, base_override: str | None, console: Console) -> int:
    """Create the worktree end-to-end and print a report. Return an exit code."""
    if not validate_name(name):
        console.print(
            f"[red]Invalid name '[bold]{name}[/bold]'.[/red] "
            r"Allowed characters: [cyan]a-z A-Z 0-9 / _ -[/cyan]"
        )
        return 2

    root = repo_root()
    repo = derive_repo_name(read_git_config_text(root), str(root))
    dirname = build_worktree_dirname(repo, name)
    branch = build_branch_name(name)
    worktree_path = root / WORKTREE_ROOT / dirname

    if branch_exists(root, branch):
        console.print(f"[red]Branch '[bold]{branch}[/bold]' already exists.[/red]")
        return 1
    if worktree_path.exists():
        console.print(f"[red]Worktree path already exists:[/red] {worktree_path}")
        return 1

    gitignore_status = ensure_gitignore_entry(root)
    base_ref = resolve_base_ref(root, base_override)
    create_worktree(root, worktree_path, branch, base_ref)

    # .worktreeinclude copy step (the part native `git worktree add` skips).
    include_file = root / ".worktreeinclude"
    copied: list[str] = []
    matched_missing = False
    if include_file.is_file():
        patterns = parse_worktreeinclude(include_file.read_text(encoding="utf-8"))
        matched = match_worktreeinclude(patterns, list_gitignored_files(root))
        copied = copy_worktreeinclude_files(root, worktree_path, matched)
        matched_missing = len(copied) < len(matched)

    direnv_ran = False
    if any(Path(rel).name == ".envrc" for rel in copied):
        direnv_ran = run_direnv_allow(worktree_path)

    project_type = detect_project_type([p.name for p in root.iterdir()])
    _print_report(
        console,
        worktree_path=worktree_path,
        branch=branch,
        base_ref=base_ref,
        gitignore_status=gitignore_status,
        copied=copied,
        matched_missing=matched_missing,
        direnv_ran=direnv_ran,
        project_type=project_type,
    )
    return 0


def _print_report(
    console: Console,
    *,
    worktree_path: Path,
    branch: str,
    base_ref: str,
    gitignore_status: str,
    copied: list[str],
    matched_missing: bool,
    direnv_ran: bool,
    project_type: str,
) -> None:
    """Print a human-readable creation report (never echoes file contents)."""
    console.print()
    console.print(f"[green]✓ Worktree ready[/green] at [bold]{worktree_path}[/bold]")
    console.print(f"  Branch:   [cyan]{branch}[/cyan] (from {base_ref})")
    if gitignore_status == "added":
        console.print(f"  .gitignore: added [cyan]{GITIGNORE_ENTRY}[/cyan]")

    if copied:
        console.print(f"  Copied .worktreeinclude files ([bold]{len(copied)}[/bold]):")
        for rel in copied:
            console.print(f"    • {rel}")
    if matched_missing:
        console.print(
            "  [yellow]Note: one or more matched files were not copied "
            "(e.g. a protected .envrc declined under default/acceptEdits).[/yellow]"
        )
    if any(Path(rel).name == ".envrc" for rel in copied):
        if direnv_ran:
            console.print("  direnv: [green]allowed[/green]")
        else:
            console.print("  direnv: [yellow]not run (direnv missing or declined)[/yellow]")

    reference = _SETUP_REFERENCE[project_type]
    console.print()
    console.print(f"  Detected project type: [bold]{project_type}[/bold]")
    console.print(f"  Next: follow [cyan]{reference}[/cyan] for dependency setup.")
    console.print()
    console.print("  Re-enter unattended (isolated env only):")
    console.print(f'    [dim]cd {worktree_path} && claude -p --permission-mode acceptEdits "<task>"[/dim]')


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Create an isolated git worktree under .claude/worktrees/<repo>-<name>/.",
    )
    parser.add_argument("name", help="Worktree name (becomes branch worktree-<name>).")
    parser.add_argument(
        "--from",
        dest="base",
        metavar="BASE",
        default=None,
        help="Base ref to branch from (default: origin/HEAD, else HEAD).",
    )
    args = parser.parse_args(argv)
    console = Console()
    try:
        return create(args.name, args.base, console)
    except WorktreeError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
