"""Unit tests for ``scripts/skill_validation.py``.

Loaded by path via importlib for consistency with the other script suites
(the file has an ``if __name__ == "__main__"`` guard, so import is safe).
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "skill_validation.py"


def _load(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(path.stem.replace("-", "_"), path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # @dataclasses.dataclass needs the module in sys.modules during class creation.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


sv = _load(SCRIPT)
Level = sv.Level


def _rules(results: list) -> set[str]:
    return {r.rule for r in results}


def _skill_path(tmp_path: Path, name: str) -> Path:
    """Return tmp_path/<name>/SKILL.md so check_name's dir match is satisfiable."""
    d = tmp_path / name
    d.mkdir(parents=True, exist_ok=True)
    return d / "SKILL.md"


# --------------------------------------------------------------------------- #
# parse_frontmatter
# --------------------------------------------------------------------------- #
class TestParseFrontmatter:
    def test_missing_opening(self) -> None:
        fm, body, err = sv.parse_frontmatter("no frontmatter here")
        assert fm is None
        assert body == "no frontmatter here"
        assert err is not None and "missing opening" in err

    def test_missing_closing(self) -> None:
        fm, _, err = sv.parse_frontmatter("---\nname: x\n")
        assert fm is None
        assert err == "no closing --- for frontmatter"

    def test_invalid_yaml(self) -> None:
        fm, _, err = sv.parse_frontmatter("---\nfoo: [unclosed\n---\nbody")
        assert fm is None
        assert err is not None and err.startswith("YAML parse error:")

    def test_non_mapping(self) -> None:
        fm, _, err = sv.parse_frontmatter("---\n- a\n- b\n---\nbody")
        assert fm is None
        assert err == "frontmatter is not a YAML mapping"

    def test_valid(self) -> None:
        fm, body, err = sv.parse_frontmatter("---\nname: foo\n---\nthe body")
        assert fm == {"name": "foo"}
        assert body == "the body"
        assert err is None

    def test_empty_block_is_non_mapping(self) -> None:
        fm, _, err = sv.parse_frontmatter("---\n---\nbody")
        assert fm is None
        assert err == "frontmatter is not a YAML mapping"


# --------------------------------------------------------------------------- #
# check_frontmatter_valid (rule 16)
# --------------------------------------------------------------------------- #
class TestFrontmatterValid:
    def test_none_reports_error_with_message(self, tmp_path: Path) -> None:
        r = sv.check_frontmatter_valid(tmp_path / "SKILL.md", None, "", [], "boom")
        assert r[0].rule == "frontmatter-valid"
        assert r[0].level is Level.ERROR
        assert r[0].message == "boom"

    def test_valid_fm_no_results(self, tmp_path: Path) -> None:
        assert sv.check_frontmatter_valid(tmp_path / "SKILL.md", {"a": 1}, "", [], None) == []


# --------------------------------------------------------------------------- #
# check_name (rules 1-3)
# --------------------------------------------------------------------------- #
class TestCheckName:
    def test_fm_none_skips(self, tmp_path: Path) -> None:
        assert sv.check_name(tmp_path / "SKILL.md", None, "", []) == []

    def test_missing_name(self, tmp_path: Path) -> None:
        p = _skill_path(tmp_path, "foo")
        assert _rules(sv.check_name(p, {}, "", [])) == {"name-exists"}

    def test_valid_name_matches_dir(self, tmp_path: Path) -> None:
        p = _skill_path(tmp_path, "good-skill")
        assert sv.check_name(p, {"name": "good-skill"}, "", []) == []

    @pytest.mark.parametrize("bad", ["BadName", "-lead", "trail-", "under_score", ""])
    def test_invalid_format(self, tmp_path: Path, bad: str) -> None:
        p = _skill_path(tmp_path, bad or "empty")
        assert "name-format" in _rules(sv.check_name(p, {"name": bad}, "", []))

    def test_too_long(self, tmp_path: Path) -> None:
        long = "a" * 65
        p = _skill_path(tmp_path, long)
        assert "name-length" in _rules(sv.check_name(p, {"name": long}, "", []))

    def test_name_dir_mismatch(self, tmp_path: Path) -> None:
        p = _skill_path(tmp_path, "dirname")
        assert "name-matches-dir" in _rules(sv.check_name(p, {"name": "other"}, "", []))


# --------------------------------------------------------------------------- #
# check_description (rules 4-6)
# --------------------------------------------------------------------------- #
class TestCheckDescription:
    def test_missing(self, tmp_path: Path) -> None:
        assert _rules(sv.check_description(tmp_path, {}, "", [])) == {"desc-exists"}

    def test_too_long(self, tmp_path: Path) -> None:
        fm = {"description": "x" * 1025 + " use when y"}
        assert "desc-length" in _rules(sv.check_description(tmp_path, fm, "", []))

    @pytest.mark.parametrize(
        "kw", ["use when", "trigger when", "invoke when", "use this", "use for", "use to"]
    )
    def test_trigger_keyword_present(self, tmp_path: Path, kw: str) -> None:
        fm = {"description": f"Does things. {kw} the user wants."}
        assert "desc-trigger" not in _rules(sv.check_description(tmp_path, fm, "", []))

    def test_trigger_case_insensitive(self, tmp_path: Path) -> None:
        fm = {"description": "Helper. USE WHEN editing files."}
        assert "desc-trigger" not in _rules(sv.check_description(tmp_path, fm, "", []))

    def test_missing_trigger_warns(self, tmp_path: Path) -> None:
        fm = {"description": "A helper that formats things."}
        r = sv.check_description(tmp_path, fm, "", [])
        assert any(x.rule == "desc-trigger" and x.level is Level.WARNING for x in r)


# --------------------------------------------------------------------------- #
# check_optional_fields (rules 7-8)
# --------------------------------------------------------------------------- #
class TestOptionalFields:
    def test_no_optional_fields_ok(self, tmp_path: Path) -> None:
        assert sv.check_optional_fields(tmp_path, {"name": "x"}, "", []) == []

    def test_known_and_mcp_tools_ok(self, tmp_path: Path) -> None:
        fm = {"allowed-tools": "Bash, Read , mcp__custom_thing"}
        assert sv.check_optional_fields(tmp_path, fm, "", []) == []

    def test_unknown_tool_warns(self, tmp_path: Path) -> None:
        r = sv.check_optional_fields(tmp_path, {"allowed-tools": "Bash,Nope"}, "", [])
        assert any(x.rule == "allowed-tools" and "Nope" in x.message for x in r)

    @pytest.mark.parametrize("model", ["sonnet", "opus", "haiku"])
    def test_valid_model(self, tmp_path: Path, model: str) -> None:
        assert sv.check_optional_fields(tmp_path, {"model": model}, "", []) == []

    def test_invalid_model_warns(self, tmp_path: Path) -> None:
        assert "model-valid" in _rules(
            sv.check_optional_fields(tmp_path, {"model": "gpt4"}, "", [])
        )


# --------------------------------------------------------------------------- #
# check_description_quality (rule 9)
# --------------------------------------------------------------------------- #
class TestDescriptionQuality:
    def test_vague_without_specifics_warns(self, tmp_path: Path) -> None:
        assert "desc-vague" in _rules(
            sv.check_description_quality(tmp_path, {"description": "Use when needed"}, "", [])
        )

    def test_vague_with_specifics_ok(self, tmp_path: Path) -> None:
        fm = {"description": "Use as appropriate to convert PNG screenshots to reels"}
        assert sv.check_description_quality(tmp_path, fm, "", []) == []

    def test_no_description_skips(self, tmp_path: Path) -> None:
        assert sv.check_description_quality(tmp_path, {}, "", []) == []


# --------------------------------------------------------------------------- #
# check_structure (rules 10-11)
# --------------------------------------------------------------------------- #
class TestCheckStructure:
    def test_under_limit_ok(self, tmp_path: Path) -> None:
        p = _skill_path(tmp_path, "s")
        assert sv.check_structure(p, None, "", ["l"] * 500) == []

    def test_over_limit_no_subdirs(self, tmp_path: Path) -> None:
        p = _skill_path(tmp_path, "s")
        assert _rules(sv.check_structure(p, None, "", ["l"] * 501)) == {
            "line-count",
            "progressive-disclosure",
        }

    def test_over_limit_with_scripts_dir(self, tmp_path: Path) -> None:
        p = _skill_path(tmp_path, "s")
        (tmp_path / "s" / "scripts").mkdir()
        rules = _rules(sv.check_structure(p, None, "", ["l"] * 501))
        assert rules == {"line-count"}


# --------------------------------------------------------------------------- #
# check_directory_conventions (rule 12)
# --------------------------------------------------------------------------- #
class TestDirectoryConventions:
    def test_all_missing_three_infos(self, tmp_path: Path) -> None:
        p = _skill_path(tmp_path, "s")
        r = sv.check_directory_conventions(p, None, "", [])
        assert len(r) == 3
        assert all(x.level is Level.INFO and x.rule == "dir-conventions" for x in r)

    def test_all_present_no_info(self, tmp_path: Path) -> None:
        p = _skill_path(tmp_path, "s")
        for d in ("scripts", "references", "assets"):
            (tmp_path / "s" / d).mkdir()
        assert sv.check_directory_conventions(p, None, "", []) == []


# --------------------------------------------------------------------------- #
# check_body_content (rules 13-14)
# --------------------------------------------------------------------------- #
class TestBodyContent:
    def test_numbered_list_satisfies_instructions(self, tmp_path: Path) -> None:
        body = "1. do this\n2. then that\n\n```\ncode\n```"
        assert sv.check_body_content(tmp_path, None, body, []) == []

    def test_headers_satisfy_instructions(self, tmp_path: Path) -> None:
        body = "## Section\n\nText\n\n```\ncode\n```"
        assert sv.check_body_content(tmp_path, None, body, []) == []

    def test_missing_instructions_and_examples(self, tmp_path: Path) -> None:
        assert _rules(sv.check_body_content(tmp_path, None, "just prose", [])) == {
            "body-instructions",
            "body-examples",
        }


# --------------------------------------------------------------------------- #
# check_backtick_bang (rule 15, parser bug #12781)
# --------------------------------------------------------------------------- #
class TestBacktickBang:
    def test_inside_fence_errors(self, tmp_path: Path) -> None:
        body = "```\n`!ls -la`\n```"
        r = sv.check_backtick_bang(tmp_path, None, body, [])
        assert r[0].rule == "backtick-bang"
        assert r[0].level is Level.ERROR

    def test_outside_fence_ok(self, tmp_path: Path) -> None:
        assert sv.check_backtick_bang(tmp_path, None, "inline `!nope` text", []) == []

    def test_breaks_on_first_match(self, tmp_path: Path) -> None:
        body = "```\n`!one`\n`!two`\n```"
        assert len(sv.check_backtick_bang(tmp_path, None, body, [])) == 1

    def test_unclosed_fence_still_detected(self, tmp_path: Path) -> None:
        body = "```\nsafe\n`!danger`"
        assert _rules(sv.check_backtick_bang(tmp_path, None, body, [])) == {"backtick-bang"}


# --------------------------------------------------------------------------- #
# validate_skill_file / find_skill_files
# --------------------------------------------------------------------------- #
class TestOrchestration:
    def test_clean_skill_has_no_results(self, tmp_path: Path) -> None:
        p = _skill_path(tmp_path, "clean-skill")
        for d in ("scripts", "references", "assets"):
            (tmp_path / "clean-skill" / d).mkdir()
        p.write_text(
            "---\n"
            "name: clean-skill\n"
            "description: A tool. Use when the user wants a clean validated skill.\n"
            "---\n"
            "## Steps\n\n1. Do the thing\n\n```bash\necho hi\n```\n"
        )
        report = sv.validate_skill_file(p)
        assert report.results == []
        assert report.errors == []

    def test_aggregates_errors(self, tmp_path: Path) -> None:
        p = _skill_path(tmp_path, "dir-x")
        p.write_text("---\nname: mismatch\n---\nbody\n")
        report = sv.validate_skill_file(p)
        assert "name-matches-dir" in _rules(report.results)
        assert report.errors

    def test_find_skill_files_sorted(self, tmp_path: Path) -> None:
        (tmp_path / "b").mkdir()
        (tmp_path / "a").mkdir()
        (tmp_path / "b" / "SKILL.md").write_text("x")
        (tmp_path / "a" / "SKILL.md").write_text("x")
        assert sv.find_skill_files(tmp_path) == [
            tmp_path / "a" / "SKILL.md",
            tmp_path / "b" / "SKILL.md",
        ]

    def test_find_skill_files_none(self, tmp_path: Path) -> None:
        assert sv.find_skill_files(tmp_path) == []


# --------------------------------------------------------------------------- #
# print_summary exit-code logic
# --------------------------------------------------------------------------- #
class TestPrintSummary:
    def _report(self, tmp_path: Path, *levels: object) -> object:
        rep = sv.FileReport(path=tmp_path / "SKILL.md")
        for lvl in levels:
            rep.results.append(sv.CheckResult("r", lvl, "m"))
        return rep

    def test_errors_fail(self, tmp_path: Path, mocker: MockerFixture) -> None:
        mocker.patch.object(sv, "console")
        assert sv.print_summary([self._report(tmp_path, Level.ERROR)], strict=False) == 1

    def test_warnings_strict_fail(self, tmp_path: Path, mocker: MockerFixture) -> None:
        mocker.patch.object(sv, "console")
        assert sv.print_summary([self._report(tmp_path, Level.WARNING)], strict=True) == 1

    def test_warnings_non_strict_pass(self, tmp_path: Path, mocker: MockerFixture) -> None:
        mocker.patch.object(sv, "console")
        assert sv.print_summary([self._report(tmp_path, Level.WARNING)], strict=False) == 0

    def test_clean_pass(self, tmp_path: Path, mocker: MockerFixture) -> None:
        mocker.patch.object(sv, "console")
        assert sv.print_summary([self._report(tmp_path)], strict=True) == 0


# --------------------------------------------------------------------------- #
# main() integration
# --------------------------------------------------------------------------- #
class TestMain:
    def _argv(self, mocker: MockerFixture, *args: str) -> None:
        mocker.patch.object(sv.sys, "argv", ["skill_validation.py", *args])
        mocker.patch.object(sv, "console")

    def _write(self, tmp_path: Path, name: str, body_extra: str = "") -> Path:
        d = tmp_path / name
        for sub in ("scripts", "references", "assets"):
            (d / sub).mkdir(parents=True)
        p = d / "SKILL.md"
        p.write_text(
            f"---\nname: {name}\n"
            f"description: Tool. Use when the user needs {name} validated thoroughly.\n"
            f"---\n## Steps\n\n1. step\n\n```bash\necho hi\n```\n{body_extra}"
        )
        return p

    def test_valid_returns_0(self, tmp_path: Path, mocker: MockerFixture) -> None:
        self._write(tmp_path, "valid-skill")
        self._argv(mocker, str(tmp_path))
        assert sv.main() == 0

    def test_errors_return_1(self, tmp_path: Path, mocker: MockerFixture) -> None:
        d = tmp_path / "dirname"
        d.mkdir()
        (d / "SKILL.md").write_text("---\nname: wrongname\n---\nbody\n")
        self._argv(mocker, str(tmp_path))
        assert sv.main() == 1

    def test_warnings_strict_returns_1(self, tmp_path: Path, mocker: MockerFixture) -> None:
        d = tmp_path / "warnskill"
        d.mkdir()
        # Missing trigger keyword + no code block => warnings, no errors.
        (d / "SKILL.md").write_text(
            "---\nname: warnskill\ndescription: plain description text\n---\n## H\n\ntext\n"
        )
        self._argv(mocker, str(tmp_path), "--strict")
        assert sv.main() == 1

    def test_warnings_non_strict_returns_0(self, tmp_path: Path, mocker: MockerFixture) -> None:
        d = tmp_path / "warnskill"
        d.mkdir()
        (d / "SKILL.md").write_text(
            "---\nname: warnskill\ndescription: plain description text\n---\n## H\n\ntext\n"
        )
        self._argv(mocker, str(tmp_path))
        assert sv.main() == 0

    def test_no_skill_files_returns_0(self, tmp_path: Path, mocker: MockerFixture) -> None:
        self._argv(mocker, str(tmp_path))
        assert sv.main() == 0

    def test_missing_directory_returns_1(self, tmp_path: Path, mocker: MockerFixture) -> None:
        self._argv(mocker, str(tmp_path / "does-not-exist"))
        assert sv.main() == 1

    def test_rules_report_passing_fixture_keeps_exit_0(self, tmp_path: Path, mocker: MockerFixture) -> None:
        self._write(tmp_path, "valid-skill")
        self._argv(mocker, str(tmp_path))
        assert sv.main() == 0
        self._argv(mocker, str(tmp_path), "--rules-report")
        assert sv.main() == 0

    def test_rules_report_failing_fixture_keeps_exit_1(self, tmp_path: Path, mocker: MockerFixture) -> None:
        d = tmp_path / "dirname"
        d.mkdir()
        (d / "SKILL.md").write_text("---\nname: wrongname\n---\nbody\n")
        self._argv(mocker, str(tmp_path))
        assert sv.main() == 1
        self._argv(mocker, str(tmp_path), "--rules-report")
        assert sv.main() == 1

    def test_rules_report_with_strict_returns_1(self, tmp_path: Path, mocker: MockerFixture) -> None:
        d = tmp_path / "warnskill"
        d.mkdir()
        # Missing trigger keyword + no code block => warnings, no errors.
        (d / "SKILL.md").write_text(
            "---\nname: warnskill\ndescription: plain description text\n---\n## H\n\ntext\n"
        )
        self._argv(mocker, str(tmp_path), "--rules-report", "--strict")
        assert sv.main() == 1


# --------------------------------------------------------------------------- #
# RULE_REGISTRY (rules report flag)
# --------------------------------------------------------------------------- #
class TestRuleRegistry:
    def test_registry_non_empty_rulespecs(self) -> None:
        assert sv.RULE_REGISTRY
        assert all(isinstance(s, sv.RuleSpec) for s in sv.RULE_REGISTRY)

    def test_rule_ids_unique(self) -> None:
        ids = [s.rule_id for s in sv.RULE_REGISTRY]
        assert len(ids) == len(set(ids))

    def test_every_level_is_a_level(self) -> None:
        assert all(isinstance(s.level, Level) for s in sv.RULE_REGISTRY)

    def test_registry_matches_emitted_rules(self) -> None:
        """Drift guard: RULE_REGISTRY must list exactly the rule IDs that the
        check_* functions emit as ``CheckResult`` literals."""
        source = SCRIPT.read_text(encoding="utf-8")
        emitted = set(re.findall(r"""CheckResult\(\s*["']([a-z0-9-]+)["']""", source))
        registered = {s.rule_id for s in sv.RULE_REGISTRY}
        assert emitted == registered


# --------------------------------------------------------------------------- #
# build_file_rules_report (per-file rules report)
# --------------------------------------------------------------------------- #
class TestBuildFileRulesReport:
    def test_clean_file_all_rows_ok(self, tmp_path: Path) -> None:
        rows = sv.build_file_rules_report(sv.FileReport(path=tmp_path / "SKILL.md"))
        assert len(rows) == len(sv.RULE_REGISTRY)
        assert all(row.fired is False for row in rows)
        assert all(row.findings == [] for row in rows)

    def test_row_order_matches_registry(self, tmp_path: Path) -> None:
        rows = sv.build_file_rules_report(sv.FileReport(path=tmp_path / "SKILL.md"))
        assert [row.spec.rule_id for row in rows] == [s.rule_id for s in sv.RULE_REGISTRY]

    def test_finding_marks_only_its_rule_fired(self, tmp_path: Path) -> None:
        report = sv.FileReport(path=tmp_path / "SKILL.md")
        report.results.append(sv.CheckResult("name-matches-dir", Level.ERROR, "mismatch"))
        rows = sv.build_file_rules_report(report)
        fired = [row for row in rows if row.fired]
        assert len(fired) == 1
        assert fired[0].spec.rule_id == "name-matches-dir"
        assert fired[0].findings[0].message == "mismatch"

    def test_multiple_findings_for_one_rule_collected(self, tmp_path: Path) -> None:
        report = sv.FileReport(path=tmp_path / "SKILL.md")
        report.results.append(sv.CheckResult("dir-conventions", Level.INFO, "no scripts/"))
        report.results.append(sv.CheckResult("dir-conventions", Level.INFO, "no assets/"))
        rows = {row.spec.rule_id: row for row in sv.build_file_rules_report(report)}
        assert len(rows["dir-conventions"].findings) == 2


# --------------------------------------------------------------------------- #
# build_rules_report (aggregate rules report)
# --------------------------------------------------------------------------- #
class TestBuildRulesReport:
    def _report(self, path: Path, *findings: tuple[str, object]) -> object:
        rep = sv.FileReport(path=path)
        for rule, level in findings:
            rep.results.append(sv.CheckResult(rule, level, "m"))
        return rep

    def test_empty_reports_all_ok(self) -> None:
        outcomes = sv.build_rules_report([])
        assert len(outcomes) == len(sv.RULE_REGISTRY)
        assert all(o.ok for o in outcomes)
        assert all(o.passing_files == [] and o.failing_files == [] for o in outcomes)

    def test_one_failing_one_clean(self, tmp_path: Path) -> None:
        failing = self._report(tmp_path / "bad" / "SKILL.md", ("name-exists", Level.ERROR))
        clean = self._report(tmp_path / "good" / "SKILL.md")
        outcomes = {o.spec.rule_id: o for o in sv.build_rules_report([failing, clean])}
        ne = outcomes["name-exists"]
        assert ne.failing_files == [tmp_path / "bad" / "SKILL.md"]
        assert ne.passing_files == [tmp_path / "good" / "SKILL.md"]
        assert ne.ok is False
        # An untouched rule passes for both files.
        assert outcomes["body-examples"].ok is True
        assert len(outcomes["body-examples"].passing_files) == 2

    def test_mixed_counts(self, tmp_path: Path) -> None:
        reports = [
            self._report(tmp_path / f"s{i}" / "SKILL.md", ("desc-trigger", Level.WARNING))
            for i in range(3)
        ]
        reports += [self._report(tmp_path / f"c{i}" / "SKILL.md") for i in range(2)]
        outcomes = {o.spec.rule_id: o for o in sv.build_rules_report(reports)}
        assert len(outcomes["desc-trigger"].failing_files) == 3
        assert len(outcomes["desc-trigger"].passing_files) == 2

    def test_info_rule_fired_is_not_ok(self, tmp_path: Path) -> None:
        rep = self._report(tmp_path / "s" / "SKILL.md", ("dir-conventions", Level.INFO))
        outcomes = {o.spec.rule_id: o for o in sv.build_rules_report([rep])}
        dc = outcomes["dir-conventions"]
        assert dc.ok is False
        assert sv.rule_status(dc.spec, fired=True) == "INFO"


# --------------------------------------------------------------------------- #
# rule_status / print_file_rules_report / print_rules_report
# --------------------------------------------------------------------------- #
class TestRulesReportDisplay:
    @pytest.mark.parametrize(
        ("level", "fired", "expected"),
        [
            (Level.ERROR, False, "OK"),
            (Level.WARNING, False, "OK"),
            (Level.INFO, False, "OK"),
            (Level.ERROR, True, "NOT OK"),
            (Level.WARNING, True, "NOT OK"),
            (Level.INFO, True, "INFO"),
        ],
    )
    def test_rule_status(self, level: object, fired: bool, expected: str) -> None:
        spec = sv.RuleSpec("x", "x", level)
        assert sv.rule_status(spec, fired=fired) == expected

    def test_print_file_rules_report_clean(self, tmp_path: Path, mocker: MockerFixture) -> None:
        mocker.patch.object(sv, "console")
        report = sv.FileReport(path=tmp_path / "skill" / "SKILL.md")
        sv.print_file_rules_report(report, sv.build_file_rules_report(report))
        sv.console.print.assert_called()

    def test_print_file_rules_report_with_findings(self, tmp_path: Path, mocker: MockerFixture) -> None:
        mocker.patch.object(sv, "console")
        report = sv.FileReport(path=tmp_path / "skill" / "SKILL.md")
        report.results.append(sv.CheckResult("name-exists", Level.ERROR, "missing [name]"))
        sv.print_file_rules_report(report, sv.build_file_rules_report(report))
        sv.console.print.assert_called()

    def test_print_rules_report_empty(self, mocker: MockerFixture) -> None:
        mocker.patch.object(sv, "console")
        sv.print_rules_report(sv.build_rules_report([]))
        sv.console.print.assert_called()

    def test_print_rules_report_mixed(self, tmp_path: Path, mocker: MockerFixture) -> None:
        mocker.patch.object(sv, "console")
        bad = sv.FileReport(path=tmp_path / "bad" / "SKILL.md")
        bad.results.append(sv.CheckResult("name-exists", Level.ERROR, "missing"))
        bad.results.append(sv.CheckResult("dir-conventions", Level.INFO, "no assets/"))
        good = sv.FileReport(path=tmp_path / "good" / "SKILL.md")
        sv.print_rules_report(sv.build_rules_report([bad, good]))
        sv.console.print.assert_called()
