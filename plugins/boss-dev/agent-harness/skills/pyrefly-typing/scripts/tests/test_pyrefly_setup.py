"""Tests for pyrefly_setup.py — pure detect/build/merge helpers."""

from __future__ import annotations

from pyrefly_setup import (
    append_pyproject_section,
    build_justfile_block,
    build_makefile_block,
    build_pyrefly_toml_block,
    build_stop_hook_entry,
    detect_existing_type_checkers,
    detect_legacy_type_checker,
    detect_python_version,
    detect_task_runner,
    has_pyrefly_dependency,
    justfile_has_pyrefly_targets,
    makefile_has_pyrefly_targets,
    merge_npm_scripts,
    merge_stop_hook,
    pyproject_has_pyrefly_section,
)


class TestDetectProjectIncludesAndVersion:
    def test_python_version_prefers_dotfile(self) -> None:
        assert detect_python_version("3.12\n", ">=3.11") == "3.12"

    def test_python_version_falls_back_to_requires_python_floor(self) -> None:
        assert detect_python_version(None, ">=3.12") == "3.12"

    def test_python_version_none_when_nothing_present(self) -> None:
        assert detect_python_version(None, None) is None

    def test_python_version_ignores_blank_dotfile(self) -> None:
        assert detect_python_version("   \n", ">=3.13") == "3.13"


class TestDetectExistingTypeCheckers:
    def test_detects_ty_and_basedpyright(self) -> None:
        data = {"tool": {"ty": {"environment": {}}, "basedpyright": {}}}
        assert detect_existing_type_checkers(data) == ["ty", "basedpyright"]

    def test_none_present(self) -> None:
        assert detect_existing_type_checkers({"tool": {"ruff": {}}}) == []

    def test_no_tool_table(self) -> None:
        assert detect_existing_type_checkers({}) == []


class TestDetectLegacyTypeChecker:
    def test_mypy_ini_detected(self) -> None:
        assert detect_legacy_type_checker({}, {"mypy.ini"}) == "mypy"

    def test_tool_mypy_detected(self) -> None:
        assert detect_legacy_type_checker({"tool": {"mypy": {}}}, set()) == "mypy"

    def test_pyrightconfig_detected(self) -> None:
        assert detect_legacy_type_checker({}, {"pyrightconfig.json"}) == "pyright"

    def test_mypy_takes_precedence_over_pyright(self) -> None:
        data = {"tool": {"mypy": {}, "pyright": {}}}
        assert detect_legacy_type_checker(data, set()) == "mypy"

    def test_none_when_no_legacy_config(self) -> None:
        assert detect_legacy_type_checker({"tool": {"ty": {}}}, {"README.md"}) is None

    def test_basedpyright_alone_is_not_legacy(self) -> None:
        assert detect_legacy_type_checker({"tool": {"basedpyright": {}}}, set()) is None


class TestDetectTaskRunner:
    def test_justfile(self) -> None:
        assert detect_task_runner({"justfile", "pyproject.toml"}) == "just"

    def test_capital_justfile(self) -> None:
        assert detect_task_runner({"Justfile"}) == "just"

    def test_makefile(self) -> None:
        assert detect_task_runner({"Makefile"}) == "make"

    def test_package_json(self) -> None:
        assert detect_task_runner({"package.json"}) == "npm"

    def test_justfile_takes_precedence_over_makefile(self) -> None:
        assert detect_task_runner({"justfile", "Makefile"}) == "just"

    def test_none_detected(self) -> None:
        assert detect_task_runner({"README.md"}) is None


class TestHasPyreflyDependency:
    def test_present_in_dependency_groups(self) -> None:
        data = {"dependency-groups": {"dev": ["pyrefly>=0.1.0", "pytest"]}}
        assert has_pyrefly_dependency(data) is True

    def test_present_in_legacy_uv_dev_dependencies(self) -> None:
        data = {"tool": {"uv": {"dev-dependencies": ["pyrefly"]}}}
        assert has_pyrefly_dependency(data) is True

    def test_absent(self) -> None:
        data = {"dependency-groups": {"dev": ["pytest", "ruff"]}}
        assert has_pyrefly_dependency(data) is False

    def test_empty_pyproject(self) -> None:
        assert has_pyrefly_dependency({}) is False


class TestPyprojectHasPyreflySection:
    def test_present(self) -> None:
        assert pyproject_has_pyrefly_section("[tool.pyrefly]\nproject-includes = []\n") is True

    def test_absent(self) -> None:
        assert pyproject_has_pyrefly_section("[tool.basedpyright]\n") is False


class TestBuildPyreflyTomlBlock:
    def test_renders_kebab_case_keys(self) -> None:
        block = build_pyrefly_toml_block(["src", "tests"], "3.12")
        assert "[tool.pyrefly]" in block
        assert 'project-includes = ["src", "tests"]' in block
        assert 'python-version = "3.12"' in block


class TestAppendPyprojectSection:
    def test_adds_blank_line_separator(self) -> None:
        original = "[project]\nname = 'x'\n"
        block = "[tool.pyrefly]\npython-version = '3.12'\n"
        merged = append_pyproject_section(original, block)
        assert merged == "[project]\nname = 'x'\n\n[tool.pyrefly]\npython-version = '3.12'\n"

    def test_handles_missing_trailing_newline(self) -> None:
        merged = append_pyproject_section("[project]\nname = 'x'", "[tool.pyrefly]\n")
        assert merged.startswith("[project]\nname = 'x'\n\n[tool.pyrefly]\n")

    def test_empty_original(self) -> None:
        assert append_pyproject_section("", "[tool.pyrefly]\n") == "[tool.pyrefly]\n"


class TestJustfileBlock:
    def test_marker_detection(self) -> None:
        assert justfile_has_pyrefly_targets("check-pyrefly:\n    uv run pyrefly check\n") is True
        assert justfile_has_pyrefly_targets("lint:\n    ruff check .\n") is False

    def test_build_includes_all_three_targets(self) -> None:
        block = build_justfile_block(["src", "tests"])
        assert "check-pyrefly:" in block
        assert "pyrefly-baseline:" in block
        assert "pyrefly-coverage:" in block
        assert "uv run pyrefly coverage report src tests" in block

    def test_never_touches_lint_or_check_targets(self) -> None:
        block = build_justfile_block(["src"])
        assert "\nlint:" not in block
        assert "\ncheck:" not in block


class TestMakefileBlock:
    def test_marker_detection(self) -> None:
        assert makefile_has_pyrefly_targets("check-pyrefly:\n\tuv run pyrefly check\n") is True

    def test_build_uses_tabs_for_recipes(self) -> None:
        block = build_makefile_block(["src", "tests"])
        assert "\tuv run pyrefly check --baseline pyrefly-baseline.json --summarize-errors\n" in block
        assert ".PHONY: check-pyrefly pyrefly-baseline pyrefly-coverage" in block


class TestMergeNpmScripts:
    def test_adds_missing_scripts(self) -> None:
        merged, added = merge_npm_scripts({}, ["src", "tests"])
        assert set(added) == {"check-pyrefly", "pyrefly-baseline", "pyrefly-coverage"}
        assert "src tests" in merged["scripts"]["pyrefly-coverage"]

    def test_idempotent_when_already_present(self) -> None:
        first, _ = merge_npm_scripts({}, ["src"])
        _, added = merge_npm_scripts(first, ["src"])
        assert added == []

    def test_preserves_existing_scripts(self) -> None:
        data = {"scripts": {"build": "tsc"}}
        merged, _ = merge_npm_scripts(data, ["src"])
        assert merged["scripts"]["build"] == "tsc"


class TestStopHook:
    def test_build_entry_shape(self) -> None:
        entry = build_stop_hook_entry()
        assert entry["hooks"][0]["type"] == "command"
        assert "pyrefly check" in entry["hooks"][0]["command"]
        assert entry["hooks"][0]["timeout"] == 30

    def test_merge_appends_to_empty_settings(self) -> None:
        merged, changed = merge_stop_hook({}, build_stop_hook_entry())
        assert changed is True
        assert len(merged["hooks"]["Stop"]) == 1

    def test_merge_is_additive_not_replacing(self) -> None:
        existing = {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "echo hi", "timeout": 5}]}]}}
        merged, changed = merge_stop_hook(existing, build_stop_hook_entry())
        assert changed is True
        commands = [h["command"] for group in merged["hooks"]["Stop"] for h in group["hooks"]]
        assert "echo hi" in commands
        assert any("pyrefly check" in c for c in commands)

    def test_merge_is_idempotent(self) -> None:
        entry = build_stop_hook_entry()
        once, _ = merge_stop_hook({}, entry)
        twice, changed = merge_stop_hook(once, entry)
        assert changed is False
        assert len(twice["hooks"]["Stop"]) == 1
