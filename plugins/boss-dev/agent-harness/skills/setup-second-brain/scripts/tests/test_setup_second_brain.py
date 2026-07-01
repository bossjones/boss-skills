"""Tests for setup_second_brain.py — config parse/merge, MCP merge, env, CLI."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import setup_second_brain as sb

# --- config parsing -----------------------------------------------------------


def test_parse_config_strips_quotes() -> None:
    text = 'OBSIDIAN_VAULT_PATH="/a/b"\nQMD_TRANSPORT=cli\n'
    parsed = sb.parse_config(text)
    assert parsed["OBSIDIAN_VAULT_PATH"] == "/a/b"
    assert parsed["QMD_TRANSPORT"] == "cli"


def test_parse_config_ignores_comments_and_blanks() -> None:
    text = "# a comment\n\nQMD_WIKI_COLLECTION=wiki\n"
    parsed = sb.parse_config(text)
    assert parsed == {"QMD_WIKI_COLLECTION": "wiki"}


# --- set_config_keys ----------------------------------------------------------


def test_set_config_keys_appends_missing() -> None:
    out = sb.set_config_keys('OBSIDIAN_VAULT_PATH="/v"\n', {"QMD_TRANSPORT": "cli"})
    assert 'OBSIDIAN_VAULT_PATH="/v"' in out
    assert 'QMD_TRANSPORT="cli"' in out


def test_set_config_keys_rewrites_in_place() -> None:
    text = 'QMD_TRANSPORT="mcp"\nOBSIDIAN_VAULT_PATH="/v"\n'
    out = sb.set_config_keys(text, {"QMD_TRANSPORT": "cli"})
    assert 'QMD_TRANSPORT="cli"' in out
    assert 'QMD_TRANSPORT="mcp"' not in out
    # unrelated line preserved, and only one QMD_TRANSPORT line remains
    assert out.count("QMD_TRANSPORT=") == 1
    assert 'OBSIDIAN_VAULT_PATH="/v"' in out


def test_set_config_keys_idempotent() -> None:
    text = ""
    once = sb.set_config_keys(text, {"QMD_TRANSPORT": "cli"})
    twice = sb.set_config_keys(once, {"QMD_TRANSPORT": "cli"})
    assert once == twice


# --- apply_qmd_config ---------------------------------------------------------


def _config(tmp_path: Path) -> Path:
    return tmp_path / "config"


def test_apply_qmd_config_writes_all_keys(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    result = sb.apply_qmd_config(
        cfg,
        transport="cli",
        wiki_collection="wiki",
        papers_collection="papers",
        search_mode="quality",
        dry_run=False,
    )
    assert result["changed"] is True
    text = cfg.read_text()
    for key in sb.QMD_KEYS:
        assert key in text


def test_apply_qmd_config_dry_run_writes_nothing(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    result = sb.apply_qmd_config(
        cfg,
        transport="cli",
        wiki_collection="wiki",
        papers_collection="papers",
        search_mode="quality",
        dry_run=True,
    )
    assert result["changed"] is True
    assert result["dry_run"] is True
    assert result["diff"]
    assert not cfg.exists()


def test_apply_qmd_config_backs_up_existing(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    cfg.write_text('OBSIDIAN_VAULT_PATH="/v"\n')
    result = sb.apply_qmd_config(
        cfg,
        transport="mcp",
        wiki_collection="wiki",
        papers_collection="papers",
        search_mode="quality",
        dry_run=False,
    )
    assert result["backup"] is not None
    assert Path(str(result["backup"])).exists()
    # pre-existing vault line preserved
    assert 'OBSIDIAN_VAULT_PATH="/v"' in cfg.read_text()


def test_apply_qmd_config_idempotent(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    kwargs = {
        "transport": "cli",
        "wiki_collection": "wiki",
        "papers_collection": "papers",
        "search_mode": "quality",
    }
    sb.apply_qmd_config(cfg, dry_run=False, **kwargs)
    first = cfg.read_text()
    backups_before = list(tmp_path.glob("config.backup.*"))

    second = sb.apply_qmd_config(cfg, dry_run=False, **kwargs)
    assert second["changed"] is False
    assert cfg.read_text() == first
    assert list(tmp_path.glob("config.backup.*")) == backups_before  # no new backup


# --- MCP merge ----------------------------------------------------------------


def test_apply_mcp_adds_server(tmp_path: Path) -> None:
    settings = tmp_path / "settings.json"
    result = sb.apply_mcp(settings, dry_run=False)
    assert result["changed"] is True
    data = json.loads(settings.read_text())
    assert data["mcpServers"]["qmd"] == sb.QMD_MCP_SERVER


def test_apply_mcp_preserves_existing_servers(tmp_path: Path) -> None:
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"mcpServers": {"other": {"command": "x"}}}))
    sb.apply_mcp(settings, dry_run=False)
    data = json.loads(settings.read_text())
    assert data["mcpServers"]["other"] == {"command": "x"}
    assert data["mcpServers"]["qmd"] == sb.QMD_MCP_SERVER


def test_apply_mcp_idempotent(tmp_path: Path) -> None:
    settings = tmp_path / "settings.json"
    sb.apply_mcp(settings, dry_run=False)
    first = settings.read_text()
    backups_before = list(tmp_path.glob("settings.json.backup.*"))

    result = sb.apply_mcp(settings, dry_run=False)
    assert result["changed"] is False
    assert settings.read_text() == first
    assert list(tmp_path.glob("settings.json.backup.*")) == backups_before


def test_apply_mcp_invalid_json_aborts(tmp_path: Path) -> None:
    settings = tmp_path / "settings.json"
    settings.write_text("{ not valid json ")
    with pytest.raises(sb.SettingsError):
        sb.apply_mcp(settings, dry_run=False)


def test_apply_mcp_dry_run_writes_nothing(tmp_path: Path) -> None:
    settings = tmp_path / "settings.json"
    result = sb.apply_mcp(settings, dry_run=True)
    assert result["changed"] is True
    assert result["diff"]
    assert not settings.exists()


# --- node version parsing -----------------------------------------------------


@pytest.mark.parametrize(
    ("version", "expected"),
    [("v22.15.1", 22), ("v20.19.5", 20), ("18.0.0", 18), (None, None), ("weird", None)],
)
def test_node_major(version: str | None, expected: int | None) -> None:
    assert sb._node_major(version) == expected


# --- detect CLI ---------------------------------------------------------------


def test_detect_reports_config_and_qmd_state(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    cfg = tmp_path / "config"
    cfg.write_text('OBSIDIAN_VAULT_PATH="/nope"\nQMD_WIKI_COLLECTION="wiki"\n')
    settings = tmp_path / "settings.json"

    rc = sb.main(["detect", "--config-path", str(cfg), "--settings-path", str(settings)])
    assert rc == 0

    report = json.loads(capsys.readouterr().out)
    assert report["config_exists"] is True
    assert report["vault_path"] == "/nope"
    assert report["vault_exists"] is False
    assert report["qmd_keys_set"]["QMD_WIKI_COLLECTION"] is True
    assert report["qmd_keys_set"]["QMD_TRANSPORT"] is False
    assert report["mcp_qmd_configured"] is False
    assert "env" in report


def test_detect_flags_invalid_settings(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    cfg = tmp_path / "config"
    settings = tmp_path / "settings.json"
    settings.write_text("{ broken")

    rc = sb.main(["detect", "--config-path", str(cfg), "--settings-path", str(settings)])
    assert rc == 0
    report = json.loads(capsys.readouterr().out)
    assert report["settings_error"] is not None
    assert report["mcp_qmd_configured"] is None


# --- apply CLI ----------------------------------------------------------------


def test_apply_cli_cli_transport_skips_mcp(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    cfg = tmp_path / "config"
    settings = tmp_path / "settings.json"
    rc = sb.main([
        "apply",
        "--config-path",
        str(cfg),
        "--settings-path",
        str(settings),
        "--qmd-config",
        "--transport",
        "cli",
    ])
    assert rc == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["qmd_config"]["changed"] is True
    assert summary["mcp"] == {"changed": False, "skipped": True}
    assert not settings.exists()


def test_apply_cli_mcp_transport_writes_both(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    cfg = tmp_path / "config"
    settings = tmp_path / "settings.json"
    rc = sb.main([
        "apply",
        "--config-path",
        str(cfg),
        "--settings-path",
        str(settings),
        "--qmd-config",
        "--transport",
        "mcp",
    ])
    assert rc == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["qmd_config"]["changed"] is True
    assert summary["mcp"]["changed"] is True
    assert 'QMD_TRANSPORT="mcp"' in cfg.read_text()
    assert json.loads(settings.read_text())["mcpServers"]["qmd"] == sb.QMD_MCP_SERVER


def test_apply_cli_mcp_invalid_settings_returns_1(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    cfg = tmp_path / "config"
    settings = tmp_path / "settings.json"
    settings.write_text("{ broken")
    rc = sb.main([
        "apply",
        "--config-path",
        str(cfg),
        "--settings-path",
        str(settings),
        "--qmd-config",
        "--transport",
        "mcp",
    ])
    assert rc == 1
    # config must NOT be written when settings validation fails first
    assert not cfg.exists()
