"""Unit tests for ``scripts/symlink_plugins.py`` (importlib load).

Pure planners (``discover_plugins``/``plan_actions``) and the mutating
``execute``/``restore``/``check`` engine are driven against a synthetic
``plugins/`` + ``.claude/`` tree under ``tmp_path``. Each engine call takes an
explicit ``repo_root`` so no monkeypatching of module globals is needed; the
module's ``REPO_ROOT`` is only used for display fallbacks.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from types import ModuleType

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "symlink_plugins.py"


def _load(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(path.stem.replace("-", "_"), path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


sp = _load(SCRIPT)


# --------------------------------------------------------------------------- #
# Builders
# --------------------------------------------------------------------------- #


def _plugin_root(repo: Path, rel: str) -> Path:
    root = repo / "plugins" / rel
    (root / ".claude-plugin").mkdir(parents=True, exist_ok=True)
    (root / ".claude-plugin" / "plugin.json").write_text("{}")
    return root


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def _skill(root: Path, name: str, body: str = "# skill\n") -> None:
    _write(root / "skills" / name / "SKILL.md", body)


def _run(repo: Path, components: tuple[str, ...], *, copy: bool = False):
    plugins = sp.discover_plugins(repo)
    actions = sp.plan_actions(repo, plugins, components)
    return sp.execute(repo, actions, copy=copy)


def _kinds(repo: Path, components: tuple[str, ...]) -> list[str]:
    plugins = sp.discover_plugins(repo)
    return [a.kind for a in sp.plan_actions(repo, plugins, components)]


# --------------------------------------------------------------------------- #
# Discovery + planning
# --------------------------------------------------------------------------- #


def test_discover_plugins_sorted(tmp_path: Path) -> None:
    _plugin_root(tmp_path, "z/late")
    _plugin_root(tmp_path, "a/early")
    found = sp.discover_plugins(tmp_path)
    rel = [p.relative_to(tmp_path).as_posix() for p in found]
    assert rel == ["plugins/a/early", "plugins/z/late"]


# --------------------------------------------------------------------------- #
# Skills: dir-level relative symlink
# --------------------------------------------------------------------------- #


def test_skill_dir_symlink_is_relative_and_resolves(tmp_path: Path) -> None:
    root = _plugin_root(tmp_path, "cat/p")
    _skill(root, "foo")
    _run(tmp_path, ("skills",))

    target = tmp_path / ".claude" / "skills" / "foo"
    assert target.is_symlink()
    link = os.readlink(target)
    assert not os.path.isabs(link) and link.startswith("..")
    assert (target / "SKILL.md").exists()


# --------------------------------------------------------------------------- #
# Leaf files + nested intermediate dirs
# --------------------------------------------------------------------------- #


def test_skills_dir_without_marker_is_not_mirrored(tmp_path: Path) -> None:
    root = _plugin_root(tmp_path, "cat/p")
    _skill(root, "real")
    (root / "skills" / "logs").mkdir(parents=True)  # runtime dir, no SKILL.md
    (root / "skills" / "logs" / "run.json").write_text("{}")
    _run(tmp_path, ("skills",))

    assert (tmp_path / ".claude" / "skills" / "real").is_symlink()
    assert not (tmp_path / ".claude" / "skills" / "logs").exists()


def test_command_leaf_and_nested_agents(tmp_path: Path) -> None:
    root = _plugin_root(tmp_path, "cat/p")
    _write(root / "commands" / "build.md", "cmd")
    _write(root / "agents" / "team" / "x.md", "agent")
    _run(tmp_path, ("commands", "agents"))

    build = tmp_path / ".claude" / "commands" / "build.md"
    assert build.is_symlink() and build.read_text() == "cmd"

    team_dir = tmp_path / ".claude" / "agents" / "team"
    assert team_dir.is_dir() and not team_dir.is_symlink()  # intermediate = real dir
    leaf = team_dir / "x.md"
    assert leaf.is_symlink() and leaf.read_text() == "agent"


# --------------------------------------------------------------------------- #
# Orphans left untouched
# --------------------------------------------------------------------------- #


def test_orphan_skill_untouched(tmp_path: Path) -> None:
    root = _plugin_root(tmp_path, "cat/p")
    _skill(root, "sourced")
    orphan = _write(tmp_path / ".claude" / "skills" / "orphan" / "SKILL.md", "mine").parent

    kinds = _kinds(tmp_path, ("skills",))
    assert sp.ORPHAN_LEFT in kinds
    _run(tmp_path, ("skills",))

    assert not orphan.is_symlink() and (orphan / "SKILL.md").read_text() == "mine"


# --------------------------------------------------------------------------- #
# Backup + replace records a manifest and preserves the original
# --------------------------------------------------------------------------- #


def test_backup_replace_and_manifest(tmp_path: Path) -> None:
    root = _plugin_root(tmp_path, "cat/p")
    _write(root / "commands" / "build.md", "plugin-version")
    _write(tmp_path / ".claude" / "commands" / "build.md", "old-copy")

    result = _run(tmp_path, ("commands",))
    target = tmp_path / ".claude" / "commands" / "build.md"
    assert target.is_symlink() and target.read_text() == "plugin-version"

    assert result.backup_dir is not None
    backup = result.backup_dir / ".claude" / "commands" / "build.md"
    assert backup.read_text() == "old-copy"

    import json

    manifest = json.loads((result.backup_dir / "manifest.json").read_text())
    entry = next(e for e in manifest["entries"] if e["target"].endswith("build.md"))
    assert entry["action"] == sp.BACKUP_REPLACE and entry["backup_path"] is not None


# --------------------------------------------------------------------------- #
# Idempotency
# --------------------------------------------------------------------------- #


def test_second_run_is_all_skip(tmp_path: Path) -> None:
    root = _plugin_root(tmp_path, "cat/p")
    _skill(root, "foo")
    _write(root / "commands" / "build.md", "cmd")
    _run(tmp_path, ("skills", "commands"))

    second = _run(tmp_path, ("skills", "commands"))
    assert not second.created and not second.backed_up
    kinds = _kinds(tmp_path, ("skills", "commands"))
    assert set(kinds) <= {sp.SKIP, sp.ORPHAN_LEFT}


# --------------------------------------------------------------------------- #
# Collision across plugins
# --------------------------------------------------------------------------- #


def test_collision_first_wins_second_conflict(tmp_path: Path) -> None:
    p1 = _plugin_root(tmp_path, "cat/a-first")
    p2 = _plugin_root(tmp_path, "cat/b-second")
    _write(p1 / "commands" / "dup.md", "from-first")
    _write(p2 / "commands" / "dup.md", "from-second")

    plugins = sp.discover_plugins(tmp_path)
    actions = sp.plan_actions(tmp_path, plugins, ("commands",))
    assert sum(1 for a in actions if a.kind == sp.CONFLICT) == 1
    assert sum(1 for a in actions if a.kind == sp.CREATE) == 1

    sp.execute(tmp_path, actions, copy=False)
    target = tmp_path / ".claude" / "commands" / "dup.md"
    assert target.read_text() == "from-first"


# --------------------------------------------------------------------------- #
# --check exit codes
# --------------------------------------------------------------------------- #


def test_check_broken_link_exits_nonzero(tmp_path: Path) -> None:
    _plugin_root(tmp_path, "cat/p")
    # A managed symlink that points nowhere.
    link = tmp_path / ".claude" / "commands" / "x.md"
    link.parent.mkdir(parents=True)
    link.symlink_to("../../plugins/cat/p/commands/gone.md")

    assert sp.main(["--check", "--repo-root", str(tmp_path), "--components", "commands"]) == 1


def test_check_consistent_exits_zero(tmp_path: Path) -> None:
    root = _plugin_root(tmp_path, "cat/p")
    _write(root / "commands" / "build.md", "cmd")
    _run(tmp_path, ("commands",))

    assert sp.main(["--check", "--repo-root", str(tmp_path), "--components", "commands"]) == 0


# --------------------------------------------------------------------------- #
# Restore round-trips the tree bit-for-bit
# --------------------------------------------------------------------------- #


def _snapshot(root: Path) -> dict[str, tuple[str, str]]:
    """Map repo-relative path → (kind, payload), excluding the .backups tree."""
    snap: dict[str, tuple[str, str]] = {}
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        if rel.startswith(".backups"):
            continue
        if path.is_symlink():
            snap[rel] = ("symlink", os.readlink(path))
        elif path.is_dir():
            snap[rel] = ("dir", "")
        else:
            snap[rel] = ("file", path.read_text())
    return snap


def test_restore_returns_pre_run_state(tmp_path: Path) -> None:
    root = _plugin_root(tmp_path, "cat/p")
    _skill(root, "foo")
    _write(root / "commands" / "build.md", "plugin-version")
    _write(root / "agents" / "team" / "x.md", "agent")
    # Pre-existing real copy that will be backed up.
    _write(tmp_path / ".claude" / "commands" / "build.md", "old-copy")

    before = _snapshot(tmp_path)
    _run(tmp_path, ("skills", "commands", "agents"))
    assert (tmp_path / ".claude" / "commands" / "build.md").is_symlink()

    assert sp.main(["--restore", "--repo-root", str(tmp_path)]) == 0
    assert _snapshot(tmp_path) == before


# --------------------------------------------------------------------------- #
# --copy produces real copies, not symlinks
# --------------------------------------------------------------------------- #


def test_copy_mode_makes_real_files(tmp_path: Path) -> None:
    root = _plugin_root(tmp_path, "cat/p")
    _skill(root, "foo")
    _write(root / "commands" / "build.md", "cmd")
    _run(tmp_path, ("skills", "commands"), copy=True)

    skill = tmp_path / ".claude" / "skills" / "foo"
    cmd = tmp_path / ".claude" / "commands" / "build.md"
    assert not skill.is_symlink() and skill.is_dir()
    assert not cmd.is_symlink() and cmd.read_text() == "cmd"
