"""Tests for setup_harness.py — gitignore reconcile, settings merge, env, CLI."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import setup_harness as sh

# --- .gitignore ---------------------------------------------------------------


def _patterns(repo: Path) -> list[str]:
    return sh.gitignore_patterns(repo)


def test_missing_patterns_empty_file(tmp_path: Path) -> None:
    assert sh.missing_patterns("", _patterns(tmp_path)) == _patterns(tmp_path)


def test_missing_patterns_skips_existing(tmp_path: Path) -> None:
    root_pattern = _patterns(tmp_path)[0]
    text = f"{root_pattern}\n*.log\n"
    missing = sh.missing_patterns(text, _patterns(tmp_path))
    assert root_pattern not in missing
    assert "*.log" not in missing
    assert ".claude/*.backup.*" in missing


def test_gitignore_patterns_ignore_derived_harness_root_and_backups(tmp_path: Path) -> None:
    # backup() writes `.gitignore.backup.<ts>` at the repo root, so the managed
    # block must ignore those root backups, not just `.claude/` ones.
    patterns = _patterns(tmp_path)
    assert patterns[0] == f".{sh.harness_slug(tmp_path.name)}/"
    assert ".gitignore.backup.*" in patterns
    assert ".gitignore.backup.*" in sh.missing_patterns("", patterns)


def test_missing_patterns_ignores_commented_lines(tmp_path: Path) -> None:
    # A commented-out pattern does not count as "present".
    root_pattern = _patterns(tmp_path)[0]
    text = f"# {root_pattern}\n"
    assert root_pattern in sh.missing_patterns(text, _patterns(tmp_path))


def test_apply_gitignore_creates_block(tmp_path: Path) -> None:
    result = sh.apply_gitignore(tmp_path, dry_run=False)
    assert result["changed"] is True
    content = (tmp_path / ".gitignore").read_text()
    assert sh.MANAGED_BLOCK_START in content
    assert sh.MANAGED_BLOCK_END in content
    for pat in _patterns(tmp_path):
        assert pat in content
    assert "logs/" not in content
    assert ".claude/data/" not in content


def test_apply_gitignore_no_dup_existing(tmp_path: Path) -> None:
    gi = tmp_path / ".gitignore"
    root_pattern = _patterns(tmp_path)[0]
    gi.write_text(f"{root_pattern}\n*.log\n")
    sh.apply_gitignore(tmp_path, dry_run=False)
    content = gi.read_text()
    # The pre-existing root pattern is not duplicated.
    assert content.count(root_pattern) == 1


def test_apply_gitignore_backs_up_existing(tmp_path: Path) -> None:
    gi = tmp_path / ".gitignore"
    gi.write_text("logs/\n")
    result = sh.apply_gitignore(tmp_path, dry_run=False)
    assert result["backup"] is not None
    assert Path(str(result["backup"])).exists()


def test_apply_gitignore_idempotent(tmp_path: Path) -> None:
    sh.apply_gitignore(tmp_path, dry_run=False)
    first = (tmp_path / ".gitignore").read_text()
    backups_before = list(tmp_path.glob(".gitignore.backup.*"))

    second_result = sh.apply_gitignore(tmp_path, dry_run=False)
    second = (tmp_path / ".gitignore").read_text()
    backups_after = list(tmp_path.glob(".gitignore.backup.*"))

    assert second_result["changed"] is False
    assert first == second
    assert backups_before == backups_after  # no new backup


def test_apply_gitignore_repairs_block_missing_end_marker(tmp_path: Path) -> None:
    # A start marker with no matching end marker must be rebuilt into a single
    # well-formed block, not left orphaned beside a freshly appended second block.
    gi = tmp_path / ".gitignore"
    gi.write_text(f"{sh.MANAGED_BLOCK_START}\nlogs/\n")

    sh.apply_gitignore(tmp_path, dry_run=False)
    content = gi.read_text()

    assert content.count(sh.MANAGED_BLOCK_START) == 1
    assert content.count(sh.MANAGED_BLOCK_END) == 1
    assert "logs/" not in content
    for pat in _patterns(tmp_path):
        assert pat in content


def test_apply_gitignore_dry_run_writes_nothing(tmp_path: Path) -> None:
    result = sh.apply_gitignore(tmp_path, dry_run=True)
    assert result["changed"] is True
    assert not (tmp_path / ".gitignore").exists()


def test_apply_gitignore_dry_run_shows_diff(tmp_path: Path) -> None:
    gi = tmp_path / ".gitignore"
    gi.write_text("existing-ignore/\n")
    result = sh.apply_gitignore(tmp_path, dry_run=True)
    diff = str(result["diff"])
    # Unified-diff header plus the added managed block, nothing written.
    assert "--- a/.gitignore" in diff
    assert "+++ b/.gitignore" in diff
    assert "+" + sh.MANAGED_BLOCK_START in diff
    assert "+" + _patterns(tmp_path)[0] in diff
    assert gi.read_text() == "existing-ignore/\n"


def test_apply_gitignore_all_present_is_full_noop(tmp_path: Path) -> None:
    gi = tmp_path / ".gitignore"
    original = "\n".join(_patterns(tmp_path)) + "\n"
    gi.write_text(original)

    result = sh.apply_gitignore(tmp_path, dry_run=False)

    assert result["changed"] is False
    assert result["added"] == []
    assert gi.read_text() == original  # untouched
    assert sh.MANAGED_BLOCK_START not in gi.read_text()  # no block added
    assert list(tmp_path.glob(".gitignore.backup.*")) == []  # no backup


def test_apply_gitignore_existing_block_subset_no_dup(tmp_path: Path) -> None:
    gi = tmp_path / ".gitignore"
    # A managed block that already holds two of the managed patterns.
    root_pattern = _patterns(tmp_path)[0]
    seeded = f"{sh.MANAGED_BLOCK_START}\n{root_pattern}\n*.log\n{sh.MANAGED_BLOCK_END}\n"
    gi.write_text(seeded)

    result = sh.apply_gitignore(tmp_path, dry_run=False)
    content = gi.read_text()

    assert result["changed"] is True
    # Only the genuinely missing patterns were added.
    assert set(result["added"]) == set(_patterns(tmp_path)) - {root_pattern, "*.log"}
    # Existing patterns are not duplicated.
    assert content.count(root_pattern) == 1
    assert content.count("*.log") == 1
    # Block markers appear exactly once each.
    assert content.count(sh.MANAGED_BLOCK_START) == 1
    assert content.count(sh.MANAGED_BLOCK_END) == 1
    # All managed patterns are present inside the single block.
    for pat in _patterns(tmp_path):
        assert pat in content


def test_apply_gitignore_rewrites_legacy_managed_block(tmp_path: Path) -> None:
    gi = tmp_path / ".gitignore"
    gi.write_text(f"{sh.MANAGED_BLOCK_START}\nlogs/\n.claude/data/\n*.log\n{sh.MANAGED_BLOCK_END}\n")

    result = sh.apply_gitignore(tmp_path, dry_run=False)
    content = gi.read_text()

    assert result["changed"] is True
    assert "logs/" not in content
    assert ".claude/data/" not in content
    for pattern in _patterns(tmp_path):
        assert pattern in content


def test_plugin_id_falls_back_to_boss_skills_marketplace(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLAUDE_PLUGIN_ROOT", raising=False)
    monkeypatch.delenv("CLAUDE_PLUGIN_MARKETPLACE", raising=False)
    assert sh._plugin_id() == "agent-harness@boss-skills"


def test_plugin_id_prefers_marketplaces_path_segment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", "/home/user/.claude/marketplaces/some-fork/plugins/agent-harness")
    monkeypatch.delenv("CLAUDE_PLUGIN_MARKETPLACE", raising=False)
    assert sh._plugin_id() == "agent-harness@some-fork"


def test_plugin_id_falls_back_to_env_marketplace(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLAUDE_PLUGIN_ROOT", raising=False)
    monkeypatch.setenv("CLAUDE_PLUGIN_MARKETPLACE", "another-fork")
    assert sh._plugin_id() == "agent-harness@another-fork"


# --- settings.local.json ------------------------------------------------------


def _settings_path(repo: Path) -> Path:
    return repo / sh.SETTINGS_REL_PATH


def test_load_settings_missing_returns_empty(tmp_path: Path) -> None:
    assert sh.load_settings(_settings_path(tmp_path)) == {}


def test_load_settings_invalid_json_aborts(tmp_path: Path) -> None:
    path = _settings_path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text("{ not valid json ")
    with pytest.raises(sh.SettingsError):
        sh.load_settings(path)


def test_apply_settings_creates_with_schema(tmp_path: Path) -> None:
    result = sh.apply_settings(
        tmp_path,
        status_line_action="skip",
        output_style_action="skip",
        enable_plugin=False,
        dry_run=False,
    )
    assert result["changed"] is True
    data = json.loads(_settings_path(tmp_path).read_text())
    assert data["$schema"] == sh.SCHEMA_URL


def test_apply_settings_merge_adds_style_and_plugin(tmp_path: Path) -> None:
    sh.apply_settings(
        tmp_path,
        status_line_action="set",
        output_style_action="yaml-structured",
        enable_plugin=True,
        dry_run=False,
    )
    data = json.loads(_settings_path(tmp_path).read_text())
    assert data["outputStyle"] == "yaml-structured"
    assert data["enabledPlugins"][sh.PLUGIN_ID] is True
    assert data["statusLine"]["command"] == sh.STATUS_LINE["command"]


def test_apply_settings_skip_preserves_existing_status_line(tmp_path: Path) -> None:
    path = _settings_path(tmp_path)
    path.parent.mkdir(parents=True)
    existing = {"$schema": sh.SCHEMA_URL, "statusLine": {"type": "command", "command": "mine"}}
    path.write_text(json.dumps(existing))

    sh.apply_settings(
        tmp_path,
        status_line_action="skip",
        output_style_action="ultra-concise",
        enable_plugin=False,
        dry_run=False,
    )
    data = json.loads(path.read_text())
    assert data["statusLine"]["command"] == "mine"  # untouched
    assert data["outputStyle"] == "ultra-concise"


def test_apply_settings_does_not_clobber_unrelated_keys(tmp_path: Path) -> None:
    path = _settings_path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"$schema": sh.SCHEMA_URL, "permissions": {"allow": ["X"]}}))

    sh.apply_settings(
        tmp_path,
        status_line_action="set",
        output_style_action="skip",
        enable_plugin=False,
        dry_run=False,
    )
    data = json.loads(path.read_text())
    assert data["permissions"] == {"allow": ["X"]}


def test_apply_settings_invalid_json_aborts_no_write(tmp_path: Path) -> None:
    path = _settings_path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text("{ broken ")
    with pytest.raises(sh.SettingsError):
        sh.apply_settings(
            tmp_path,
            status_line_action="set",
            output_style_action="skip",
            enable_plugin=False,
            dry_run=False,
        )
    assert path.read_text() == "{ broken "  # untouched


def test_apply_settings_keeps_foreign_schema(tmp_path: Path) -> None:
    path = _settings_path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"$schema": "https://example.com/other.json"}))

    _, changes = sh.plan_settings(
        json.loads(path.read_text()),
        status_line_action="skip",
        output_style_action="skip",
        enable_plugin=False,
    )
    assert any("kept existing $schema" in c for c in changes)


def test_apply_settings_dry_run_shows_diff(tmp_path: Path) -> None:
    result = sh.apply_settings(
        tmp_path,
        status_line_action="set",
        output_style_action="yaml-structured",
        enable_plugin=True,
        dry_run=True,
    )
    diff = str(result["diff"])
    assert result["changed"] is True
    assert "+++ b/.claude/settings.local.json" in diff
    assert '+  "$schema"' in diff
    assert '+  "outputStyle": "yaml-structured"' in diff
    # Dry run writes nothing.
    assert not _settings_path(tmp_path).exists()


def test_apply_settings_foreign_schema_only_is_noop(tmp_path: Path) -> None:
    # A foreign $schema with nothing else to do must not back up / rewrite the
    # file on every run — the "kept existing $schema" note is informational only.
    path = _settings_path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"$schema": "https://example.com/other.json"}))
    before = path.read_text()

    result = sh.apply_settings(
        tmp_path,
        status_line_action="skip",
        output_style_action="skip",
        enable_plugin=False,
        dry_run=False,
    )

    assert result["changed"] is False
    assert result["backup"] is None
    assert path.read_text() == before  # byte-unchanged
    assert list((tmp_path / ".claude").glob("settings.local.json.backup.*")) == []


def test_plugin_enabled_tolerates_null_enabled_plugins() -> None:
    assert sh._plugin_enabled({"enabledPlugins": None}) is False
    assert sh._plugin_enabled({"enabledPlugins": []}) is False
    assert sh._plugin_enabled({"enabledPlugins": {sh.PLUGIN_ID: True}}) is True


def test_detect_tolerates_null_enabled_plugins(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = _settings_path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"$schema": sh.SCHEMA_URL, "enabledPlugins": None}))

    rc = sh.main(["detect", "--repo-root", str(tmp_path)])

    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["plugin_enabled"] is False


def test_apply_settings_enable_plugin_over_null(tmp_path: Path) -> None:
    path = _settings_path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"$schema": sh.SCHEMA_URL, "enabledPlugins": None}))

    sh.apply_settings(
        tmp_path,
        status_line_action="skip",
        output_style_action="skip",
        enable_plugin=True,
        dry_run=False,
    )

    data = json.loads(path.read_text())
    assert data["enabledPlugins"][sh.PLUGIN_ID] is True


def test_apply_settings_idempotent(tmp_path: Path) -> None:
    args = {
        "status_line_action": "set",
        "output_style_action": "genui",
        "enable_plugin": True,
        "dry_run": False,
    }
    sh.apply_settings(tmp_path, **args)  # type: ignore[arg-type]
    backups_before = list((tmp_path / ".claude").glob("settings.local.json.backup.*"))
    result = sh.apply_settings(tmp_path, **args)  # type: ignore[arg-type]
    backups_after = list((tmp_path / ".claude").glob("settings.local.json.backup.*"))
    assert result["changed"] is False
    assert backups_before == backups_after


def test_apply_settings_backs_up_existing(tmp_path: Path) -> None:
    path = _settings_path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"$schema": sh.SCHEMA_URL}))
    result = sh.apply_settings(
        tmp_path,
        status_line_action="set",
        output_style_action="skip",
        enable_plugin=False,
        dry_run=False,
    )
    assert result["backup"] is not None
    assert Path(str(result["backup"])).exists()


def test_apply_settings_status_line_already_equal_is_noop(tmp_path: Path) -> None:
    path = _settings_path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"$schema": sh.SCHEMA_URL, "statusLine": sh.STATUS_LINE}))
    before = path.read_text()

    result = sh.apply_settings(
        tmp_path,
        status_line_action="set",
        output_style_action="skip",
        enable_plugin=False,
        dry_run=False,
    )

    assert result["changed"] is False
    assert path.read_text() == before  # byte-unchanged
    assert list((tmp_path / ".claude").glob("settings.local.json.backup.*")) == []


def test_apply_settings_output_style_already_equal_is_noop(tmp_path: Path) -> None:
    path = _settings_path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"$schema": sh.SCHEMA_URL, "outputStyle": "table-based"}))
    before = path.read_text()

    result = sh.apply_settings(
        tmp_path,
        status_line_action="skip",
        output_style_action="table-based",
        enable_plugin=False,
        dry_run=False,
    )

    assert result["changed"] is False
    assert path.read_text() == before
    assert list((tmp_path / ".claude").glob("settings.local.json.backup.*")) == []


def test_apply_settings_plugin_already_enabled_is_noop(tmp_path: Path) -> None:
    path = _settings_path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"$schema": sh.SCHEMA_URL, "enabledPlugins": {sh.PLUGIN_ID: True}}))
    before = path.read_text()

    result = sh.apply_settings(
        tmp_path,
        status_line_action="skip",
        output_style_action="skip",
        enable_plugin=True,
        dry_run=False,
    )

    assert result["changed"] is False
    data = json.loads(path.read_text())
    assert data["enabledPlugins"][sh.PLUGIN_ID] is True
    assert path.read_text() == before
    assert list((tmp_path / ".claude").glob("settings.local.json.backup.*")) == []


# --- env checks ---------------------------------------------------------------


def test_check_env_reports_structure() -> None:
    env = sh.check_env()
    assert set(env) == {"uv", "python3", "gh"}
    assert "installed" in env["gh"]
    assert "authenticated" in env["gh"]


def test_check_env_degrades_when_binaries_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sh.shutil, "which", lambda _name: None)
    env = sh.check_env()
    assert env["uv"]["ok"] is False
    assert env["uv"]["hint"]
    assert env["gh"]["installed"] is False
    assert env["gh"]["authenticated"] is False


# --- CLI ----------------------------------------------------------------------


def test_detect_emits_stable_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = sh.main(["detect", "--repo-root", str(tmp_path)])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    expected_keys = {
        "repo_root",
        "settings_exists",
        "settings_error",
        "has_schema",
        "has_status_line",
        "has_output_style",
        "output_style",
        "plugin_enabled",
        "gitignore_missing",
        "output_styles",
        "env",
    }
    assert expected_keys <= set(out)
    assert out["settings_exists"] is False
    assert out["gitignore_missing"] == _patterns(tmp_path)


def test_detect_reports_null_fields_on_invalid_settings(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = _settings_path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text("{ broken ")

    rc = sh.main(["detect", "--repo-root", str(tmp_path)])

    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["settings_exists"] is True
    assert out["settings_error"] is not None
    # Derived fields are unknown, not misleadingly False.
    for key in (
        "has_schema",
        "has_status_line",
        "has_output_style",
        "output_style",
        "plugin_enabled",
    ):
        assert out[key] is None


def test_apply_cli_rejects_unknown_style(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = sh.main(["apply", "--repo-root", str(tmp_path), "--output-style", "nonexistent"])
    assert rc == 2
    assert "output-style" in capsys.readouterr().err


def test_apply_cli_dry_run(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = sh.main([
        "apply",
        "--repo-root",
        str(tmp_path),
        "--gitignore",
        "--status-line",
        "set",
        "--dry-run",
    ])
    assert rc == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["dry_run"] is True
    assert not (tmp_path / ".gitignore").exists()
    assert not _settings_path(tmp_path).exists()


def test_apply_cli_invalid_settings_leaves_gitignore_untouched(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Invalid settings.local.json must abort before .gitignore is modified.
    settings = _settings_path(tmp_path)
    settings.parent.mkdir(parents=True)
    settings.write_text("{ broken ")

    rc = sh.main(["apply", "--repo-root", str(tmp_path), "--gitignore"])

    assert rc == 1
    assert "invalid JSON" in capsys.readouterr().err
    assert not (tmp_path / ".gitignore").exists()  # never touched
    assert settings.read_text() == "{ broken "  # untouched


def test_apply_cli_end_to_end(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = sh.main([
        "apply",
        "--repo-root",
        str(tmp_path),
        "--gitignore",
        "--status-line",
        "set",
        "--output-style",
        "table-based",
        "--enable-plugin",
    ])
    assert rc == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["gitignore"]["changed"] is True
    assert summary["settings"]["changed"] is True
    data = json.loads(_settings_path(tmp_path).read_text())
    assert data["outputStyle"] == "table-based"
    assert data["enabledPlugins"][sh.PLUGIN_ID] is True
