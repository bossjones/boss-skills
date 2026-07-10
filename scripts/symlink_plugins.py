#!/usr/bin/env -S uv run --script --quiet
# /// script
# requires-python = ">=3.13"
# dependencies = [
#   "rich>=13.0.0",
# ]
# ///
"""Mirror plugin components into ``.claude/`` via relative symlinks (local dogfooding).

``boss-skills`` ships plugins from ``plugins/<category>/<plugin>/`` to a marketplace,
but the repo's own ``.claude/`` dev environment historically kept *separate copies*
of that content, which drift silently. This script makes ``plugins/`` the single
source of truth: ``.claude/{skills,commands,agents,hooks,output-styles,status_lines}``
become **relative symlinks** into the matching plugin components, so working in this
repo exercises the exact bytes marketplace users install.

Granularity:
    skills/ ................ symlink each immediate subdirectory (``<skill>/`` is atomic).
    everything else ........ symlink each *leaf file*, recreating intermediate dirs as
                             real directories (handles nested ``agents/team/x.md`` and
                             ``hooks/validators/y.py``); ``.claude/commands`` is one shared
                             namespace fed by several plugins, so file-level is required.

Safety:
    Any *real* (non-symlink) target that has a plugin source is moved into a timestamped
    backup dir under ``.backups/symlink-plugins/<ts>/`` and recorded in ``manifest.json``
    before the symlink is created. ``.claude/`` items with **no** plugin source (orphans)
    are never touched. ``--restore`` consumes the latest manifest to return the tree to
    its pre-run state.

Usage:
    scripts/symlink_plugins.py                 # back up + create the mirror
    scripts/symlink_plugins.py --check         # dry run + verify existing links (CI/pre-commit)
    scripts/symlink_plugins.py --restore       # undo: remove links, move originals back
    scripts/symlink_plugins.py --copy          # copy instead of symlink (symlink-hostile FS)
    scripts/symlink_plugins.py --components skills,commands   # subset (default: all six)

Exit codes: 0 success/consistent, 1 problem detected (broken link, drift, failed verify).
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import shutil
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from rich.console import Console

_NUL_BYTE = b"\x00"

REPO_ROOT = Path(__file__).resolve().parent.parent

# Component dirs mirrored from plugins/ into .claude/. Order is stable/informational.
ALL_COMPONENTS: tuple[str, ...] = (
    "skills",
    "commands",
    "agents",
    "hooks",
    "output-styles",
    "status_lines",
)

# Component whose immediate subdirectories are the atomic unit (dir-level symlink).
DIR_LEVEL_COMPONENT = "skills"
SKILL_MARKER = "SKILL.md"

# Never mirror these names / suffixes (build junk, not shipped content).
IGNORE_NAMES: frozenset[str] = frozenset({"__pycache__", ".DS_Store"})
IGNORE_SUFFIXES: tuple[str, ...] = (".pyc",)

BACKUP_ROOT_REL = Path(".backups") / "symlink-plugins"
LATEST_POINTER = "latest"
MANIFEST_NAME = "manifest.json"

# Action kinds.
CREATE = "create"
SKIP = "skip"
REPOINT = "repoint"
BACKUP_REPLACE = "backup+replace"
CONFLICT = "conflict"
ORPHAN_LEFT = "orphan-left"

console = Console()


@dataclass(frozen=True)
class Action:
    """One planned operation for a single ``.claude/`` target."""

    component: str
    kind: str
    target: Path  # absolute path under .claude/
    source: Path | None  # absolute path under plugins/ (None for orphan-left)
    detail: str = ""


@dataclass
class RunResult:
    """Outcome of executing a plan."""

    backup_dir: Path | None = None
    created: list[Action] = field(default_factory=list)
    backed_up: list[Action] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)


def _is_ignored(name: str) -> bool:
    return name in IGNORE_NAMES or name.endswith(IGNORE_SUFFIXES)


def _rel_to_repo(path: Path, repo_root: Path) -> str:
    """Repo-relative POSIX string, for stable manifest storage.

    Resolves the *parent* chain but never the leaf, so a path that is itself a
    symlink (e.g. a target we just created) is not followed back to its source.
    """
    leaf = path.parent.resolve() / path.name
    return leaf.relative_to(repo_root.resolve()).as_posix()


def discover_plugins(repo_root: Path) -> list[Path]:
    """Return local plugin roots (dirs holding ``.claude-plugin/plugin.json``), sorted.

    Sorting by repo-relative path makes collision resolution deterministic: the first
    plugin to claim a leaf name wins; later claimants are reported as ``conflict``.
    External ``git-subdir`` plugins have no local dir and are simply absent.
    """
    roots = [manifest.parent.parent for manifest in repo_root.glob("plugins/*/*/.claude-plugin/plugin.json")]
    return sorted(roots, key=lambda p: _rel_to_repo(p, repo_root))


def _iter_sources(plugin_root: Path, component: str) -> list[tuple[str, Path]]:
    """Yield ``(rel_key, source_path)`` pairs for one plugin's component dir.

    ``rel_key`` is the path *within* the component dir and becomes the target's path
    within ``.claude/<component>/``. For skills that is the immediate subdir name; for
    every other component it is the leaf file's relative path (so nested dirs survive).
    """
    comp_dir = plugin_root / component
    if not comp_dir.is_dir():
        return []

    pairs: list[tuple[str, Path]] = []
    if component == DIR_LEVEL_COMPONENT:
        for child in sorted(comp_dir.iterdir()):
            # A skill is defined by its SKILL.md; ignore runtime/data dirs (e.g. logs/).
            if child.is_dir() and not _is_ignored(child.name) and (child / SKILL_MARKER).is_file():
                pairs.append((child.name, child))
    else:
        for path in sorted(comp_dir.rglob("*")):
            if not path.is_file():
                continue
            if any(_is_ignored(part) for part in path.relative_to(comp_dir).parts):
                continue
            if _is_ignored(path.name):
                continue
            pairs.append((path.relative_to(comp_dir).as_posix(), path))
    return pairs


def _intended_link(source: Path, target: Path) -> str:
    """Relative symlink string from *target* to *source*."""
    return os.path.relpath(source, start=target.parent)


def _classify(target: Path, source: Path) -> str:
    """Classify an existing (or absent) target against its intended source."""
    if not target.exists() and not target.is_symlink():
        return CREATE
    if target.is_symlink():
        try:
            current = os.readlink(target)
        except OSError:
            return REPOINT
        return SKIP if current == _intended_link(source, target) else REPOINT
    # A real file or directory occupying the slot.
    return BACKUP_REPLACE


def _read_text_or_none(path: Path) -> list[str] | None:
    """UTF-8 lines (keepends) for a readable text file; None if binary/missing/undecodable."""
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    if _NUL_BYTE in raw:
        return None
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None
    return text.splitlines(keepends=True)


def diff_files(source: Path, target: Path) -> list[str]:
    """Unified diff lines, target's current content -> source's content.

    ``[]`` if identical. Falls back to raw byte-equality when either side is
    binary/undecodable, so identical binaries never falsely report "differ".
    """
    source_lines = _read_text_or_none(source)
    target_lines = _read_text_or_none(target)
    if source_lines is None or target_lines is None:
        try:
            source_bytes = source.read_bytes()
            target_bytes = target.read_bytes()
        except OSError:
            return [f"binary files {_display(target)} and {_display(source)} differ (unreadable)\n"]
        if source_bytes == target_bytes:
            return []
        return [f"binary files {_display(target)} and {_display(source)} differ\n"]

    diff = list(
        difflib.unified_diff(
            target_lines,
            source_lines,
            fromfile=_display(target),
            tofile=_display(source),
        )
    )
    return diff


def _list_files(root: Path) -> dict[str, Path]:
    """rel-POSIX-path -> abs Path for every non-ignored file under *root*."""
    if not root.is_dir():
        return {}
    files: dict[str, Path] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(_is_ignored(part) for part in path.relative_to(root).parts):
            continue
        files[path.relative_to(root).as_posix()] = path
    return files


DIR_ONLY_IN_SOURCE = "only-in-source"
DIR_ONLY_IN_TARGET = "only-in-target"
DIR_DIFFERS = "differs"


@dataclass(frozen=True)
class DirDiffEntry:
    """One relative path's comparison result inside a recursive dir diff."""

    rel_path: str
    status: str  # DIR_ONLY_IN_SOURCE | DIR_ONLY_IN_TARGET | DIR_DIFFERS
    diff: list[str] = field(default_factory=list)  # only for DIR_DIFFERS


def diff_dirs(source: Path, target: Path) -> list[DirDiffEntry]:
    """Recursive dir comparison. Identical common files are omitted entirely."""
    source_files = _list_files(source)
    target_files = _list_files(target)
    entries: list[DirDiffEntry] = []

    for rel_path in sorted(source_files.keys() | target_files.keys()):
        in_source = rel_path in source_files
        in_target = rel_path in target_files
        if in_source and not in_target:
            entries.append(DirDiffEntry(rel_path, DIR_ONLY_IN_SOURCE))
        elif in_target and not in_source:
            entries.append(DirDiffEntry(rel_path, DIR_ONLY_IN_TARGET))
        else:
            diff = diff_files(source_files[rel_path], target_files[rel_path])
            if diff:
                entries.append(DirDiffEntry(rel_path, DIR_DIFFERS, diff))
    return entries


def diff_action(action: Action) -> list[str]:
    """Renderable diff lines for one action; ``[]`` when there's nothing to show."""
    if action.kind not in (BACKUP_REPLACE, REPOINT):
        return []
    source = action.source
    if source is None:
        return []
    target = action.target

    if action.kind == REPOINT:
        try:
            target.resolve(strict=True)
        except OSError:
            return [f"{_display(target)} → broken symlink, cannot diff\n"]

    source_is_dir = source.is_dir()
    target_is_dir = target.is_dir()
    if source_is_dir != target_is_dir:
        return [
            f"{_display(target)} → type mismatch: source is "
            f"{'a directory' if source_is_dir else 'a file'}, target is "
            f"{'a directory' if target_is_dir else 'a file'}\n"
        ]

    if source_is_dir:
        lines: list[str] = []
        for entry in diff_dirs(source, target):
            if entry.status == DIR_DIFFERS:
                lines.append(f"--- {entry.rel_path} ---\n")
                lines.extend(entry.diff)
            else:
                lines.append(f"{entry.rel_path}: {entry.status}\n")
        return lines

    return diff_files(source, target)


def plan_actions(
    repo_root: Path,
    plugins: list[Path],
    components: tuple[str, ...],
) -> list[Action]:
    """Build the full action list across *components* with no filesystem mutation."""
    claude_root = repo_root / ".claude"
    actions: list[Action] = []

    for component in components:
        comp_target_root = claude_root / component
        claimed: dict[str, Path] = {}  # rel_key -> winning source

        for plugin_root in plugins:  # already sorted → deterministic winner
            for rel_key, source in _iter_sources(plugin_root, component):
                target = comp_target_root / rel_key
                if rel_key in claimed:
                    actions.append(
                        Action(
                            component,
                            CONFLICT,
                            target,
                            source,
                            detail=f"already claimed by {_rel_to_repo(claimed[rel_key], repo_root)}",
                        )
                    )
                    continue
                claimed[rel_key] = source
                actions.append(Action(component, _classify(target, source), target, source))

        actions.extend(_orphan_actions(comp_target_root, component, claimed))

    return actions


def _orphan_actions(
    comp_target_root: Path,
    component: str,
    claimed: dict[str, Path],
) -> list[Action]:
    """Report existing ``.claude/`` items with no plugin source (left untouched)."""
    if not comp_target_root.is_dir():
        return []

    orphans: list[Action] = []
    if component == DIR_LEVEL_COMPONENT:
        for child in sorted(comp_target_root.iterdir()):
            if child.is_dir() and child.name not in claimed and not _is_ignored(child.name):
                orphans.append(Action(component, ORPHAN_LEFT, child, None))
    else:
        for path in sorted(comp_target_root.rglob("*")):
            if not (path.is_file() or path.is_symlink()):
                continue
            rel_key = path.relative_to(comp_target_root).as_posix()
            if rel_key not in claimed and not _is_ignored(path.name):
                orphans.append(Action(component, ORPHAN_LEFT, path, None))
    return orphans


def _mkdir_tracking(directory: Path, created_dirs: list[Path]) -> None:
    """``mkdir -p`` that records each directory it actually creates (for restore)."""
    missing: list[Path] = []
    cursor = directory
    while not cursor.exists():
        missing.append(cursor)
        cursor = cursor.parent
    for path in reversed(missing):
        path.mkdir()
        created_dirs.append(path)


def _place(source: Path, target: Path, *, copy: bool) -> None:
    """Create the link (or copy) at *target* pointing at *source*."""
    if copy:
        if source.is_dir():
            shutil.copytree(source, target)
        else:
            shutil.copy2(source, target)
    else:
        target.symlink_to(_intended_link(source, target), target_is_directory=source.is_dir())


def _verify_target(action: Action) -> str | None:
    """Return a problem string if a just-placed target does not resolve, else None."""
    target = action.target
    if action.component == DIR_LEVEL_COMPONENT:
        if not (target / SKILL_MARKER).exists():
            return f"{_display(target)} → missing {SKILL_MARKER}"
    elif not target.exists():
        return f"{_display(target)} → broken link"
    return None


def _display(path: Path) -> str:
    """Path shown to the user: repo-relative when possible (leaf not followed)."""
    try:
        leaf = path.parent.resolve() / path.name
        return leaf.relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def execute(
    repo_root: Path,
    actions: list[Action],
    *,
    copy: bool,
) -> RunResult:
    """Apply the plan: back up real targets, then create links/copies. Verify after."""
    mutating = [a for a in actions if a.kind in (CREATE, REPOINT, BACKUP_REPLACE)]
    conflicts = [a for a in actions if a.kind == CONFLICT]
    for conflict in conflicts:
        console.print(f"[yellow]conflict[/yellow] {_display(conflict.target)} — {conflict.detail}; skipped")

    result = RunResult()
    if not mutating:
        console.print("[green]Already in sync — nothing to do.[/green]")
        return result

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_dir = repo_root / BACKUP_ROOT_REL / timestamp
    backup_dir.mkdir(parents=True, exist_ok=True)
    result.backup_dir = backup_dir

    created_dirs: list[Path] = []
    manifest_entries: list[dict[str, str | None]] = []

    for action in mutating:
        source = action.source
        if source is None:  # defensive: create/repoint/backup+replace always carry a source
            continue
        target = action.target
        _mkdir_tracking(target.parent, created_dirs)

        backup_path: Path | None = None
        if action.kind == BACKUP_REPLACE:
            backup_path = backup_dir / _rel_to_repo(target, repo_root)
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(target), str(backup_path))
            result.backed_up.append(action)
        elif target.is_symlink():  # repoint: drop the stale link first
            target.unlink()

        _place(source, target, copy=copy)
        result.created.append(action)

        manifest_entries.append({
            "target": _rel_to_repo(target, repo_root),
            "action": action.kind,
            "source": _rel_to_repo(source, repo_root),
            "backup_path": _rel_to_repo(backup_path, repo_root) if backup_path else None,
            "copy": "true" if copy else "false",
        })

        problem = _verify_target(action)
        if problem:
            result.problems.append(problem)

    manifest = {
        "timestamp": timestamp,
        "copy": copy,
        "created_dirs": [_rel_to_repo(d, repo_root) for d in created_dirs],
        "entries": manifest_entries,
    }
    (backup_dir / MANIFEST_NAME).write_text(json.dumps(manifest, indent=2) + "\n")
    _write_latest(repo_root, backup_dir)
    return result


def _write_latest(repo_root: Path, backup_dir: Path) -> None:
    pointer = repo_root / BACKUP_ROOT_REL / LATEST_POINTER
    pointer.parent.mkdir(parents=True, exist_ok=True)
    pointer.write_text(_rel_to_repo(backup_dir, repo_root) + "\n")


def _read_latest(repo_root: Path) -> Path | None:
    pointer = repo_root / BACKUP_ROOT_REL / LATEST_POINTER
    if not pointer.is_file():
        return None
    backup_dir = repo_root / pointer.read_text().strip()
    return backup_dir if (backup_dir / MANIFEST_NAME).is_file() else None


def restore(repo_root: Path) -> int:
    """Undo the latest run: remove created links/copies, move backups back. Idempotent."""
    backup_dir = _read_latest(repo_root)
    if backup_dir is None:
        console.print("[yellow]No backup manifest found — nothing to restore.[/yellow]")
        return 0

    manifest = json.loads((backup_dir / MANIFEST_NAME).read_text())
    entries: list[dict[str, str | None]] = manifest["entries"]
    removed = restored = 0

    for entry in reversed(entries):  # reverse so nested targets clear before parents
        target = repo_root / str(entry["target"])
        if target.is_symlink() or target.exists():
            if target.is_symlink() or target.is_file():
                target.unlink()
            else:
                shutil.rmtree(target)
            removed += 1
        backup_rel = entry["backup_path"]
        if backup_rel:
            source_backup = repo_root / backup_rel
            if source_backup.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(source_backup), str(target))
                restored += 1

    _remove_created_dirs(repo_root, manifest.get("created_dirs", []))

    console.print(
        f"[green]Restored[/green] from {_display(backup_dir)}: "
        f"removed {removed} link(s), moved back {restored} original(s)."
    )
    return 0


def _remove_created_dirs(repo_root: Path, created_dirs: list[str]) -> None:
    """Remove directories the run created, deepest first, only when empty."""
    for rel in sorted(created_dirs, key=lambda r: r.count("/"), reverse=True):
        directory = repo_root / rel
        if directory.is_dir() and not any(directory.iterdir()):
            directory.rmdir()


def _scan_broken_links(repo_root: Path, components: tuple[str, ...]) -> list[str]:
    """Find managed symlinks under ``.claude/<component>`` that no longer resolve."""
    problems: list[str] = []
    claude_root = repo_root / ".claude"
    for component in components:
        comp_root = claude_root / component
        if not comp_root.is_dir():
            continue
        candidates = [comp_root, *comp_root.rglob("*")]
        for path in candidates:
            if path.is_symlink() and not path.exists():
                problems.append(f"{_display(path)} → broken link")
    return problems


def check(repo_root: Path, actions: list[Action], components: tuple[str, ...], *, show_diff: bool = False) -> int:
    """Print the plan and return non-zero on drift or broken managed links."""
    _print_plan(actions)
    if show_diff:
        _print_diffs(actions)

    problems: list[str] = _scan_broken_links(repo_root, components)
    problems += [
        f"{_display(a.target)} → symlink points to wrong source (repoint needed)" for a in actions if a.kind == REPOINT
    ]

    if problems:
        console.print("\n[red]Problems detected:[/red]")
        for problem in problems:
            console.print(f"  [red]•[/red] {problem}")
        return 1

    console.print("\n[green]No broken links or drift among existing managed symlinks.[/green]")
    return 0


def _print_diffs(actions: list[Action]) -> None:
    """Print content diffs for every action with a non-empty ``diff_action`` result."""
    for action in actions:
        lines = diff_action(action)
        if not lines or action.source is None:
            continue
        console.print(f"\n[bold]{_display(action.target)}[/bold] ← {_display(action.source)}")
        for line in lines:
            console.print(line, end="", markup=False, highlight=False)


def _print_plan(actions: list[Action]) -> None:
    """Print planned actions grouped by component with per-kind counts."""
    order = [CREATE, REPOINT, BACKUP_REPLACE, SKIP, CONFLICT, ORPHAN_LEFT]
    by_component: dict[str, list[Action]] = {}
    for action in actions:
        by_component.setdefault(action.component, []).append(action)

    for component, comp_actions in by_component.items():
        counts = {kind: sum(1 for a in comp_actions if a.kind == kind) for kind in order}
        summary = "  ".join(f"{kind}={counts[kind]}" for kind in order if counts[kind])
        console.print(f"\n[bold]{component}[/bold]  {summary or 'no components'}")
        for action in comp_actions:
            if action.kind in (SKIP, ORPHAN_LEFT):
                continue
            extra = f" ({action.detail})" if action.detail else ""
            console.print(f"  [cyan]{action.kind:<14}[/cyan] {_display(action.target)}{extra}")


def _print_run_summary(result: RunResult) -> None:
    console.print(
        f"\n[green]Done.[/green] created/repointed={len(result.created)}  "
        f"backed-up={len(result.backed_up)}"
        + (f"  backup_dir={_display(result.backup_dir)}" if result.backup_dir else "")
    )


def _parse_components(raw: str | None) -> tuple[str, ...]:
    if not raw:
        return ALL_COMPONENTS
    requested = [c.strip() for c in raw.split(",") if c.strip()]
    unknown = [c for c in requested if c not in ALL_COMPONENTS]
    if unknown:
        msg = f"unknown component(s): {', '.join(unknown)} (valid: {', '.join(ALL_COMPONENTS)})"
        raise SystemExit(msg)
    return tuple(requested)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Symlink plugin components into .claude/ for local dogfooding.",
    )
    parser.add_argument(
        "--check", action="store_true", help="dry run: print plan, verify links, exit non-zero on drift"
    )
    parser.add_argument(
        "--diff",
        action="store_true",
        help="show content diffs for backup+replace/repoint actions (dry run; "
        "pair with --check to also gate the exit code on drift)",
    )
    parser.add_argument("--restore", action="store_true", help="undo the latest run from its backup manifest")
    parser.add_argument("--copy", action="store_true", help="copy files instead of symlinking (symlink-hostile FS)")
    parser.add_argument("--components", help=f"comma-separated subset (default: {','.join(ALL_COMPONENTS)})")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT, help="repo root (default: script's repo)")
    parser.add_argument("--yes", action="store_true", help="reserved: proceed without prompts (non-interactive)")
    args = parser.parse_args(argv)

    repo_root: Path = args.repo_root.resolve()

    if args.restore:
        return restore(repo_root)

    components = _parse_components(args.components)
    plugins = discover_plugins(repo_root)
    if not plugins:
        console.print("[yellow]No local plugins found under plugins/*/*/.claude-plugin/plugin.json[/yellow]")
        return 0

    actions = plan_actions(repo_root, plugins, components)

    if args.check or args.diff:
        exit_code = check(repo_root, actions, components, show_diff=args.diff)
        return exit_code if args.check else 0

    result = execute(repo_root, actions, copy=args.copy)
    _print_run_summary(result)
    if result.problems:
        console.print("\n[red]Post-run verification failed:[/red]")
        for problem in result.problems:
            console.print(f"  [red]•[/red] {problem}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
