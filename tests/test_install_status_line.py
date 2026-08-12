"""Unit tests for ``plugins/boss-dev/agent-harness/scripts/install_status_line.py``.

The pure planner (``plan``) and the mutating engine
(``execute``/``uninstall``/``restore``) are driven entirely under ``tmp_path``:
every engine call takes explicit ``settings_path`` / ``backup_root`` arguments, so
no test monkeypatches module globals and no test touches the real ``~/.claude/`` or
the real project ``.claude/settings.local.json``. PEP 723 script is loaded via
``importlib`` (the ``if __name__ == "__main__"`` guard keeps import side-effect-free).
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT = (
    Path(__file__).resolve().parent.parent
    / "plugins"
    / "boss-dev"
    / "agent-harness"
    / "scripts"
    / "install_status_line.py"
)


def _load(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(path.stem.replace("-", "_"), path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


isl = _load(SCRIPT)


# --------------------------------------------------------------------------- #
# Builders
# --------------------------------------------------------------------------- #


def _desired(variant: str = "status_line_v10.py") -> dict:
    return isl.build_status_line_block(isl.resolve_variant_path(variant))


def _settings_file(path: Path, data: dict, *, indent: int = 2) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=indent) + "\n", encoding="utf-8")
    return path


def _backup_stamps(settings_path: Path, backup_root: Path) -> list[str]:
    d = isl.backup_dir_for(settings_path, backup_root)
    if not d.is_dir():
        return []
    return sorted(p.name for p in d.iterdir() if p.is_dir())


def _latest_manifest(settings_path: Path, backup_root: Path) -> dict:
    d = isl.backup_dir_for(settings_path, backup_root)
    latest = (d / isl.LATEST_POINTER).read_text().strip()
    return json.loads((d / latest / isl.MANIFEST_NAME).read_text())


# --------------------------------------------------------------------------- #
# build_status_line_block / resolve_variant_path
# --------------------------------------------------------------------------- #


def test_build_block_is_absolute_no_plugin_root_var() -> None:
    block = _desired()
    assert block["type"] == "command"
    assert "${CLAUDE_PLUGIN_ROOT}" not in block["command"]
    assert block["command"].startswith("uv run ")
    # The quoted path is absolute.
    assert '"/' in block["command"]


def test_resolve_variant_rejects_traversal() -> None:
    with pytest.raises(ValueError):
        isl.resolve_variant_path("../evil.py")
    with pytest.raises(ValueError):
        isl.resolve_variant_path("subdir/evil.py")


def test_resolve_variant_unknown_raises_filenotfound() -> None:
    with pytest.raises(FileNotFoundError):
        isl.resolve_variant_path("status_line_v999.py")


# --------------------------------------------------------------------------- #
# plan (pure)
# --------------------------------------------------------------------------- #


def test_plan_install_when_no_status_line() -> None:
    assert isl.plan({}, _desired()).kind == isl.INSTALL


def test_plan_current_when_identical() -> None:
    desired = _desired()
    assert isl.plan({"statusLine": dict(desired)}, desired).kind == isl.CURRENT


def test_plan_replace_ours_when_different_variant() -> None:
    settings = {"statusLine": _desired("status_line_v6.py")}
    assert isl.plan(settings, _desired("status_line_v10.py")).kind == isl.REPLACE_OURS


def test_plan_foreign_when_third_party() -> None:
    settings = {"statusLine": {"type": "command", "command": "echo hi"}}
    assert isl.plan(settings, _desired()).kind == isl.FOREIGN


# --------------------------------------------------------------------------- #
# execute (under tmp_path)
# --------------------------------------------------------------------------- #


def test_execute_creates_absent_file(tmp_path: Path) -> None:
    settings_path = tmp_path / ".claude" / "settings.local.json"
    backup_root = tmp_path / "backups"

    rc = isl.execute(settings_path, backup_root, _desired())

    assert rc == 0
    assert settings_path.is_file()
    data = json.loads(settings_path.read_text())
    assert data["statusLine"] == _desired()
    manifest = _latest_manifest(settings_path, backup_root)
    assert manifest["existed"] is False
    assert manifest["backup_path"] is None


def test_execute_preserves_keys_order_indent_and_backs_up(tmp_path: Path) -> None:
    settings_path = tmp_path / "settings.local.json"
    backup_root = tmp_path / "backups"
    original = {"permissions": {"allow": ["Bash"]}, "env": {"A": "1"}}
    _settings_file(settings_path, original, indent=4)
    original_bytes = settings_path.read_bytes()

    rc = isl.execute(settings_path, backup_root, _desired())

    assert rc == 0
    text = settings_path.read_text()
    data = json.loads(text)
    # Pre-existing keys survive and keep their relative order; statusLine appended last.
    assert list(data.keys()) == ["permissions", "env", "statusLine"]
    # Indent preserved (4-space in, 4-space out).
    assert '\n    "permissions"' in text
    # Backup is byte-identical to the original.
    manifest = _latest_manifest(settings_path, backup_root)
    assert manifest["existed"] is True
    backup_path = Path(manifest["backup_path"])
    assert backup_path.read_bytes() == original_bytes


def test_execute_current_is_idempotent_no_new_backup(tmp_path: Path) -> None:
    settings_path = tmp_path / "settings.local.json"
    backup_root = tmp_path / "backups"

    isl.execute(settings_path, backup_root, _desired())
    stamps_after_first = _backup_stamps(settings_path, backup_root)

    rc = isl.execute(settings_path, backup_root, _desired())

    assert rc == 0
    assert _backup_stamps(settings_path, backup_root) == stamps_after_first


def test_execute_foreign_refuses_and_leaves_file_untouched(tmp_path: Path) -> None:
    settings_path = tmp_path / "settings.local.json"
    backup_root = tmp_path / "backups"
    _settings_file(settings_path, {"statusLine": {"type": "command", "command": "echo foreign"}})
    before = settings_path.read_bytes()

    rc = isl.execute(settings_path, backup_root, _desired())

    assert rc != 0
    assert settings_path.read_bytes() == before


def test_execute_foreign_with_force_replaces_and_backs_up(tmp_path: Path) -> None:
    settings_path = tmp_path / "settings.local.json"
    backup_root = tmp_path / "backups"
    foreign = {"statusLine": {"type": "command", "command": "echo foreign"}}
    _settings_file(settings_path, foreign)
    original_bytes = settings_path.read_bytes()

    rc = isl.execute(settings_path, backup_root, _desired(), force=True)

    assert rc == 0
    assert json.loads(settings_path.read_text())["statusLine"] == _desired()
    backup_path = Path(_latest_manifest(settings_path, backup_root)["backup_path"])
    assert backup_path.read_bytes() == original_bytes


def test_execute_malformed_json_aborts_fail_closed(tmp_path: Path) -> None:
    settings_path = tmp_path / "settings.local.json"
    backup_root = tmp_path / "backups"
    settings_path.write_text("{ this is not json", encoding="utf-8")
    before = settings_path.read_bytes()

    rc = isl.execute(settings_path, backup_root, _desired())

    assert rc != 0
    assert settings_path.read_bytes() == before


def test_execute_empty_file_treated_as_malformed(tmp_path: Path) -> None:
    settings_path = tmp_path / "settings.local.json"
    backup_root = tmp_path / "backups"
    settings_path.write_text("", encoding="utf-8")

    rc = isl.execute(settings_path, backup_root, _desired())

    assert rc != 0
    assert settings_path.read_bytes() == b""


def test_execute_leaves_no_tmp_file(tmp_path: Path) -> None:
    settings_path = tmp_path / "settings.local.json"
    backup_root = tmp_path / "backups"

    isl.execute(settings_path, backup_root, _desired())

    leftovers = [p.name for p in settings_path.parent.iterdir() if p.name.endswith(".tmp")]
    assert leftovers == []


# --------------------------------------------------------------------------- #
# uninstall
# --------------------------------------------------------------------------- #


def test_uninstall_removes_only_our_block(tmp_path: Path) -> None:
    settings_path = tmp_path / "settings.local.json"
    backup_root = tmp_path / "backups"
    _settings_file(settings_path, {"env": {"A": "1"}})
    isl.execute(settings_path, backup_root, _desired())

    rc = isl.uninstall(settings_path, backup_root)

    assert rc == 0
    data = json.loads(settings_path.read_text())
    assert "statusLine" not in data
    assert data["env"] == {"A": "1"}


def test_uninstall_refuses_foreign_without_force(tmp_path: Path) -> None:
    settings_path = tmp_path / "settings.local.json"
    backup_root = tmp_path / "backups"
    foreign = {"statusLine": {"type": "command", "command": "echo foreign"}}
    _settings_file(settings_path, foreign)
    before = settings_path.read_bytes()

    rc = isl.uninstall(settings_path, backup_root)

    assert rc != 0
    assert settings_path.read_bytes() == before


# --------------------------------------------------------------------------- #
# restore
# --------------------------------------------------------------------------- #


def test_restore_reproduces_original_byte_for_byte(tmp_path: Path) -> None:
    settings_path = tmp_path / "settings.local.json"
    backup_root = tmp_path / "backups"
    _settings_file(settings_path, {"env": {"A": "1"}}, indent=4)
    original_bytes = settings_path.read_bytes()
    isl.execute(settings_path, backup_root, _desired())
    assert settings_path.read_bytes() != original_bytes  # sanity: install changed it

    rc = isl.restore(settings_path, backup_root, yes=True)

    assert rc == 0
    assert settings_path.read_bytes() == original_bytes


def test_restore_deletes_file_that_did_not_exist(tmp_path: Path) -> None:
    settings_path = tmp_path / ".claude" / "settings.local.json"
    backup_root = tmp_path / "backups"
    isl.execute(settings_path, backup_root, _desired())
    assert settings_path.is_file()

    rc = isl.restore(settings_path, backup_root, yes=True)

    assert rc == 0
    assert not settings_path.exists()


def test_restore_after_uninstall_returns_install_time_pre_image(tmp_path: Path) -> None:
    """install -> uninstall -> restore must land on the *pre-install* payload.

    Regression: ``uninstall`` used to move the ``latest`` pointer to its own (post-install)
    backup, so ``--restore`` re-added the status-line block instead of reverting to the
    original settings.
    """
    settings_path = tmp_path / "settings.local.json"
    backup_root = tmp_path / "backups"
    _settings_file(settings_path, {"env": {"A": "1"}}, indent=4)
    original_bytes = settings_path.read_bytes()

    assert isl.execute(settings_path, backup_root, _desired()) == 0
    assert isl.uninstall(settings_path, backup_root) == 0

    rc = isl.restore(settings_path, backup_root, yes=True)

    assert rc == 0
    assert settings_path.read_bytes() == original_bytes
    assert "statusLine" not in json.loads(settings_path.read_text())


def test_uninstall_still_writes_its_own_backup(tmp_path: Path) -> None:
    """The uninstall backup is kept (just not the restore target)."""
    settings_path = tmp_path / "settings.local.json"
    backup_root = tmp_path / "backups"
    _settings_file(settings_path, {"env": {"A": "1"}})

    isl.execute(settings_path, backup_root, _desired())
    installed_bytes = settings_path.read_bytes()
    isl.uninstall(settings_path, backup_root)

    manifests = [
        json.loads((d / isl.MANIFEST_NAME).read_text())
        for d in sorted(isl.backup_dir_for(settings_path, backup_root).iterdir())
        if d.is_dir()
    ]
    uninstall_manifests = [m for m in manifests if m["plan_kind"] == "uninstall"]
    assert len(uninstall_manifests) == 1
    assert Path(uninstall_manifests[0]["backup_path"]).read_bytes() == installed_bytes


def test_restore_refuses_to_delete_target_with_user_added_settings(tmp_path: Path) -> None:
    """Absent-before-install + user-added settings -> refuse, never destroy user config."""
    settings_path = tmp_path / ".claude" / "settings.local.json"
    backup_root = tmp_path / "backups"
    assert isl.execute(settings_path, backup_root, _desired()) == 0

    # The user later adds unrelated configuration to the same file.
    data = json.loads(settings_path.read_text())
    data["permissions"] = {"allow": ["Bash"]}
    _settings_file(settings_path, data)
    before = settings_path.read_bytes()

    rc = isl.restore(settings_path, backup_root, yes=True)

    assert rc != 0
    assert settings_path.read_bytes() == before
    assert json.loads(settings_path.read_text())["permissions"] == {"allow": ["Bash"]}


def test_restore_refuses_to_delete_target_holding_a_foreign_status_line(tmp_path: Path) -> None:
    settings_path = tmp_path / ".claude" / "settings.local.json"
    backup_root = tmp_path / "backups"
    assert isl.execute(settings_path, backup_root, _desired()) == 0
    _settings_file(settings_path, {"statusLine": {"type": "command", "command": "echo foreign"}})
    before = settings_path.read_bytes()

    rc = isl.restore(settings_path, backup_root, yes=True)

    assert rc != 0
    assert settings_path.read_bytes() == before


def test_restore_deletes_target_that_only_holds_our_block(tmp_path: Path) -> None:
    """The user-preserving guard must not break the plain install -> restore path."""
    settings_path = tmp_path / ".claude" / "settings.local.json"
    backup_root = tmp_path / "backups"
    isl.execute(settings_path, backup_root, _desired())

    rc = isl.restore(settings_path, backup_root, yes=True)

    assert rc == 0
    assert not settings_path.exists()


def test_restore_with_no_backup_is_noop(tmp_path: Path) -> None:
    settings_path = tmp_path / "settings.local.json"
    backup_root = tmp_path / "backups"

    rc = isl.restore(settings_path, backup_root, yes=True)

    assert rc == 0


# --------------------------------------------------------------------------- #
# check
# --------------------------------------------------------------------------- #


def test_check_returns_zero_for_install(tmp_path: Path) -> None:
    settings_path = tmp_path / "settings.local.json"
    _settings_file(settings_path, {"env": {}})
    assert isl.check(settings_path, _desired()) == 0


def test_check_returns_nonzero_for_foreign(tmp_path: Path) -> None:
    settings_path = tmp_path / "settings.local.json"
    _settings_file(settings_path, {"statusLine": {"type": "command", "command": "echo foreign"}})
    assert isl.check(settings_path, _desired()) != 0


# --------------------------------------------------------------------------- #
# backup timestamp collision
# --------------------------------------------------------------------------- #


def test_write_backup_collision_gets_suffix(tmp_path: Path) -> None:
    settings_path = tmp_path / "settings.local.json"
    backup_root = tmp_path / "backups"
    _settings_file(settings_path, {"env": {"A": "1"}})

    first = isl.write_backup(settings_path, backup_root, isl.INSTALL, "status_line_v10.py")
    second = isl.write_backup(settings_path, backup_root, isl.INSTALL, "status_line_v10.py")

    assert first != second
    assert first.is_dir()
    assert second.is_dir()
