"""Tests for the boss-cmux-team spawn_team.py generalized spawner.

Pure helpers are imported directly (see conftest.py sys.path shim); the CLI --dry-run
path is exercised via subprocess since importlib loading cannot assert CLI semantics.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import spawn_team

SCRIPT = Path(__file__).parent.parent / "spawn_team.py"


# --------------------------------------------------------------------------- #
# slugify
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Add Health Endpoint", "add-health-endpoint"),
        ("word-count!!", "word-count"),
        ("  Mixed CASE 123  ", "--mixed-case-123--"),
        ("émoji✨safe", "mojisafe"),
    ],
)
def test_slugify(raw: str, expected: str) -> None:
    assert spawn_team.slugify(raw) == expected


# --------------------------------------------------------------------------- #
# config loading + validation
# --------------------------------------------------------------------------- #
def test_default_config_loads_and_is_valid() -> None:
    config = spawn_team.load_config(spawn_team.DEFAULT_CONFIG)
    assert spawn_team.role_names(config) == ["lead", "plan", "build-be", "build-fe", "test"]
    assert config["completion_sentinel"] == "TASK-DONE"


def test_resolve_config_path_falls_back_to_bundled(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)  # no ./.cmux/team.json here
    assert spawn_team.resolve_config_path(None) == spawn_team.DEFAULT_CONFIG


def test_resolve_config_path_prefers_local(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    local = tmp_path / ".cmux" / "team.json"
    local.parent.mkdir()
    local.write_text("{}")
    monkeypatch.chdir(tmp_path)
    assert spawn_team.resolve_config_path(None) == local


def test_load_config_rejects_missing_roles(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"roles": []}))
    with pytest.raises(ValueError, match="non-empty 'roles'"):
        spawn_team.load_config(bad)


def test_load_config_rejects_non_object(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("[1, 2, 3]")
    with pytest.raises(ValueError, match="must be a JSON object"):
        spawn_team.load_config(bad)


# --------------------------------------------------------------------------- #
# layout generation
# --------------------------------------------------------------------------- #
def test_build_layout_lead_left_half_and_worker_grid() -> None:
    config = spawn_team.load_config(spawn_team.DEFAULT_CONFIG)
    layout = spawn_team.build_layout(config, "demo")
    # top-level: lead pane on the left, worker subtree on the right
    assert layout["direction"] == "horizontal"
    assert layout["split"] == 0.5
    lead_node, worker_tree = layout["children"]
    assert lead_node["pane"]["surfaces"][0]["name"] == "lead"
    # 4 workers => 2x2 grid: a vertical split of two horizontal rows
    assert worker_tree["direction"] == "vertical"
    top_row, bottom_row = worker_tree["children"]
    assert top_row["direction"] == "horizontal"
    names = [pane["pane"]["surfaces"][0]["name"] for row in (top_row, bottom_row) for pane in row["children"]]
    assert names == ["plan", "build-be", "build-fe", "test"]


def test_build_layout_single_lead_returns_bare_pane() -> None:
    config = {"roles": [{"name": "solo", "model": "m", "prompt": "roles/lead.md"}]}
    layout = spawn_team.build_layout(config, "demo")
    assert layout["pane"]["surfaces"][0]["name"] == "solo"


def test_build_command_threads_model_feature_and_sentinel() -> None:
    config = spawn_team.load_config(spawn_team.DEFAULT_CONFIG)
    ctx = spawn_team.ctx_from(config, "myfeat")
    cmd = spawn_team.build_command(config["roles"][0], ctx)
    assert "--name lead-myfeat" in cmd
    assert "--model <your-lead-model>" in cmd
    assert "TASK-DONE: " in cmd
    assert cmd.strip().startswith("pi --append-system-prompt ")


def test_layout_has_no_flotion_or_hardcoded_models() -> None:
    config = spawn_team.load_config(spawn_team.DEFAULT_CONFIG)
    blob = spawn_team.compact_layout(spawn_team.build_layout(config, "demo")).lower()
    for banned in ("flotion", "glm-5.2", "minimax"):
        assert banned not in blob


# --------------------------------------------------------------------------- #
# CLI --dry-run (subprocess: importlib can't assert CLI exit codes)
# --------------------------------------------------------------------------- #
def test_dry_run_exits_zero_and_prints_layout() -> None:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "cc", "Add Health Endpoint", "--dry-run"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert "# feature: add-health-endpoint" in proc.stdout
    assert '"name": "lead"' in proc.stdout
    assert "flotion" not in proc.stdout.lower()
