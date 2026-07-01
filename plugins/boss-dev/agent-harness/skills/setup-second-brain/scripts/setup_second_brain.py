#!/usr/bin/env -S uv run --script --quiet
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Set up the "second brain" (obsidian-wiki + optional QMD semantic search).

Standalone PEP 723 script — stdlib only, run it with::

    uv run setup_second_brain.py detect
    uv run setup_second_brain.py apply [flags...]

The script does the deterministic, idempotent file work: it detects the local
environment (uv / node / npm / obsidian-wiki / qmd + config state) and, on
``apply``, writes QMD variables into ``~/.obsidian-wiki/config`` and — only when
QMD transport is ``mcp`` — merges a ``qmd`` MCP server into
``~/.claude/settings.json``. Every modified file is copied to
``<file>.backup.<timestamp>`` before being written.

The network / global installs themselves (``uv tool install``,
``npm install -g``, ``obsidian-wiki setup``, ``qmd`` indexing) are run by the
calling skill via Bash after the user confirms — this script never installs
anything or reaches the network, so it stays fast, offline, and testable.

Two modes:

- ``detect`` — prints a JSON report of current state to stdout. Read-only.
- ``apply`` — backup -> edit -> validate, driven by explicit flags.
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# --- Config shape -------------------------------------------------------------

# QMD variables the obsidian-wiki skills read from the resolved config
# (see ~/.claude/skills/wiki-query/SKILL.md and wiki-ingest/SKILL.md). They are
# stored in ~/.obsidian-wiki/config alongside OBSIDIAN_VAULT_PATH, one
# KEY="value" per line, which the skills source during config resolution.
QMD_KEYS = (
    "QMD_WIKI_COLLECTION",
    "QMD_PAPERS_COLLECTION",
    "QMD_TRANSPORT",
    "QMD_CLI_SEARCH_MODE",
)

TRANSPORTS = ("cli", "mcp")
SEARCH_MODES = ("quality", "balanced", "fast")

DEFAULT_CONFIG_PATH = Path.home() / ".obsidian-wiki" / "config"
DEFAULT_SETTINGS_PATH = Path.home() / ".claude" / "settings.json"

# The qmd MCP server entry merged into settings.json when transport == "mcp".
QMD_MCP_NAME = "qmd"
QMD_MCP_SERVER = {"command": "qmd", "args": ["mcp"]}

MIN_NODE_MAJOR = 22


# --- Helpers ------------------------------------------------------------------


def timestamp() -> str:
    """Return a filesystem-safe timestamp like ``20260701-153012``."""
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


def _which(name: str) -> bool:
    return shutil.which(name) is not None


# --- obsidian-wiki config (KEY="value" lines) ---------------------------------


class ConfigError(RuntimeError):
    """Raised when the obsidian-wiki config cannot be safely handled."""


_CONFIG_LINE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$")


def parse_config(text: str) -> dict[str, str]:
    """Parse ``KEY=value`` / ``KEY="value"`` lines into a dict.

    Comments and blank lines are ignored. Surrounding single or double quotes
    are stripped from values. Later lines win over earlier ones.
    """
    out: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = _CONFIG_LINE.match(line)
        if not match:
            continue
        key, value = match.group(1), match.group(2).strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        out[key] = value
    return out


def _render_config_line(key: str, value: str) -> str:
    return f'{key}="{value}"'


def set_config_keys(text: str, updates: dict[str, str]) -> str:
    """Return ``text`` with ``updates`` applied idempotently.

    Existing keys are rewritten in place (preserving surrounding lines/order);
    missing keys are appended. Re-running with the same values is a no-op.
    """
    lines = text.splitlines()
    remaining = dict(updates)
    result: list[str] = []

    for raw in lines:
        match = _CONFIG_LINE.match(raw.strip())
        if match and match.group(1) in remaining:
            key = match.group(1)
            result.append(_render_config_line(key, remaining.pop(key)))
        else:
            result.append(raw)

    for key, value in remaining.items():
        result.append(_render_config_line(key, value))

    rendered = "\n".join(result)
    if rendered and not rendered.endswith("\n"):
        rendered += "\n"
    return rendered


def plan_qmd_config(
    current_text: str,
    transport: str,
    wiki_collection: str,
    papers_collection: str,
    search_mode: str,
) -> dict[str, str]:
    """Return the desired QMD key/value map to merge into the config."""
    return {
        "QMD_TRANSPORT": transport,
        "QMD_WIKI_COLLECTION": wiki_collection,
        "QMD_PAPERS_COLLECTION": papers_collection,
        "QMD_CLI_SEARCH_MODE": search_mode,
    }


def apply_qmd_config(
    config_path: Path,
    transport: str,
    wiki_collection: str,
    papers_collection: str,
    search_mode: str,
    dry_run: bool,
) -> dict[str, object]:
    """Idempotently write the QMD variables into the obsidian-wiki config."""
    old_text = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
    updates = plan_qmd_config(old_text, transport, wiki_collection, papers_collection, search_mode)
    new_text = set_config_keys(old_text, updates)

    if new_text == old_text:
        return {"changed": False, "keys": sorted(updates), "backup": None}

    if dry_run:
        return {
            "changed": True,
            "keys": sorted(updates),
            "backup": None,
            "dry_run": True,
            "diff": _unified_diff(old_text, new_text, "~/.obsidian-wiki/config"),
        }

    config_path.parent.mkdir(parents=True, exist_ok=True)
    backup_path: Path | None = backup(config_path) if config_path.exists() else None
    config_path.write_text(new_text, encoding="utf-8")
    return {
        "changed": True,
        "keys": sorted(updates),
        "backup": str(backup_path) if backup_path else None,
    }


# --- settings.json QMD MCP merge ----------------------------------------------


class SettingsError(RuntimeError):
    """Raised when settings.json cannot be safely loaded or written."""


def load_settings(path: Path) -> dict[str, object]:
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


def plan_mcp(current: dict[str, object]) -> tuple[dict[str, object], list[str]]:
    """Return ``(merged, changes)`` — add the qmd MCP server, keeping others."""
    merged = json.loads(json.dumps(current))  # deep copy
    changes: list[str] = []

    servers = merged.get("mcpServers")
    if not isinstance(servers, dict):
        servers = {}
        merged["mcpServers"] = servers

    desired = json.loads(json.dumps(QMD_MCP_SERVER))
    if servers.get(QMD_MCP_NAME) != desired:
        servers[QMD_MCP_NAME] = desired
        changes.append(f"set mcpServers['{QMD_MCP_NAME}'] -> qmd mcp")

    return merged, changes


def apply_mcp(settings_path: Path, dry_run: bool) -> dict[str, object]:
    """Merge the qmd MCP server into settings.json safely (additive)."""
    current = load_settings(settings_path)
    merged, changes = plan_mcp(current)

    if merged == current:
        return {"changed": False, "changes": changes, "backup": None}

    payload = json.dumps(merged, indent=2) + "\n"

    if dry_run:
        old_text = settings_path.read_text(encoding="utf-8") if settings_path.exists() else ""
        return {
            "changed": True,
            "changes": changes,
            "backup": None,
            "dry_run": True,
            "diff": _unified_diff(old_text, payload, str(settings_path)),
        }

    settings_path.parent.mkdir(parents=True, exist_ok=True)
    backup_path: Path | None = backup(settings_path) if settings_path.exists() else None
    settings_path.write_text(payload, encoding="utf-8")

    # Re-read and validate; restore from backup on failure.
    try:
        json.loads(settings_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        if backup_path is not None:
            shutil.copy2(backup_path, settings_path)
        raise SettingsError(f"wrote {settings_path} but it failed to parse ({exc}); restored from backup.") from exc

    return {
        "changed": True,
        "changes": changes,
        "backup": str(backup_path) if backup_path else None,
    }


# --- environment detection ----------------------------------------------------


def _tool_version(cmd: list[str]) -> str | None:
    """Return the trimmed first line of ``cmd`` output, or ``None`` on failure."""
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=20, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    out = (proc.stdout or proc.stderr).strip()
    return out.splitlines()[0] if out else None


def _node_major(version: str | None) -> int | None:
    """Parse the major version from a ``node --version`` string (``v22.15.1``)."""
    if not version:
        return None
    match = re.search(r"(\d+)", version)
    return int(match.group(1)) if match else None


def check_env() -> dict[str, object]:
    """Report (never block) on the tools the second brain expects."""
    results: dict[str, object] = {}

    results["uv"] = {
        "ok": _which("uv"),
        "hint": None if _which("uv") else "install uv: https://docs.astral.sh/uv/",
    }

    node_version = _tool_version(["node", "--version"]) if _which("node") else None
    node_major = _node_major(node_version)
    node_ok = node_major is not None and node_major >= MIN_NODE_MAJOR
    if not _which("node"):
        node_hint: str | None = "install Node.js >= 22 (required for QMD)"
    elif not node_ok:
        node_hint = f"Node {node_version} is < {MIN_NODE_MAJOR}; QMD needs Node >= {MIN_NODE_MAJOR}"
    else:
        node_hint = None
    results["node"] = {
        "installed": _which("node"),
        "version": node_version,
        "meets_min": node_ok,
        "hint": node_hint,
    }

    results["npm"] = {
        "ok": _which("npm"),
        "hint": None if _which("npm") else "install npm (bundled with Node.js)",
    }

    wiki_installed = _which("obsidian-wiki")
    results["obsidian_wiki"] = {
        "installed": wiki_installed,
        "version": _tool_version(["obsidian-wiki", "--version"]) if wiki_installed else None,
        "hint": None if wiki_installed else 'install: uv tool install "obsidian-wiki[graph,ast]"',
    }

    qmd_installed = _which("qmd")
    results["qmd"] = {
        "installed": qmd_installed,
        "hint": None if qmd_installed else "optional: npm install -g @tobilu/qmd (needs Node >= 22)",
    }

    return results


# --- detect / apply commands --------------------------------------------------


def cmd_detect(config_path: Path, settings_path: Path) -> int:
    config_exists = config_path.exists()
    config = parse_config(config_path.read_text(encoding="utf-8")) if config_exists else {}
    vault_path = config.get("OBSIDIAN_VAULT_PATH")
    vault_expanded = Path(vault_path).expanduser() if vault_path else None

    try:
        settings = load_settings(settings_path)
        settings_error = None
    except SettingsError as exc:
        settings = {}
        settings_error = str(exc)

    servers = settings.get("mcpServers")
    mcp_qmd = isinstance(servers, dict) and QMD_MCP_NAME in servers

    report = {
        "config_path": str(config_path),
        "config_exists": config_exists,
        "vault_path": vault_path,
        "vault_exists": bool(vault_expanded and vault_expanded.is_dir()),
        "qmd_keys_set": {key: (key in config and bool(config[key])) for key in QMD_KEYS},
        "settings_path": str(settings_path),
        "settings_error": settings_error,
        "mcp_qmd_configured": None if settings_error else mcp_qmd,
        "transports": list(TRANSPORTS),
        "search_modes": list(SEARCH_MODES),
        "env": check_env(),
    }
    json.dump(report, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


def cmd_apply(args: argparse.Namespace) -> int:
    if args.transport not in TRANSPORTS:
        print(f"error: --transport must be one of: {', '.join(TRANSPORTS)}", file=sys.stderr)
        return 2
    if args.search_mode not in SEARCH_MODES:
        print(f"error: --search-mode must be one of: {', '.join(SEARCH_MODES)}", file=sys.stderr)
        return 2

    config_path = Path(args.config_path).expanduser()
    settings_path = Path(args.settings_path).expanduser()

    summary: dict[str, object] = {"dry_run": args.dry_run}
    backups: list[str] = []

    try:
        # Fail fast: validate settings JSON before touching the config, so an
        # invalid settings.json can't leave a half-applied config behind.
        if args.transport == "mcp":
            load_settings(settings_path)

        if args.qmd_config:
            qmd = apply_qmd_config(
                config_path,
                transport=args.transport,
                wiki_collection=args.wiki_collection,
                papers_collection=args.papers_collection,
                search_mode=args.search_mode,
                dry_run=args.dry_run,
            )
            summary["qmd_config"] = qmd
            if qmd.get("backup"):
                backups.append(str(qmd["backup"]))
        else:
            summary["qmd_config"] = {"changed": False, "skipped": True}

        if args.transport == "mcp":
            mcp = apply_mcp(settings_path, args.dry_run)
            summary["mcp"] = mcp
            if mcp.get("backup"):
                backups.append(str(mcp["backup"]))
        else:
            summary["mcp"] = {"changed": False, "skipped": True}
    except (SettingsError, ConfigError) as exc:
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
    p_detect.add_argument("--config-path", default=str(DEFAULT_CONFIG_PATH))
    p_detect.add_argument("--settings-path", default=str(DEFAULT_SETTINGS_PATH))

    p_apply = sub.add_parser("apply", help="apply backup -> edit -> validate")
    p_apply.add_argument("--config-path", default=str(DEFAULT_CONFIG_PATH))
    p_apply.add_argument("--settings-path", default=str(DEFAULT_SETTINGS_PATH))
    p_apply.add_argument(
        "--qmd-config",
        action="store_true",
        help="write the QMD_* variables into ~/.obsidian-wiki/config",
    )
    p_apply.add_argument(
        "--transport",
        choices=list(TRANSPORTS),
        default="cli",
        help="QMD transport; 'mcp' also merges the qmd MCP server into settings.json",
    )
    p_apply.add_argument("--wiki-collection", default="wiki", help="QMD_WIKI_COLLECTION value")
    p_apply.add_argument("--papers-collection", default="papers", help="QMD_PAPERS_COLLECTION value")
    p_apply.add_argument(
        "--search-mode",
        choices=list(SEARCH_MODES),
        default="quality",
        help="QMD_CLI_SEARCH_MODE value (cli transport only)",
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
        return cmd_detect(
            Path(args.config_path).expanduser(),
            Path(args.settings_path).expanduser(),
        )
    if args.command == "apply":
        return cmd_apply(args)
    return 2  # pragma: no cover


if __name__ == "__main__":
    raise SystemExit(main())
