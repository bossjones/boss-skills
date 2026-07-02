"""Unit tests for ``scripts/verify-structure.py`` (hyphenated → importlib load).

Granular pure validators are unit-tested with explicit ``Path``/``dict`` args;
a handful of integration tests drive ``check_marketplace_structure``/``main``
against a ``tmp_path`` tree with the module's ``__file__`` monkeypatched so
``Path(__file__).parent.parent`` resolves to the temp repo root.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "verify-structure.py"


def _load(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(path.stem.replace("-", "_"), path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


vs = _load(SCRIPT)


def _plugin(tmp: Path, name: str, *, manifest: dict | None = None, readme: bool = True) -> Path:
    d = tmp / "plugins" / name
    (d / ".claude-plugin").mkdir(parents=True)
    if manifest is not None:
        (d / ".claude-plugin" / "plugin.json").write_text(json.dumps(manifest))
    if readme:
        (d / "README.md").write_text("# x")
    return d


# --------------------------------------------------------------------------- #
# validate_plugin_path
# --------------------------------------------------------------------------- #
class TestValidatePluginPath:
    def test_inside_base_ok(self, tmp_path: Path) -> None:
        path, err = vs.validate_plugin_path(tmp_path, "sub/file.txt", "ctx")
        assert err is None
        assert path == (tmp_path.resolve() / "sub" / "file.txt")

    def test_traversal_escapes(self, tmp_path: Path) -> None:
        path, err = vs.validate_plugin_path(tmp_path, "../evil", "ctx")
        assert path is None
        assert err is not None and "escapes base directory" in err

    def test_absolute_path_escapes(self, tmp_path: Path) -> None:
        path, err = vs.validate_plugin_path(tmp_path, "/etc/passwd", "ctx")
        assert path is None
        assert err is not None and "escapes base directory" in err


# --------------------------------------------------------------------------- #
# load_plugin_json_file
# --------------------------------------------------------------------------- #
class TestLoadPluginJsonFile:
    def test_missing(self, tmp_path: Path) -> None:
        data, errs = vs.load_plugin_json_file(tmp_path, "nope.json", "ctx")
        assert data is None
        assert errs and "File not found" in errs[0]

    def test_invalid_json(self, tmp_path: Path) -> None:
        (tmp_path / "bad.json").write_text("{not json")
        data, errs = vs.load_plugin_json_file(tmp_path, "bad.json", "ctx")
        assert data is None
        assert errs and "Invalid JSON" in errs[0]

    def test_non_utf8(self, tmp_path: Path) -> None:
        (tmp_path / "b.json").write_bytes(b"\xff\xfe\x00bad")
        data, errs = vs.load_plugin_json_file(tmp_path, "b.json", "ctx")
        assert data is None
        assert errs and "not valid UTF-8" in errs[0]

    def test_valid(self, tmp_path: Path) -> None:
        (tmp_path / "ok.json").write_text('{"a": 1}')
        data, errs = vs.load_plugin_json_file(tmp_path, "ok.json", "ctx")
        assert data == {"a": 1}
        assert errs == []

    def test_traversal(self, tmp_path: Path) -> None:
        data, errs = vs.load_plugin_json_file(tmp_path, "../x.json", "ctx")
        assert data is None
        assert errs and "escapes base directory" in errs[0]


# --------------------------------------------------------------------------- #
# validate_json_schema
# --------------------------------------------------------------------------- #
class TestValidateJsonSchema:
    def test_valid(self) -> None:
        schema = {"type": "object", "required": ["x"]}
        assert vs.validate_json_schema({"x": 1}, schema, "ctx") == []

    def test_violation(self) -> None:
        schema = {"type": "object", "required": ["x"]}
        errs = vs.validate_json_schema({}, schema, "ctx")
        assert errs and "required" in errs[0]

    def test_malformed_schema_is_caught_gracefully(self) -> None:
        # A bad schema must not raise — it is reported as an error string.
        errs = vs.validate_json_schema({}, {"type": 123}, "ctx")
        assert errs and errs[0].startswith("ctx: ")


# --------------------------------------------------------------------------- #
# validate_marketplace_json
# --------------------------------------------------------------------------- #
class TestValidateMarketplaceJson:
    def test_valid(self) -> None:
        data = {
            "name": "mp",
            "owner": {"name": "o"},
            "plugins": [{"name": "p", "source": "./plugins/p"}],
        }
        assert vs.validate_marketplace_json(data) == []

    def test_missing_required(self) -> None:
        assert vs.validate_marketplace_json({"name": "mp"}) != []

    def test_non_kebab_name(self) -> None:
        data = {"name": "Bad_Name", "owner": {"name": "o"}, "plugins": [{"name": "p", "source": "x"}]}
        assert any("name" in e for e in vs.validate_marketplace_json(data))

    def test_empty_plugins(self) -> None:
        data = {"name": "mp", "owner": {"name": "o"}, "plugins": []}
        assert vs.validate_marketplace_json(data) != []

    def test_entry_missing_source(self) -> None:
        data = {"name": "mp", "owner": {"name": "o"}, "plugins": [{"name": "p"}]}
        assert any("source" in e for e in vs.validate_marketplace_json(data))


# --------------------------------------------------------------------------- #
# validate_markdown_frontmatter
# --------------------------------------------------------------------------- #
class TestValidateMarkdownFrontmatter:
    def _md(self, tmp_path: Path, text: str) -> Path:
        d = tmp_path / "p" / "skills"
        d.mkdir(parents=True)
        f = d / "SKILL.md"
        f.write_text(text)
        return f

    def test_valid(self, tmp_path: Path) -> None:
        f = self._md(tmp_path, "---\nname: x\ndescription: y\n---\nbody")
        assert vs.validate_markdown_frontmatter(f, ["name", "description"], "p") == []

    def test_missing_field(self, tmp_path: Path) -> None:
        f = self._md(tmp_path, "---\nname: x\n---\nbody")
        errs = vs.validate_markdown_frontmatter(f, ["name", "description"], "p")
        assert any("Missing required field 'description'" in e for e in errs)

    def test_empty_field(self, tmp_path: Path) -> None:
        f = self._md(tmp_path, "---\nname: x\ndescription:\n---\nb")
        errs = vs.validate_markdown_frontmatter(f, ["description"], "p")
        assert any("empty or null" in e for e in errs)

    def test_no_frontmatter(self, tmp_path: Path) -> None:
        f = self._md(tmp_path, "no frontmatter")
        assert any("Missing YAML frontmatter" in e for e in vs.validate_markdown_frontmatter(f, ["name"], "p"))

    def test_missing_closing(self, tmp_path: Path) -> None:
        f = self._md(tmp_path, "---\nname: x")
        assert any("Malformed frontmatter" in e for e in vs.validate_markdown_frontmatter(f, ["name"], "p"))

    def test_bad_yaml(self, tmp_path: Path) -> None:
        f = self._md(tmp_path, "---\nx: [unclosed\n---\nb")
        assert any("Invalid YAML" in e for e in vs.validate_markdown_frontmatter(f, ["x"], "p"))

    def test_non_mapping(self, tmp_path: Path) -> None:
        f = self._md(tmp_path, "---\n- a\n- b\n---\nb")
        assert any("must be a YAML mapping" in e for e in vs.validate_markdown_frontmatter(f, ["x"], "p"))


# --------------------------------------------------------------------------- #
# component placement / skills / commands / agents
# --------------------------------------------------------------------------- #
class TestComponentDirectories:
    def test_placement_in_claude_plugin_errors(self, tmp_path: Path) -> None:
        d = _plugin(tmp_path, "p", manifest={"name": "p"})
        (d / ".claude-plugin" / "commands").mkdir()
        errs = vs.check_component_placement(d)
        assert any("commands/ directory found in .claude-plugin/" in e for e in errs)

    def test_skills_not_a_directory(self, tmp_path: Path) -> None:
        d = _plugin(tmp_path, "p", manifest={"name": "p"})
        (d / "skills").write_text("not a dir")
        assert any("not a directory" in e for e in vs.check_skills_directory(d))

    def test_skills_empty(self, tmp_path: Path) -> None:
        d = _plugin(tmp_path, "p", manifest={"name": "p"})
        (d / "skills").mkdir()
        assert any("no skill subdirectories" in e for e in vs.check_skills_directory(d))

    def test_skill_missing_skill_md(self, tmp_path: Path) -> None:
        d = _plugin(tmp_path, "p", manifest={"name": "p"})
        (d / "skills" / "foo").mkdir(parents=True)
        assert any("Missing required SKILL.md" in e for e in vs.check_skills_directory(d))

    def test_skill_workspace_dir_excluded(self, tmp_path: Path) -> None:
        d = _plugin(tmp_path, "p", manifest={"name": "p"})
        (d / "skills" / "foo").mkdir(parents=True)
        (d / "skills" / "foo" / "SKILL.md").write_text("---\nname: foo\ndescription: x\n---\nbody")
        (d / "skills" / "foo-workspace").mkdir()
        (d / "skills" / "foo-workspace" / "trigger-eval.json").write_text("[]")
        assert vs.check_skills_directory(d) == []

    def test_skill_logs_dir_excluded(self, tmp_path: Path) -> None:
        d = _plugin(tmp_path, "p", manifest={"name": "p"})
        (d / "skills" / "foo").mkdir(parents=True)
        (d / "skills" / "foo" / "SKILL.md").write_text("---\nname: foo\ndescription: x\n---\nbody")
        (d / "skills" / "logs").mkdir()
        assert vs.check_skills_directory(d) == []

    def test_commands_empty(self, tmp_path: Path) -> None:
        d = _plugin(tmp_path, "p", manifest={"name": "p"})
        (d / "commands").mkdir()
        assert any("no .md files" in e for e in vs.check_commands_directory(d))

    def test_command_missing_description(self, tmp_path: Path) -> None:
        d = _plugin(tmp_path, "p", manifest={"name": "p"})
        (d / "commands").mkdir()
        (d / "commands" / "c.md").write_text("---\ntitle: x\n---\nbody")
        assert any("Missing required field 'description'" in e for e in vs.check_commands_directory(d))

    def test_agent_missing_capabilities(self, tmp_path: Path) -> None:
        d = _plugin(tmp_path, "p", manifest={"name": "p"})
        (d / "agents").mkdir()
        (d / "agents" / "a.md").write_text("---\ndescription: x\n---\nbody")
        assert any("capabilities" in e for e in vs.check_agents_directory(d))

    def test_optional_dirs_absent_ok(self, tmp_path: Path) -> None:
        d = _plugin(tmp_path, "p", manifest={"name": "p"})
        assert vs.check_skills_directory(d) == []
        assert vs.check_commands_directory(d) == []
        assert vs.check_agents_directory(d) == []


# --------------------------------------------------------------------------- #
# hooks
# --------------------------------------------------------------------------- #
class TestHooks:
    def test_missing_hooks_key(self, tmp_path: Path) -> None:
        d = _plugin(tmp_path, "p", manifest={"name": "p"})
        errs = vs.check_hooks_configuration(d, {"hooks": {"not_hooks": 1}})
        assert any("missing 'hooks' key" in e for e in errs)

    @pytest.mark.parametrize("event", sorted(_load(SCRIPT).VALID_HOOK_EVENTS))
    def test_valid_events_accepted(self, tmp_path: Path, event: str) -> None:
        d = _plugin(tmp_path, "p", manifest={"name": "p"})
        cfg = {"hooks": {event: []}}
        assert vs.check_hooks_configuration(d, {"hooks": cfg}) == []

    def test_invalid_event(self, tmp_path: Path) -> None:
        d = _plugin(tmp_path, "p", manifest={"name": "p"})
        errs = vs.check_hooks_configuration(d, {"hooks": {"hooks": {"Bogus": []}}})
        assert any("Invalid hook event 'Bogus'" in e for e in errs)

    def test_invalid_hook_type(self, tmp_path: Path) -> None:
        d = _plugin(tmp_path, "p", manifest={"name": "p"})
        cfg = {"hooks": {"PreToolUse": [{"hooks": [{"type": "weird"}]}]}}
        errs = vs.check_hooks_configuration(d, {"hooks": cfg})
        assert any("Invalid hook type 'weird'" in e for e in errs)

    def test_command_script_missing(self, tmp_path: Path) -> None:
        d = _plugin(tmp_path, "p", manifest={"name": "p"})
        cfg = {
            "hooks": {"PreToolUse": [{"hooks": [{"type": "command", "command": "${CLAUDE_PLUGIN_ROOT}/hooks/x.sh"}]}]}
        }
        errs = vs.check_hooks_configuration(d, {"hooks": cfg})
        assert any("Hook command script not found" in e for e in errs)

    def test_command_script_present_ok(self, tmp_path: Path) -> None:
        d = _plugin(tmp_path, "p", manifest={"name": "p"})
        (d / "hooks").mkdir()
        (d / "hooks" / "x.sh").write_text("#!/bin/sh\n")
        cfg = {
            "hooks": {"PreToolUse": [{"hooks": [{"type": "command", "command": "${CLAUDE_PLUGIN_ROOT}/hooks/x.sh"}]}]}
        }
        assert vs.check_hooks_configuration(d, {"hooks": cfg}) == []

    def test_command_quoted_shell_form_ok(self, tmp_path: Path) -> None:
        # Documented shell form: closing quote sits between } and / —
        # e.g. uv run "${CLAUDE_PLUGIN_ROOT}"/hooks/x.py
        d = _plugin(tmp_path, "p", manifest={"name": "p"})
        (d / "hooks").mkdir()
        (d / "hooks" / "x.py").write_text("#!/usr/bin/env python\n")
        cfg = {
            "hooks": {
                "PreToolUse": [
                    {
                        "hooks": [
                            {
                                "type": "command",
                                "command": 'uv run "${CLAUDE_PLUGIN_ROOT}"/hooks/x.py --flag',
                            }
                        ]
                    }
                ]
            }
        }
        assert vs.check_hooks_configuration(d, {"hooks": cfg}) == []


# --------------------------------------------------------------------------- #
# mcp / custom paths
# --------------------------------------------------------------------------- #
class TestMcpAndPaths:
    def test_mcp_missing_key(self, tmp_path: Path) -> None:
        d = _plugin(tmp_path, "p", manifest={"name": "p"})
        errs = vs.check_mcp_servers(d, {"mcpServers": {"nope": 1}})
        assert any("missing 'mcpServers' key" in e for e in errs)

    def test_mcp_server_missing_command(self, tmp_path: Path) -> None:
        d = _plugin(tmp_path, "p", manifest={"name": "p"})
        errs = vs.check_mcp_servers(d, {"mcpServers": {"mcpServers": {"s": {}}}})
        assert any("missing 'command' field" in e for e in errs)

    def test_mcp_absolute_path_warns(self, tmp_path: Path) -> None:
        d = _plugin(tmp_path, "p", manifest={"name": "p"})
        cfg = {"mcpServers": {"mcpServers": {"s": {"command": "/usr/bin/x"}}}}
        errs = vs.check_mcp_servers(d, cfg)
        assert any("absolute path" in e for e in errs)

    def test_custom_command_not_dotslash(self, tmp_path: Path) -> None:
        d = _plugin(tmp_path, "p", manifest={"name": "p"})
        errs = vs.check_custom_component_paths(d, {"commands": "commands/x.md"})
        assert any("must start with './'" in e for e in errs)

    def test_custom_command_not_found(self, tmp_path: Path) -> None:
        d = _plugin(tmp_path, "p", manifest={"name": "p"})
        errs = vs.check_custom_component_paths(d, {"commands": "./missing.md"})
        assert any("not found" in e for e in errs)


# --------------------------------------------------------------------------- #
# check_manifest_conflicts
# --------------------------------------------------------------------------- #
class TestManifestConflicts:
    def test_version_conflict_is_warning(self) -> None:
        w, info = vs.check_manifest_conflicts("p", {"version": "1.0.0"}, {"version": "2.0.0"})
        assert w and not info

    def test_author_conflict_is_info_only(self) -> None:
        w, info = vs.check_manifest_conflicts("p", {"author": {"name": "A"}}, {"author": {"name": "B"}})
        assert info and not w

    def test_keywords_order_insensitive(self) -> None:
        w, _ = vs.check_manifest_conflicts("p", {"keywords": ["a", "b"]}, {"keywords": ["b", "a"]})
        assert w == []

    def test_keywords_real_diff_warns(self) -> None:
        w, _ = vs.check_manifest_conflicts("p", {"keywords": ["a"]}, {"keywords": ["b"]})
        assert w


# --------------------------------------------------------------------------- #
# calculate_exit_code
# --------------------------------------------------------------------------- #
class TestCalculateExitCode:
    @pytest.mark.parametrize(
        ("result", "strict", "expected"),
        [
            ({"marketplace_errors": [], "plugin_results": {}}, False, 0),
            ({"marketplace_errors": ["e"], "plugin_results": {}}, False, 1),
            (
                {"marketplace_errors": [], "plugin_results": {"p": {"skills": ["e"]}}},
                False,
                1,
            ),
            (
                {"marketplace_errors": [], "plugin_results": {"p": {"warnings": ["w"]}}},
                False,
                0,
            ),
            (
                {"marketplace_errors": [], "plugin_results": {"p": {"warnings": ["w"]}}},
                True,
                1,
            ),
            (
                {"marketplace_errors": [], "plugin_results": {"p": {"info_only": ["i"]}}},
                True,
                0,
            ),
        ],
    )
    def test_exit_codes(self, result: dict, strict: bool, expected: int) -> None:
        code, *_ = vs.calculate_exit_code(result, strict=strict)
        assert code == expected

    def test_totals(self) -> None:
        result = {
            "marketplace_errors": ["e"],
            "plugin_results": {"p": {"skills": ["e2"], "warnings": ["w"], "info_only": ["i"]}},
        }
        code, errs, warns, info = vs.calculate_exit_code(result, strict=False)
        assert (code, errs, warns, info) == (1, 2, 1, 1)


# --------------------------------------------------------------------------- #
# check_plugin_manifest
# --------------------------------------------------------------------------- #
class TestCheckPluginManifest:
    def test_require_manifest_missing_errors(self, tmp_path: Path) -> None:
        d = _plugin(tmp_path, "p", manifest=None)
        res = vs.check_plugin_manifest(d, require_manifest=True)
        assert any("Missing .claude-plugin/plugin.json" in e for e in res["manifest"])

    def test_optional_manifest_uses_marketplace_entry(self, tmp_path: Path) -> None:
        d = _plugin(tmp_path, "p", manifest=None)
        res = vs.check_plugin_manifest(d, marketplace_entry={"name": "p"}, require_manifest=False)
        assert not any("Missing .claude-plugin/plugin.json" in e for e in res["manifest"])

    def test_missing_readme(self, tmp_path: Path) -> None:
        d = _plugin(tmp_path, "p", manifest={"name": "p"}, readme=False)
        res = vs.check_plugin_manifest(d, require_manifest=True)
        assert any("Missing README.md" in e for e in res["manifest"])


# --------------------------------------------------------------------------- #
# Integration: check_marketplace_structure + main
# --------------------------------------------------------------------------- #
class TestIntegration:
    def _repo(self, tmp_path: Path, mocker: MockerFixture) -> None:
        mocker.patch.object(vs, "__file__", str(tmp_path / "scripts" / "verify-structure.py"))
        mocker.patch.object(vs, "console", mocker.Mock())

    def _marketplace(self, tmp_path: Path, entries: list[dict]) -> None:
        (tmp_path / ".claude-plugin").mkdir(parents=True)
        (tmp_path / ".claude-plugin" / "marketplace.json").write_text(
            json.dumps({"name": "mp", "owner": {"name": "o"}, "plugins": entries})
        )

    def test_happy_path_exit_0(self, tmp_path: Path, mocker: MockerFixture) -> None:
        self._repo(tmp_path, mocker)
        _plugin(tmp_path, "p", manifest={"name": "p"})
        self._marketplace(tmp_path, [{"name": "p", "source": "./plugins/p"}])
        result = vs.check_marketplace_structure()
        code, *_ = vs.calculate_exit_code(result, strict=False)
        assert code == 0
        mocker.patch.object(vs.sys, "argv", ["verify-structure.py"])
        assert vs.main() == 0

    def test_missing_marketplace_exit_1(self, tmp_path: Path, mocker: MockerFixture) -> None:
        self._repo(tmp_path, mocker)
        result = vs.check_marketplace_structure()
        assert result["marketplace_errors"]
        mocker.patch.object(vs.sys, "argv", ["verify-structure.py"])
        assert vs.main() == 1

    def test_strict_conflict_exit_1(self, tmp_path: Path, mocker: MockerFixture) -> None:
        self._repo(tmp_path, mocker)
        _plugin(tmp_path, "p", manifest={"name": "p", "version": "2.0.0"})
        self._marketplace(tmp_path, [{"name": "p", "source": "./plugins/p", "version": "1.0.0"}])
        mocker.patch.object(vs.sys, "argv", ["verify-structure.py", "--strict"])
        assert vs.main() == 1

    def test_conflict_non_strict_exit_0(self, tmp_path: Path, mocker: MockerFixture) -> None:
        self._repo(tmp_path, mocker)
        _plugin(tmp_path, "p", manifest={"name": "p", "version": "2.0.0"})
        self._marketplace(tmp_path, [{"name": "p", "source": "./plugins/p", "version": "1.0.0"}])
        mocker.patch.object(vs.sys, "argv", ["verify-structure.py"])
        assert vs.main() == 0
