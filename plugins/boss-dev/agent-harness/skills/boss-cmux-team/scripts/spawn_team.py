#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///
"""Scripted fast-path spawn of a config-driven multi-agent team in cmux.

Boots every role's pane at once from a generated cmux ``--layout`` (the first role
is the *lead* on the left half; the remaining roles fill a balanced grid on the
right), colors and labels the workspace, writes a ``.team/<feature>.spawn.json`` the
orchestrator can attach to, then execs the chosen orchestrator (Claude Code or pi)
in THIS terminal so it takes command already oriented via ``/cmux-did-spawn``.

Unlike the demo it was generalized from, nothing here is hardcoded: roles, models,
role-prompt files, the completion sentinel, the app path, and the stack description
all come from a **team-config JSON**, resolved in this order:

    --config <path>  ->  ./.cmux/team.json  ->  bundled assets/team-config.example.json

The layout is *generated* from that config, so any role set / model blend / app works.

Usage:
    spawn_team.py <cc|pi> <feature-slug> [--config PATH] [--cwd DIR]
                  [--orch-pi-model MODEL] [--dry-run]

``--dry-run`` prints the resolved config, the generated layout, and the cmux commands
it *would* run, then exits 0 without contacting cmux (CI-safe).

The scan/build/generate logic is pure and unit tested; the IO layer runs cmux and
reads/writes files.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# scripts/ lives inside the skill; assets/ is its sibling under the skill root.
SKILL_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = SKILL_ROOT / "assets" / "team-config.example.json"
DEFAULT_ORCH_PI_MODEL = "<your-orchestrator-model>"
UUID_RE = re.compile(r"[0-9a-fA-F-]{36}")

Config = dict[str, Any]


@dataclass(frozen=True)
class Ctx:
    """Substitution context threaded through layout/command generation."""

    feature: str
    sentinel: str
    app_path: str
    stack: str


# --------------------------------------------------------------------------- #
# Pure helpers (unit tested — no IO, no cmux)
# --------------------------------------------------------------------------- #
def die(msg: str) -> None:
    print(msg, file=sys.stderr)
    sys.exit(1)


def slugify(feature: str) -> str:
    """lowercase, spaces -> dashes, keep only [a-z0-9-]."""
    feature = feature.lower().replace(" ", "-")
    return re.sub(r"[^a-z0-9-]", "", feature)


def resolve_config_path(explicit: str | None) -> Path:
    """Resolve the team-config path: --config -> ./.cmux/team.json -> bundled default."""
    if explicit:
        return Path(explicit).expanduser()
    local = Path.cwd() / ".cmux" / "team.json"
    if local.is_file():
        return local
    return DEFAULT_CONFIG


def load_config(path: Path) -> Config:
    """Load + validate the team config. Raises ValueError on a malformed config."""
    try:
        raw: object = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"could not read team config {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ValueError(f"team config {path} must be a JSON object")
    config: Config = raw
    roles = config.get("roles")
    if not isinstance(roles, list) or not roles:
        raise ValueError(f"team config {path} must define a non-empty 'roles' array")
    for role in roles:
        if not isinstance(role, dict) or "name" not in role:
            raise ValueError(f"each role in {path} needs at least a 'name'")
    return config


def role_names(config: Config) -> list[str]:
    return [str(r["name"]) for r in config["roles"]]


def ctx_from(config: Config, feature: str) -> Ctx:
    return Ctx(
        feature=feature,
        sentinel=str(config.get("completion_sentinel", "TASK-DONE")),
        app_path=str(config.get("app_path", "")),
        stack=str(config.get("stack", "")),
    )


def _interpolate(text: str, ctx: Ctx) -> str:
    """Substitute the config placeholders into a kickoff line."""
    return (
        text
        .replace("__FEATURE__", ctx.feature)
        .replace("__SENTINEL__", ctx.sentinel)
        .replace("__APP_PATH__", ctx.app_path)
        .replace("__STACK__", ctx.stack)
    )


def _resolve_prompt(prompt: str) -> str:
    """Resolve a role-prompt path (relative -> the skill's assets/) to an absolute str."""
    p = Path(prompt).expanduser()
    if not p.is_absolute():
        p = (SKILL_ROOT / "assets" / p).resolve()
    return str(p)


def build_command(role: dict[str, Any], ctx: Ctx) -> str:
    """Build the pane launch command for a role from the config (no shell execution)."""
    launcher = str(role.get("launcher", "pi"))
    model = str(role["model"])
    name = f"{role['name']}-{ctx.feature}"
    prompt = _resolve_prompt(str(role["prompt"]))
    kickoff = _interpolate(str(role.get("kickoff", "")), ctx)
    return f'{launcher} --append-system-prompt {prompt} --model {model} --name {name} "{kickoff}"'


def _pane_node(role: dict[str, Any], ctx: Ctx) -> dict[str, Any]:
    surface = {"type": "terminal", "name": str(role["name"]), "command": build_command(role, ctx)}
    return {"pane": {"surfaces": [surface]}}


def _toggle(direction: str) -> str:
    return "horizontal" if direction == "vertical" else "vertical"


def _worker_tree(workers: list[dict[str, Any]], direction: str, ctx: Ctx) -> dict[str, Any]:
    """Arrange N workers into a balanced binary split tree (any N)."""
    if len(workers) == 1:
        return _pane_node(workers[0], ctx)
    mid = len(workers) // 2
    left = _worker_tree(workers[:mid], _toggle(direction), ctx)
    right = _worker_tree(workers[mid:], _toggle(direction), ctx)
    return {"direction": direction, "split": 0.5, "children": [left, right]}


def build_layout(config: Config, feature: str) -> dict[str, Any]:
    """Generate a cmux ``--layout`` tree from the config: lead left-half, workers in a grid."""
    ctx = ctx_from(config, feature)
    roles: list[dict[str, Any]] = list(config["roles"])
    lead, workers = roles[0], roles[1:]
    lead_node = _pane_node(lead, ctx)
    if not workers:
        return lead_node
    # Right side splits vertically first (top/bottom), mirroring a lead + 2x2 grid.
    return {"direction": "horizontal", "split": 0.5, "children": [lead_node, _worker_tree(workers, "vertical", ctx)]}


def compact_layout(layout: dict[str, Any]) -> str:
    return json.dumps(layout, separators=(",", ":"))


# --------------------------------------------------------------------------- #
# IO layer (cmux + filesystem)
# --------------------------------------------------------------------------- #
def sh(*args: str) -> subprocess.CompletedProcess[str]:
    """Run a command, capturing stdout/stderr as text. Never raises."""
    return subprocess.run(list(args), capture_output=True, text=True, check=False)


def cmux(*args: str) -> subprocess.CompletedProcess[str]:
    return sh("cmux", *args)


def cmux_json(*args: str) -> Any:
    out = cmux(*args).stdout.strip()
    if not out:
        return None
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return None


def ensure_cmux_running() -> None:
    """Preflight: if the socket is down, launch cmux and wait (don't stop)."""
    if cmux("identify", "--json").returncode == 0:
        return
    sh("open", "-a", "cmux")  # cmux owns the socket
    for _ in range(30):  # poll ~15s
        if cmux("identify", "--json").returncode == 0:
            return
        time.sleep(0.5)
    if cmux("identify", "--json").returncode != 0:
        die("cmux failed to start; aborting.")


def find_or_create_window() -> tuple[str, bool, str | None]:
    """Reuse the open window (UUID is the only stable handle); create one only if none."""
    windows = cmux_json("list-windows", "--json") or []
    win = next((w["id"] for w in windows if w.get("key")), None)
    if not win and windows:
        win = windows[0].get("id")
    if win:
        return str(win), False, None

    created = cmux("new-window").stdout
    match = UUID_RE.search(created or "")
    if not match:
        die("failed to create a window")
        raise SystemExit(1)  # unreachable; die() exits, but keeps type checkers happy
    win = match.group(0)
    wslist = cmux_json("workspace", "list", "--window", win, "--json") or {}
    workspaces = wslist.get("workspaces") or []
    default_ws = workspaces[0].get("ref") if workspaces else None
    return str(win), True, (str(default_ws) if default_ws else None)


def write_spawn_file(config: Config, feature: str, win: str, agent: str, cwd: Path) -> Path:
    spawn = cwd / ".team" / f"{feature}.spawn.json"
    spawn.parent.mkdir(parents=True, exist_ok=True)
    models = {str(r["name"]): str(r["model"]) for r in config["roles"]}
    payload = {
        "feature": feature,
        "window": win,
        "workspace_name": feature,
        "orchestrator": agent,
        "roles": role_names(config),
        "models": models,
        "completion_sentinel": str(config.get("completion_sentinel", "TASK-DONE")),
    }
    spawn.write_text(json.dumps(payload, indent=2) + "\n")
    return spawn


def exec_orchestrator(config: Config, agent: str, feature: str, orch_pi_model: str, cwd: Path) -> None:
    """Replace this process with the orchestrator, oriented to the spawned team."""
    os.chdir(cwd)  # so the relative spawn-file arg resolves for /cmux-did-spawn
    sys.stdout.flush()
    attach = f"/cmux-did-spawn .team/{feature}.spawn.json"
    orch: dict[str, Any] = dict(config.get("orchestrator", {}))
    if agent == "cc":
        cc_model = str(dict(orch.get("cc", {})).get("model", "opus[1m]"))
        os.execvp("claude", ["claude", "--dangerously-skip-permissions", "--model", cc_model, attach])
    else:  # pi
        os.execvp("pi", ["pi", "--name", f"orchestrator-{feature}", "--model", orch_pi_model, attach])


def _print_dry_run(
    config: Config, config_path: Path, cwd: Path, feature: str, env_file: str, layout: dict[str, Any]
) -> None:
    print(f"# config:  {config_path}")
    print(f"# cwd:     {cwd}")
    print(f"# feature: {feature}")
    print(f"# roles:   {', '.join(role_names(config))}")
    print(f"# sentinel: {config.get('completion_sentinel', 'TASK-DONE')}")
    print("# layout:")
    print(json.dumps(layout, indent=2))
    print("# would run:")
    print(
        f"cmux workspace create --window <WIN> --name {feature} --cwd {cwd} --env-file {env_file} --layout <layout> --focus true --json"
    )


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Config-driven fast-path spawn of a multi-agent team in cmux.")
    parser.add_argument("agent", choices=["cc", "pi"], help="orchestrator: cc (Claude Code) or pi")
    parser.add_argument("feature", help="feature slug (dash-case); names the team's workspace")
    parser.add_argument(
        "--config", default=None, help="team-config JSON (default: ./.cmux/team.json or bundled example)"
    )
    parser.add_argument("--cwd", default=None, help="repo/working dir for the team (default: current dir)")
    parser.add_argument("--orch-pi-model", default=None, help="model for the pi orchestrator")
    parser.add_argument("--dry-run", action="store_true", help="print the plan and exit without contacting cmux")
    args = parser.parse_args(argv)

    feature = slugify(args.feature)
    if not feature:
        die(f"usage: spawn_team.py {args.agent} <feature-slug>")

    try:
        config_path = resolve_config_path(args.config)
        config = load_config(config_path)
    except ValueError as exc:
        die(str(exc))
        return 1  # unreachable; die() exits

    orch: dict[str, Any] = dict(config.get("orchestrator", {}))
    cwd = Path(args.cwd).expanduser().resolve() if args.cwd else Path(str(config.get("cwd") or Path.cwd())).resolve()
    orch_pi_model = args.orch_pi_model or str(dict(orch.get("pi", {})).get("model", DEFAULT_ORCH_PI_MODEL))
    env_file = str(config.get("env_file", ".env"))
    layout = build_layout(config, feature)

    if args.dry_run:
        _print_dry_run(config, config_path, cwd, feature, env_file, layout)
        return 0

    os.environ["CMUX_QUIET"] = "1"
    ensure_cmux_running()
    win, created_win, default_ws = find_or_create_window()

    created = cmux_json(
        "workspace",
        "create",
        "--window",
        win,
        "--name",
        feature,
        "--cwd",
        str(cwd),
        "--env-file",
        str(cwd / env_file),
        "--layout",
        compact_layout(layout),
        "--focus",
        "true",
        "--json",
    )
    created = created if isinstance(created, dict) else {}
    ws = created.get("workspace_ref")
    lead = created.get("surface_ref")
    if not ws or not lead:
        die("failed to create the team workspace from the layout")

    ws_ref = str(ws)
    cmux("focus-window", "--window", win)
    if created_win and default_ws and default_ws != ws_ref:
        cmux("close-workspace", "--workspace", default_ws)

    color = str(config.get("workspace_color", "Purple"))
    cmux("workspace-action", "--action", "set-color", "--workspace", ws_ref, "--color", color)
    status: dict[str, Any] = dict(config.get("status", {}))
    cmux(
        "set-status",
        "team",
        feature,
        "--workspace",
        ws_ref,
        "--color",
        str(status.get("color", "#8E44AD")),
        "--icon",
        str(status.get("icon", "person.3.fill")),
    )

    spawn = write_spawn_file(config, feature, win, args.agent, cwd)
    print(f"team window={win} workspace={ws_ref} lead={lead}  spawn={spawn}", flush=True)
    print(f"launching {args.agent} orchestrator, already aware via /cmux-did-spawn ...", flush=True)

    exec_orchestrator(config, args.agent, feature, orch_pi_model, cwd)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
