#!/usr/bin/env -S uv run --script --quiet
# /// script
# requires-python = ">=3.13"
# dependencies = [
#   "rich>=13.0.0",
# ]
# ///
"""Install the agent-harness status line into a project's ``.claude/settings.local.json``.

By default this writes the ``statusLine`` block into the *current project's*
``.claude/settings.local.json`` — a gitignored, highest-precedence settings file, so
the status line is scoped to this project and never committed. ``--settings PATH``
retargets any file (e.g. ``~/.claude/settings.json`` for a manual global install, or
``.claude/settings.json`` for a team-shared one).

The write is fail-closed: read → plan → back up → render → validate → atomic
``os.replace``. A file that cannot be parsed is never overwritten; a third-party
``statusLine`` is never clobbered without ``--force``. Every mutation is preceded by a
timestamped backup (outside the repo, under ``~/.claude/backups/…``) with a
``manifest.json``, so ``--restore`` reverts verbatim and ``--uninstall`` surgically
removes only our block.

``--restore`` always targets the **install-time pre-image**: the per-target ``latest``
pointer names the newest *pre-install* backup and is deliberately not advanced by
``--uninstall`` (whose backup is still written, so the post-install file remains
recoverable by hand). When that pre-image is "the file did not exist", restore deletes the
target — but only while the file still holds nothing but our own ``statusLine``. If the
user has since added other settings, or replaced the ``statusLine`` with a third-party
one, or the file no longer parses, restore refuses with exit 1 and points at
``--uninstall``; user-added configuration is never silently destroyed.

Usage:
    install_status_line.py                     # install into ./.claude/settings.local.json
    install_status_line.py --check             # dry run: print the plan, exit 1 on FOREIGN
    install_status_line.py --uninstall         # remove only our block
    install_status_line.py --restore           # revert the target to its pre-install state
    install_status_line.py --variant status_line_v6.py
    install_status_line.py --settings ~/.claude/settings.json   # manual global install

Exit codes: 0 success/no-op, non-zero on a refused or aborted write.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rich.console import Console

# A parsed settings file or statusLine block — an arbitrary JSON object.
JsonDict = dict[str, Any]

# Backups live outside any repo so they never appear in a git diff.
BACKUP_ROOT = Path.home() / ".claude" / "backups" / "agent-harness-status-line"
LATEST_POINTER = "latest"
MANIFEST_NAME = "manifest.json"
SETTINGS_REL = Path(".claude") / "settings.local.json"
DEFAULT_VARIANT = "status_line_v10.py"
STATUS_LINES_DIR = "status_lines"
PLUGIN_DIR_NAME = "agent-harness"
DEFAULT_INDENT = 2

# Plan kinds.
INSTALL = "install"
CURRENT = "current"
REPLACE_OURS = "replace-ours"
FOREIGN = "foreign"
UNINSTALL = "uninstall"

console = Console()


@dataclass(frozen=True)
class Plan:
    """Pure classification of a settings dict against the desired ``statusLine`` block."""

    kind: str
    existing: JsonDict | None = None


# --------------------------------------------------------------------------- #
# Pure helpers
# --------------------------------------------------------------------------- #


def resolve_variant_path(variant: str, plugin_root: Path | None = None) -> Path:
    """Resolve a status-line variant filename to an absolute path under ``status_lines/``.

    ``variant`` comes from user config, so it is untrusted: a path separator or ``..``
    is rejected outright. An unknown filename raises ``FileNotFoundError``.
    """
    if "/" in variant or "\\" in variant or ".." in variant:
        msg = f"invalid variant name (no path separators or '..'): {variant!r}"
        raise ValueError(msg)
    root = plugin_root or Path(__file__).resolve().parent.parent
    path = (root / STATUS_LINES_DIR / variant).resolve()
    if not path.is_file():
        msg = f"status-line variant not found: {path}"
        raise FileNotFoundError(msg)
    return path


def build_status_line_block(script_path: Path) -> JsonDict:
    """Build the ``statusLine`` block for a resolved (absolute) variant path."""
    return {"type": "command", "command": f'uv run "{script_path}"', "padding": 0}


def _command_path(block: JsonDict) -> Path | None:
    """Extract the script path from a ``uv run "<path>"`` command, if present."""
    command = block.get("command")
    if not isinstance(command, str):
        return None
    match = re.search(r'uv run(?:\s+--\S+)*\s+"([^"]+)"', command)
    if match:
        return Path(match.group(1))
    # Fall back to the last whitespace-delimited token (unquoted paths).
    tokens = command.split()
    return Path(tokens[-1]) if tokens else None


def is_ours(block: JsonDict) -> bool:
    """True if a ``statusLine`` block points into this plugin's ``status_lines/`` dir.

    Matched structurally (``…/agent-harness/status_lines/<file>``) so it holds for both
    a repo checkout and a marketplace install regardless of the absolute prefix.
    """
    path = _command_path(block)
    if path is None:
        return False
    parts = path.parts
    for i in range(len(parts) - 2):
        if parts[i] == PLUGIN_DIR_NAME and parts[i + 1] == STATUS_LINES_DIR:
            return True
    return False


def plan(settings: JsonDict, desired: JsonDict) -> Plan:
    """Classify an install with no I/O."""
    existing = settings.get("statusLine")
    if existing is None:
        return Plan(INSTALL)
    if existing == desired:
        return Plan(CURRENT, existing)
    if is_ours(existing):
        return Plan(REPLACE_OURS, existing)
    return Plan(FOREIGN, existing)


def sniff_indent(text: str) -> int:
    """Leading-space count of the first indented line; ``DEFAULT_INDENT`` if none."""
    for line in text.splitlines():
        stripped = line.lstrip(" ")
        if stripped and stripped != line:
            return len(line) - len(stripped)
    return DEFAULT_INDENT


def _slug(settings_path: Path) -> str:
    """Stable, readable, per-target slug of a settings path (backups never collide)."""
    resolved = str(settings_path.resolve())
    digest = hashlib.sha256(resolved.encode("utf-8")).hexdigest()[:12]
    return f"{settings_path.name}-{digest}"


def backup_dir_for(settings_path: Path, backup_root: Path) -> Path:
    """Per-target backup directory: ``backup_root / <slug>``."""
    return backup_root / _slug(settings_path)


def _variant_from_block(block: JsonDict) -> str:
    path = _command_path(block)
    return path.name if path is not None else ""


# --------------------------------------------------------------------------- #
# Backup / restore engine
# --------------------------------------------------------------------------- #


def _read_settings(settings_path: Path) -> JsonDict:
    """Parse the settings file. Raises ``ValueError`` on a present-but-unparseable file.

    An absent file yields ``{}`` (a fresh install target).
    """
    if not settings_path.exists():
        return {}
    text = settings_path.read_text(encoding="utf-8")
    if text.strip() == "":
        msg = "settings file is empty"
        raise ValueError(msg)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        msg = f"settings file is not valid JSON: {exc}"
        raise ValueError(msg) from exc
    if not isinstance(data, dict):
        msg = "settings file is not a JSON object"
        raise ValueError(msg)
    return data


def _next_timestamp_dir(parent: Path) -> Path:
    """A fresh timestamped dir under ``parent``, adding ``-1``/``-2``… on collision."""
    base = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    candidate = parent / base
    suffix = 1
    while candidate.exists():
        candidate = parent / f"{base}-{suffix}"
        suffix += 1
    return candidate


def write_backup(settings_path: Path, backup_root: Path, plan_kind: str, variant: str) -> Path:
    """Back up the current settings file (if any) and record a manifest.

    The ``latest`` pointer names the *restore target*, so it only advances for backups
    that capture a pre-install state. An ``uninstall`` backup is still written (it is the
    only copy of the post-install file) but must not become the restore target: doing so
    made ``install → uninstall → restore`` re-add the status-line block instead of
    reverting to the original settings.
    """
    target_dir = backup_dir_for(settings_path, backup_root)
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp_dir = _next_timestamp_dir(target_dir)
    stamp_dir.mkdir(parents=True)

    existed = settings_path.exists()
    backup_path: Path | None = None
    if existed:
        backup_path = stamp_dir / settings_path.name
        shutil.copy2(settings_path, backup_path)

    manifest = {
        "settings_path": str(settings_path.resolve()),
        "existed": existed,
        "backup_path": str(backup_path) if backup_path is not None else None,
        "plan_kind": plan_kind,
        "variant": variant,
        "version": "1",
    }
    (stamp_dir / MANIFEST_NAME).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    if plan_kind != UNINSTALL:
        (target_dir / LATEST_POINTER).write_text(stamp_dir.name + "\n", encoding="utf-8")
    return stamp_dir


def _atomic_write(settings_path: Path, data: JsonDict, indent: int) -> None:
    """Render, validate the rendered string round-trips, then atomically replace."""
    rendered = json.dumps(data, indent=indent) + "\n"
    json.loads(rendered)  # prove it round-trips before any bytes touch the target
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = settings_path.parent / f"{settings_path.name}.{os.getpid()}.tmp"
    try:
        tmp.write_text(rendered, encoding="utf-8")
        os.replace(tmp, settings_path)
    finally:
        if tmp.exists():
            tmp.unlink()


def execute(settings_path: Path, backup_root: Path, desired: JsonDict, *, force: bool = False) -> int:
    """Install ``desired`` as the ``statusLine`` block. Ordered, fail-closed."""
    try:
        settings = _read_settings(settings_path)
    except ValueError as exc:
        console.print(f"[red]Refusing to write:[/red] {exc} ({settings_path})")
        return 1

    existing_text = settings_path.read_text(encoding="utf-8") if settings_path.exists() else ""
    indent = sniff_indent(existing_text)

    outcome = plan(settings, desired)
    if outcome.kind == CURRENT:
        console.print(f"[green]Already installed[/green] — nothing to do ({settings_path}).")
        return 0
    if outcome.kind == FOREIGN and not force:
        existing_cmd = (outcome.existing or {}).get("command", "<unknown>")
        console.print(
            f"[red]A different statusLine is already set[/red] ({settings_path}):\n  {existing_cmd}\n"
            "Re-run with --force to replace it (the original is backed up)."
        )
        return 1

    variant = _variant_from_block(desired)
    write_backup(settings_path, backup_root, outcome.kind, variant)

    settings["statusLine"] = desired
    _atomic_write(settings_path, settings, indent)
    console.print(f"[green]Installed[/green] statusLine → {settings_path} ({outcome.kind}).")
    return 0


def uninstall(settings_path: Path, backup_root: Path, *, force: bool = False) -> int:
    """Remove the ``statusLine`` block, but only when it is ours (or ``--force``)."""
    try:
        settings = _read_settings(settings_path)
    except ValueError as exc:
        console.print(f"[red]Refusing to write:[/red] {exc} ({settings_path})")
        return 1

    existing = settings.get("statusLine")
    if existing is None:
        console.print(f"[yellow]No statusLine set[/yellow] — nothing to uninstall ({settings_path}).")
        return 0
    if not is_ours(existing) and not force:
        console.print(
            f"[red]The statusLine is not ours[/red] ({settings_path}); refusing to remove it. "
            "Re-run with --force to remove it anyway."
        )
        return 1

    variant = _variant_from_block(existing)
    write_backup(settings_path, backup_root, UNINSTALL, variant)

    indent = sniff_indent(settings_path.read_text(encoding="utf-8"))
    del settings["statusLine"]
    _atomic_write(settings_path, settings, indent)
    console.print(f"[green]Removed[/green] statusLine ({settings_path}).")
    return 0


def _delete_refusal_reason(target: Path) -> str | None:
    """Why deleting ``target`` would destroy user data — ``None`` when deletion is safe.

    Only reached when the target did not exist before install, i.e. every byte in it was
    written by us *unless* the user added something afterwards. Deletion is safe only when
    the file still holds nothing but our own ``statusLine`` block.
    """
    if not target.exists():
        return None
    try:
        data = _read_settings(target)
    except ValueError as exc:
        return str(exc)
    added = sorted(key for key in data if key != "statusLine")
    if added:
        return f"it now holds settings added since install: {', '.join(added)}"
    existing = data.get("statusLine")
    if existing is not None and not is_ours(existing):
        return "its statusLine is no longer ours"
    return None


def restore(settings_path: Path, backup_root: Path, *, yes: bool = False) -> int:
    """Revert the target to its latest pre-install state (verbatim copy, or delete)."""
    target_dir = backup_dir_for(settings_path, backup_root)
    pointer = target_dir / LATEST_POINTER
    if not pointer.is_file():
        console.print(f"[yellow]No backup found[/yellow] — nothing to restore ({settings_path}).")
        return 0

    stamp_dir = target_dir / pointer.read_text().strip()
    manifest_file = stamp_dir / MANIFEST_NAME
    if not manifest_file.is_file():
        console.print(f"[yellow]Backup manifest missing[/yellow] — nothing to restore ({stamp_dir}).")
        return 0

    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    target = Path(manifest["settings_path"])

    if not manifest["existed"]:
        refusal = _delete_refusal_reason(target)
        if refusal is not None:
            console.print(
                f"[red]Refusing to delete {target}[/red]: {refusal}.\n"
                "Run --uninstall instead to remove only our statusLine block."
            )
            return 1
        console.print(f"[bold]Restore[/bold] will DELETE {target} (it did not exist before install).")
    else:
        console.print(f"[bold]Restore[/bold] will OVERWRITE {target} with the pre-install backup.")
    if not yes and not sys.stdin.isatty():
        console.print("[red]Refusing to restore non-interactively without --yes.[/red]")
        return 1

    if not manifest["existed"]:
        if target.exists():
            target.unlink()
        console.print(f"[green]Restored[/green] — deleted {target}.")
        return 0

    backup_path = Path(manifest["backup_path"])
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(backup_path, target)
    console.print(f"[green]Restored[/green] {target} from {backup_path}.")
    return 0


def check(settings_path: Path, desired: JsonDict) -> int:
    """Dry run: print the plan kind. Exit 1 on FOREIGN (or an unparsable file), else 0."""
    try:
        settings = _read_settings(settings_path)
    except ValueError as exc:
        console.print(f"[red]{exc}[/red] ({settings_path})")
        return 1
    outcome = plan(settings, desired)
    console.print(f"[bold]{outcome.kind}[/bold] — {settings_path}")
    return 1 if outcome.kind == FOREIGN else 0


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Install the agent-harness status line into a project's .claude/settings.local.json.",
    )
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--check", action="store_true", help="dry run: print the plan, exit 1 on a foreign statusLine")
    action.add_argument("--uninstall", action="store_true", help="remove only our statusLine block")
    action.add_argument("--restore", action="store_true", help="revert the target to its pre-install state")

    parser.add_argument("--variant", default=DEFAULT_VARIANT, help=f"status-line filename (default: {DEFAULT_VARIANT})")
    parser.add_argument(
        "--settings",
        type=Path,
        default=Path.cwd() / SETTINGS_REL,
        help="target settings file (default: ./.claude/settings.local.json)",
    )
    parser.add_argument("--backup-root", type=Path, default=BACKUP_ROOT, help="root for timestamped backups")
    parser.add_argument("--force", action="store_true", help="replace/remove a foreign statusLine")
    parser.add_argument(
        "--yes", action="store_true", help="proceed without prompts (required for non-interactive restore)"
    )
    args = parser.parse_args(argv)

    settings_path: Path = args.settings
    backup_root: Path = args.backup_root

    if args.restore:
        return restore(settings_path, backup_root, yes=args.yes)
    if args.uninstall:
        return uninstall(settings_path, backup_root, force=args.force)

    try:
        variant_path = resolve_variant_path(args.variant)
    except (ValueError, FileNotFoundError) as exc:
        console.print(f"[red]{exc}[/red]")
        return 1
    desired = build_status_line_block(variant_path)

    if args.check:
        return check(settings_path, desired)
    return execute(settings_path, backup_root, desired, force=args.force)


if __name__ == "__main__":
    sys.exit(main())
