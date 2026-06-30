#!/usr/bin/env -S uv run --script --quiet
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Make a repo "agent-harness ready": gitignore + settings.local.json setup.

Standalone PEP 723 script — stdlib only, run it with::

    uv run setup_harness.py detect [--repo-root <path>]
    uv run setup_harness.py apply  [flags...]

The script does all deterministic work (detection, timestamped backups,
idempotent ``.gitignore`` updates, JSON-safe ``settings.local.json`` merges, and
post-write validation). It never decides policy on conflicting
``statusLine`` / ``outputStyle`` values — the calling skill collects those
decisions interactively and passes them as flags, so the interactive contract
stays where the user can see it.

Two modes:

- ``detect`` — prints a JSON report of current state to stdout. Read-only.
- ``apply`` — backup -> edit -> validate, driven by explicit flags.

Every modified file is copied to ``<file>.backup.<YYYYMMDD-HHMMSS>`` before being
written, and ``.claude/*.backup.*`` is part of the managed ``.gitignore`` block.
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# --- Managed .gitignore block -------------------------------------------------

MANAGED_BLOCK_START = "# >>> agent-harness managed (do not edit) >>>"
MANAGED_BLOCK_END = "# <<< agent-harness managed <<<"

# Runtime artifacts written by agent-harness hooks, plus the backups this script
# creates. The last two patterns ignore `<file>.backup.<timestamp>` files: settings
# backups live under `.claude/`, and `.gitignore` backups are written beside
# `.gitignore` at the repo root.
GITIGNORE_PATTERNS = [
    "logs/",
    ".claude/data/",
    "*.log",
    ".claude/*.backup.*",
    ".gitignore.backup.*",
]

# --- settings.local.json shape ------------------------------------------------

SCHEMA_URL = "https://json.schemastore.org/claude-code-settings.json"
PLUGIN_ID = "agent-harness@boss-skills"

# The plugin ships `status_lines/status_line_v10.py` at its root; ${CLAUDE_PLUGIN_ROOT}
# is left literal so Claude Code interpolates it at runtime.
STATUS_LINE = {
    "type": "command",
    "command": 'uv run "${CLAUDE_PLUGIN_ROOT}/status_lines/status_line_v10.py"',
    "padding": 0,
}

OUTPUT_STYLES = [
    "bullet-points",
    "genui",
    "html-structured",
    "markdown-focused",
    "table-based",
    "tts-summary",
    "ultra-concise",
    "yaml-structured",
]

SETTINGS_REL_PATH = Path(".claude") / "settings.local.json"


# --- Helpers ------------------------------------------------------------------


def timestamp() -> str:
    """Return a filesystem-safe timestamp like ``20260623-153012``."""
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def backup(path: Path) -> Path:
    """Copy ``path`` to ``<path>.backup.<timestamp>`` and return the new path.

    Only call this when a real change is about to be written.
    """
    dest = path.with_name(f"{path.name}.backup.{timestamp()}")
    shutil.copy2(path, dest)
    return dest


def _unified_diff(old: str, new: str, rel_path: str) -> str:
    """Return a git-style unified diff from ``old`` to ``new`` for ``rel_path``.

    Returns an empty string when the two texts are identical.
    """
    diff = difflib.unified_diff(
        old.splitlines(keepends=True),
        new.splitlines(keepends=True),
        fromfile=f"a/{rel_path}",
        tofile=f"b/{rel_path}",
    )
    return "".join(diff)


# --- .gitignore reconcile -----------------------------------------------------


def _non_comment_lines(text: str) -> set[str]:
    """Return the set of stripped, non-comment, non-empty lines in ``text``."""
    out: set[str] = set()
    for raw in text.splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            out.add(line)
    return out


def missing_patterns(text: str) -> list[str]:
    """Return managed patterns not already present as an exact line in ``text``."""
    present = _non_comment_lines(text)
    return [p for p in GITIGNORE_PATTERNS if p not in present]


def _render_managed_block(patterns: list[str]) -> str:
    body = "\n".join(patterns)
    return f"{MANAGED_BLOCK_START}\n{body}\n{MANAGED_BLOCK_END}"


def apply_gitignore(repo_root: Path, dry_run: bool) -> dict[str, object]:
    """Idempotently ensure the managed patterns are present in ``.gitignore``.

    Returns a result dict describing what changed (or would change).
    """
    path = repo_root / ".gitignore"
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    missing = missing_patterns(text)

    if not missing:
        return {"changed": False, "added": [], "backup": None}

    new_text = _merge_managed_block(text, missing)

    if dry_run:
        return {
            "changed": True,
            "added": missing,
            "backup": None,
            "dry_run": True,
            "diff": _unified_diff(text, new_text, ".gitignore"),
        }

    backup_path: Path | None = backup(path) if path.exists() else None
    path.write_text(new_text, encoding="utf-8")
    return {
        "changed": True,
        "added": missing,
        "backup": str(backup_path) if backup_path else None,
    }


def _merge_managed_block(text: str, missing: list[str]) -> str:
    """Insert/refresh the managed block, appending only ``missing`` patterns."""
    lines = text.splitlines()
    try:
        start = lines.index(MANAGED_BLOCK_START)
    except ValueError:
        start = -1

    if start != -1:
        # Find the matching end marker after start. If it's missing or misordered,
        # treat everything from start to EOF as the (malformed) block and rebuild a
        # single well-formed block — never append a second one beside an orphan.
        try:
            end = lines.index(MANAGED_BLOCK_END, start + 1)
        except ValueError:
            end = len(lines)
        body = [ln for ln in lines[start + 1 : end] if ln not in (MANAGED_BLOCK_START, MANAGED_BLOCK_END)]
        existing = _non_comment_lines("\n".join(body))
        to_add = [p for p in missing if p not in existing]
        new_block = [MANAGED_BLOCK_START, *body, *to_add, MANAGED_BLOCK_END]
        merged = lines[:start] + new_block + lines[end + 1 :]
        return "\n".join(merged) + "\n"

    # No existing block — append a fresh one.
    prefix = text
    if prefix and not prefix.endswith("\n"):
        prefix += "\n"
    if prefix and not prefix.endswith("\n\n"):
        prefix += "\n"
    return prefix + _render_managed_block(missing) + "\n"


# --- settings.local.json merge ------------------------------------------------


class SettingsError(RuntimeError):
    """Raised when settings cannot be safely loaded or written."""


def load_settings(path: Path) -> dict:
    """Parse existing settings or return ``{}``; abort on invalid JSON."""
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SettingsError(
            f"{path} contains invalid JSON ({exc}); refusing to overwrite. Fix or remove the file and re-run."
        ) from exc
    if not isinstance(data, dict):
        raise SettingsError(f"{path} must contain a JSON object, got {type(data).__name__}.")
    return data


def plan_settings(
    current: dict,
    status_line_action: str,
    output_style_action: str,
    enable_plugin: bool,
) -> tuple[dict, list[str]]:
    """Return ``(merged, changes)`` — a pure merge of the requested settings.

    ``status_line_action``: ``"set"`` or ``"skip"``.
    ``output_style_action``: a style name, or ``"skip"``.
    """
    merged = json.loads(json.dumps(current))  # deep copy
    changes: list[str] = []

    existing_schema = merged.get("$schema")
    if existing_schema is None:
        merged["$schema"] = SCHEMA_URL
        changes.append(f"set $schema -> {SCHEMA_URL}")
    elif existing_schema != SCHEMA_URL:
        changes.append(f"kept existing $schema ({existing_schema}) — not overwritten")

    if status_line_action == "set":
        desired = json.loads(json.dumps(STATUS_LINE))
        if merged.get("statusLine") != desired:
            merged["statusLine"] = desired
            changes.append("set statusLine -> agent-harness status_line_v10.py")

    if output_style_action != "skip" and merged.get("outputStyle") != output_style_action:
        merged["outputStyle"] = output_style_action
        changes.append(f"set outputStyle -> {output_style_action}")

    if enable_plugin:
        plugins = merged.get("enabledPlugins")
        if not isinstance(plugins, dict):
            plugins = {}
            merged["enabledPlugins"] = plugins
        if plugins.get(PLUGIN_ID) is not True:
            plugins[PLUGIN_ID] = True
            changes.append(f"enabled plugin {PLUGIN_ID}")

    return merged, changes


def apply_settings(
    repo_root: Path,
    status_line_action: str,
    output_style_action: str,
    enable_plugin: bool,
    dry_run: bool,
) -> dict[str, object]:
    """Merge requested settings into ``.claude/settings.local.json`` safely."""
    path = repo_root / SETTINGS_REL_PATH
    current = load_settings(path)
    merged, changes = plan_settings(current, status_line_action, output_style_action, enable_plugin)

    # Decide on the document, not the change log: notes like "kept existing $schema"
    # populate ``changes`` without mutating ``merged``, so writing on non-empty
    # ``changes`` would break the idempotent no-op contract.
    if merged == current:
        return {"changed": False, "changes": changes, "backup": None}

    payload = json.dumps(merged, indent=2) + "\n"

    if dry_run:
        old_text = path.read_text(encoding="utf-8") if path.exists() else ""
        return {
            "changed": True,
            "changes": changes,
            "backup": None,
            "dry_run": True,
            "diff": _unified_diff(old_text, payload, str(SETTINGS_REL_PATH)),
        }

    path.parent.mkdir(parents=True, exist_ok=True)
    backup_path: Path | None = backup(path) if path.exists() else None
    path.write_text(payload, encoding="utf-8")

    # Re-read and validate; restore from backup on failure.
    try:
        json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        if backup_path is not None:
            shutil.copy2(backup_path, path)
        raise SettingsError(f"wrote {path} but it failed to parse ({exc}); restored from backup.") from exc

    return {
        "changed": True,
        "changes": changes,
        "backup": str(backup_path) if backup_path else None,
    }


# --- environment readiness ----------------------------------------------------


def _which(name: str) -> bool:
    return shutil.which(name) is not None


def check_env() -> dict[str, object]:
    """Report (never block) on tools the harness expects: uv, python, gh."""
    results: dict[str, object] = {}

    results["uv"] = {
        "ok": _which("uv"),
        "hint": None if _which("uv") else "install uv: https://docs.astral.sh/uv/",
    }
    results["python3"] = {
        "ok": _which("python3"),
        "hint": None if _which("python3") else "install Python 3.11+",
    }

    gh_installed = _which("gh")
    gh_auth_ok = False
    if gh_installed:
        try:
            proc = subprocess.run(
                ["gh", "auth", "status"],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            gh_auth_ok = proc.returncode == 0
        except (OSError, subprocess.SubprocessError):
            gh_auth_ok = False
    if not gh_installed:
        gh_hint: str | None = "install GitHub CLI: https://cli.github.com/"
    elif not gh_auth_ok:
        gh_hint = "run `gh auth login` to authenticate"
    else:
        gh_hint = None
    results["gh"] = {"installed": gh_installed, "authenticated": gh_auth_ok, "hint": gh_hint}

    return results


# --- detect / apply commands --------------------------------------------------


def _plugin_enabled(settings: dict) -> bool:
    plugins = settings.get("enabledPlugins")
    return isinstance(plugins, dict) and plugins.get(PLUGIN_ID) is True


def cmd_detect(repo_root: Path) -> int:
    settings_path = repo_root / SETTINGS_REL_PATH
    try:
        settings = load_settings(settings_path)
        settings_error = None
    except SettingsError as exc:
        settings = {}
        settings_error = str(exc)

    gitignore_path = repo_root / ".gitignore"
    gitignore_text = gitignore_path.read_text(encoding="utf-8") if gitignore_path.exists() else ""

    # When settings can't be read, the derived fields are unknown — report them as
    # null rather than as `False`, so the skill surfaces the error instead of
    # prompting to "add" config that apply would then refuse to overwrite.
    report = {
        "repo_root": str(repo_root),
        "settings_exists": settings_path.exists(),
        "settings_error": settings_error,
        "has_schema": None if settings_error else settings.get("$schema") is not None,
        "has_status_line": None if settings_error else "statusLine" in settings,
        "has_output_style": None if settings_error else "outputStyle" in settings,
        "output_style": None if settings_error else settings.get("outputStyle"),
        "plugin_enabled": None if settings_error else _plugin_enabled(settings),
        "gitignore_missing": missing_patterns(gitignore_text),
        "output_styles": OUTPUT_STYLES,
        "env": check_env(),
    }
    json.dump(report, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


def cmd_apply(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()

    if args.output_style not in ("skip", *OUTPUT_STYLES):
        valid = ", ".join(OUTPUT_STYLES)
        print(
            f"error: --output-style must be 'skip' or one of: {valid}",
            file=sys.stderr,
        )
        return 2

    summary: dict[str, object] = {"repo_root": str(repo_root), "dry_run": args.dry_run}
    backups: list[str] = []

    try:
        # Fail fast: validate settings JSON before mutating .gitignore, so an
        # invalid settings.local.json can't leave a half-applied .gitignore behind.
        load_settings(repo_root / SETTINGS_REL_PATH)

        if args.gitignore:
            gi = apply_gitignore(repo_root, args.dry_run)
            summary["gitignore"] = gi
            if gi.get("backup"):
                backups.append(str(gi["backup"]))
        else:
            summary["gitignore"] = {"changed": False, "skipped": True}

        st = apply_settings(
            repo_root,
            status_line_action=args.status_line,
            output_style_action=args.output_style,
            enable_plugin=args.enable_plugin,
            dry_run=args.dry_run,
        )
        summary["settings"] = st
        if st.get("backup"):
            backups.append(str(st["backup"]))
    except SettingsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    summary["backups"] = backups
    json.dump(summary, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_detect = sub.add_parser("detect", help="print current state as JSON (read-only)")
    p_detect.add_argument("--repo-root", default=os.getcwd())

    p_apply = sub.add_parser("apply", help="apply backup -> edit -> validate")
    p_apply.add_argument("--repo-root", default=os.getcwd())
    p_apply.add_argument(
        "--gitignore",
        action="store_true",
        help="update .gitignore with the managed block",
    )
    p_apply.add_argument(
        "--status-line",
        choices=["set", "skip"],
        default="skip",
        help="set or skip the harness statusLine",
    )
    p_apply.add_argument(
        "--output-style",
        default="skip",
        help="an output style name, or 'skip'",
    )
    p_apply.add_argument(
        "--enable-plugin",
        action="store_true",
        help=f"ensure enabledPlugins['{PLUGIN_ID}'] = true",
    )
    p_apply.add_argument(
        "--dry-run",
        action="store_true",
        help="report intended changes without writing",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "detect":
        return cmd_detect(Path(args.repo_root).resolve())
    if args.command == "apply":
        return cmd_apply(args)
    return 2  # pragma: no cover


if __name__ == "__main__":
    raise SystemExit(main())
