"""Tests for the read-only harness doctor."""

from __future__ import annotations

import json
from pathlib import Path

import harness_doctor as doctor


def test_directory_size_skips_symlink_targets(tmp_path: Path) -> None:
    storage = tmp_path / "storage"
    storage.mkdir()
    (storage / "event.jsonl").write_bytes(b"event")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.jsonl").write_bytes(b"outside")
    (storage / "outside-link").symlink_to(outside, target_is_directory=True)

    assert doctor.directory_size(storage) == {"files": 1, "bytes": 5}


def test_build_report_breaks_down_storage_and_stale_artifacts(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    root = doctor._harness_root(tmp_path)
    (root / "logs").mkdir(parents=True)
    (root / "logs" / "event.jsonl").write_bytes(b"log")
    (root / "data").mkdir()
    (root / "data" / "session.json").write_bytes(b"data")
    (tmp_path / "logs").mkdir()
    (tmp_path / "logs" / "old.json").write_bytes(b"old")
    (tmp_path / ".claude" / "data").mkdir(parents=True)

    report = doctor.build_report(tmp_path)

    assert set(report["harness_root"]["storage"]) == {"logs", "data", "cache"}
    assert report["harness_root"]["storage"]["logs"] == {"files": 1, "bytes": 3}
    assert report["harness_root"]["storage"]["data"] == {"files": 1, "bytes": 4}
    assert report["stale_artifacts"]["logs"]["exists"] is True
    assert report["stale_artifacts"]["claude_data"]["exists"] is True
    assert report["advisory"] is True


def test_enabled_plugins_reports_current_manifest_version(tmp_path: Path) -> None:
    settings = tmp_path / ".claude" / "settings.local.json"
    settings.parent.mkdir()
    settings.write_text(json.dumps({"enabledPlugins": {"agent-harness@boss-skills": True}}))

    plugins = doctor.enabled_plugins(tmp_path)

    assert plugins == [
        {
            "identity": "agent-harness@boss-skills",
            "version": doctor._manifest()["version"],
            "settings_path": ".claude/settings.local.json",
        }
    ]


def test_main_emits_read_only_json(tmp_path: Path, capsys) -> None:
    rc = doctor.main(["--repo-root", str(tmp_path)])

    assert rc == 0
    report = json.loads(capsys.readouterr().out)
    assert report["repo_root"] == str(tmp_path)
    assert report["advisory"] is True
