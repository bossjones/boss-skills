"""Unit tests for ``scripts/eval-skills.py``.

The script is a hyphenated PEP 723 file (not an importable module), so it is
loaded by path via importlib, mirroring
``tests/test_version_bump_reviewer_hook.py``. Every ``subprocess.run`` is
mocked — the suite does no network I/O and runs in milliseconds.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "eval-skills.py"


def _load(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(path.stem.replace("-", "_"), path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


es = _load(SCRIPT)


def _proc(mocker: MockerFixture, returncode: int = 0, stdout: str = "", stderr: str = ""):
    return mocker.Mock(returncode=returncode, stdout=stdout, stderr=stderr)


def _ns(**kw: object) -> argparse.Namespace:
    """Namespace with the full attribute set the run_* handlers read."""
    base: dict[str, object] = {
        "command": "score",
        "layer": "static",
        "threshold": None,
        "skill": None,
        "corpus_dir": None,
        "targets": [],
    }
    base.update(kw)
    return argparse.Namespace(**base)


# --------------------------------------------------------------------------- #
# resolve_source / LAYER_TO_DEPTH
# --------------------------------------------------------------------------- #
GIT = "git+https://github.com/wshobson/agents.git#subdirectory=plugins/plugin-eval"


class TestResolveSource:
    def test_no_llm_returns_unchanged(self) -> None:
        assert es.resolve_source(GIT, False) == GIT

    def test_llm_wraps_bare_git_url(self) -> None:
        assert es.resolve_source(GIT, True) == f"plugin-eval[llm] @ {GIT}"

    def test_llm_does_not_double_wrap_existing_spec(self) -> None:
        spec = f"plugin-eval[llm] @ {GIT}"
        assert es.resolve_source(spec, True) == spec

    def test_llm_passes_through_any_plugin_eval_prefixed_spec(self) -> None:
        assert es.resolve_source("plugin-eval @ /local/path", True) == "plugin-eval @ /local/path"


class TestLayerToDepth:
    @pytest.mark.parametrize(
        ("layer", "depth"),
        [
            ("static", "quick"),
            ("static-analysis", "quick"),
            ("llm-judge", "standard"),
            ("monte-carlo", "deep"),
            ("all", "thorough"),
        ],
    )
    def test_mapping(self, layer: str, depth: str) -> None:
        assert es.LAYER_TO_DEPTH[layer] == depth


# --------------------------------------------------------------------------- #
# SkillResult.rel
# --------------------------------------------------------------------------- #
class TestSkillResultRel:
    def test_relative_when_under_repo_root(self, mocker: MockerFixture, tmp_path: Path) -> None:
        mocker.patch.object(es, "REPO_ROOT", tmp_path)
        r = es.SkillResult(tmp_path / "plugins" / "foo", 80.0, "gold", 0, None)
        assert r.rel == "plugins/foo"

    def test_absolute_when_outside_repo_root(self, mocker: MockerFixture, tmp_path: Path) -> None:
        mocker.patch.object(es, "REPO_ROOT", tmp_path / "repo")
        outside = tmp_path / "elsewhere" / "bar"
        r = es.SkillResult(outside, None, "-", 0, None)
        assert r.rel == str(outside)


# --------------------------------------------------------------------------- #
# discover_skills
# --------------------------------------------------------------------------- #
class TestDiscoverSkills:
    def test_empty_when_no_skill_md(self, mocker: MockerFixture, tmp_path: Path) -> None:
        mocker.patch.object(es, "PLUGINS_DIR", tmp_path)
        assert es.discover_skills() == []

    def test_dedupes_parent_and_sorts(self, mocker: MockerFixture, tmp_path: Path) -> None:
        mocker.patch.object(es, "PLUGINS_DIR", tmp_path)
        (tmp_path / "b" / "skills" / "two").mkdir(parents=True)
        (tmp_path / "a" / "skills" / "one").mkdir(parents=True)
        (tmp_path / "a" / "skills" / "one" / "SKILL.md").write_text("x")
        (tmp_path / "a" / "skills" / "one" / "EXTRA.md").write_text("x")  # noise
        (tmp_path / "b" / "skills" / "two" / "SKILL.md").write_text("x")
        result = es.discover_skills()
        assert result == [
            tmp_path / "a" / "skills" / "one",
            tmp_path / "b" / "skills" / "two",
        ]

    def test_parent_is_the_directory_holding_skill_md(
        self, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        mocker.patch.object(es, "PLUGINS_DIR", tmp_path)
        nested = tmp_path / "p" / "skills" / "deep"
        nested.mkdir(parents=True)
        (nested / "SKILL.md").write_text("x")
        assert es.discover_skills() == [nested]


# --------------------------------------------------------------------------- #
# score_skill
# --------------------------------------------------------------------------- #
class TestScoreSkill:
    def test_happy_path_parses_composite_and_sums_anti_patterns(
        self, mocker: MockerFixture
    ) -> None:
        payload = {
            "composite": {"score": 73.7, "badge": "silver"},
            "layers": [
                {"anti_patterns": ["a", "b"]},
                {"anti_patterns": ["c"]},
                {},
            ],
        }
        mocker.patch.object(
            es.subprocess, "run", return_value=_proc(mocker, 0, json.dumps(payload))
        )
        r = es.score_skill(Path("/s"), GIT, "quick")
        assert (r.score, r.badge, r.anti_patterns, r.error) == (73.7, "silver", 3, None)

    def test_missing_composite_yields_none_score_and_dash_badge(
        self, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(es.subprocess, "run", return_value=_proc(mocker, 0, "{}"))
        r = es.score_skill(Path("/s"), GIT, "quick")
        assert r.score is None
        assert r.badge == "-"
        assert r.error is None

    def test_falsy_badge_falls_back_to_dash(self, mocker: MockerFixture) -> None:
        body = json.dumps({"composite": {"score": 1.0, "badge": ""}})
        mocker.patch.object(es.subprocess, "run", return_value=_proc(mocker, 0, body))
        assert es.score_skill(Path("/s"), GIT, "quick").badge == "-"

    def test_failure_with_empty_stdout_uses_last_stderr_line(
        self, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(
            es.subprocess,
            "run",
            return_value=_proc(mocker, 1, "", "warn\nfatal: boom"),
        )
        r = es.score_skill(Path("/s"), GIT, "quick")
        assert r.score is None
        assert r.error == "fatal: boom"

    def test_failure_with_no_output_uses_generic_message(
        self, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(es.subprocess, "run", return_value=_proc(mocker, 1, "", ""))
        assert es.score_skill(Path("/s"), GIT, "quick").error == "plugin-eval failed"

    def test_unparsable_json_is_reported(self, mocker: MockerFixture) -> None:
        mocker.patch.object(
            es.subprocess, "run", return_value=_proc(mocker, 0, "not json")
        )
        assert es.score_skill(Path("/s"), GIT, "quick").error == "unparsable plugin-eval output"

    def test_command_vector_and_subprocess_kwargs(self, mocker: MockerFixture) -> None:
        run = mocker.patch.object(
            es.subprocess, "run", return_value=_proc(mocker, 0, "{}")
        )
        es.score_skill(Path("/skills/foo"), "SRC", "deep")
        cmd, kwargs = run.call_args[0][0], run.call_args[1]
        assert cmd == [
            "uvx",
            "--from",
            "SRC",
            "plugin-eval",
            "score",
            "/skills/foo",
            "--depth",
            "deep",
            "--output",
            "json",
        ]
        assert kwargs == {"capture_output": True, "text": True, "check": False}


# --------------------------------------------------------------------------- #
# run_passthrough
# --------------------------------------------------------------------------- #
class TestRunPassthrough:
    @pytest.mark.parametrize("code", [0, 1, 2, 42])
    def test_returns_subprocess_returncode(self, mocker: MockerFixture, code: int) -> None:
        mocker.patch.object(es.subprocess, "run", return_value=_proc(mocker, code))
        assert es.run_passthrough(["x"]) == code

    def test_runs_without_capture_and_check_false(self, mocker: MockerFixture) -> None:
        run = mocker.patch.object(es.subprocess, "run", return_value=_proc(mocker, 0))
        es.run_passthrough(["uvx", "y"])
        assert run.call_args[0][0] == ["uvx", "y"]
        assert run.call_args[1] == {"check": False}


# --------------------------------------------------------------------------- #
# print_table
# --------------------------------------------------------------------------- #
class TestPrintTable:
    def test_empty_uses_default_width(self, capsys: pytest.CaptureFixture[str]) -> None:
        es.print_table([])
        out = capsys.readouterr().out.splitlines()
        assert out[0].startswith("SKILL")
        assert set(out[1]) == {"-"}

    def test_ok_row_formatting(
        self, mocker: MockerFixture, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        mocker.patch.object(es, "REPO_ROOT", tmp_path)
        r = es.SkillResult(tmp_path / "plugins" / "foo", 66.5, "bronze", 2, None)
        es.print_table([r])
        last = capsys.readouterr().out.splitlines()[-1]
        assert "plugins/foo" in last
        assert "66.5" in last
        assert "bronze" in last
        assert last.strip().endswith("ok")

    def test_none_score_renders_dash(
        self, mocker: MockerFixture, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        mocker.patch.object(es, "REPO_ROOT", tmp_path)
        es.print_table([es.SkillResult(tmp_path / "p", None, "-", 0, None)])
        assert " - " in capsys.readouterr().out.splitlines()[-1]

    def test_error_row_shows_error(
        self, mocker: MockerFixture, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        mocker.patch.object(es, "REPO_ROOT", tmp_path)
        es.print_table([es.SkillResult(tmp_path / "p", None, "-", 0, "boom")])
        assert "ERROR: boom" in capsys.readouterr().out.splitlines()[-1]

    def test_header_separator_matches_header_width(
        self, mocker: MockerFixture, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        mocker.patch.object(es, "REPO_ROOT", tmp_path)
        long = tmp_path / ("x" * 60)
        es.print_table([es.SkillResult(long, 1.0, "g", 0, None)])
        header, sep = capsys.readouterr().out.splitlines()[:2]
        assert len(sep) == len(header)


# --------------------------------------------------------------------------- #
# run_score
# --------------------------------------------------------------------------- #
class TestRunScore:
    def test_no_skills_discovered_exits_2(
        self, mocker: MockerFixture, capsys: pytest.CaptureFixture[str]
    ) -> None:
        mocker.patch.object(es, "discover_skills", return_value=[])
        assert es.run_score(_ns(), GIT, "quick") == 2
        assert "No skills found" in capsys.readouterr().err

    def test_skill_relative_resolved_against_repo_root_missing_md_exits_2(
        self, mocker: MockerFixture, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        mocker.patch.object(es, "REPO_ROOT", tmp_path)
        rc = es.run_score(_ns(skill=Path("nope")), GIT, "quick")
        assert rc == 2
        assert str(tmp_path / "nope") in capsys.readouterr().err

    def test_single_skill_scored_and_tabled(
        self, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        mocker.patch.object(es, "REPO_ROOT", tmp_path)
        skill = tmp_path / "plugins" / "x"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text("x")
        score = mocker.patch.object(
            es, "score_skill", return_value=es.SkillResult(skill, 90.0, "platinum", 0, None)
        )
        table = mocker.patch.object(es, "print_table")
        assert es.run_score(_ns(skill=Path("plugins/x")), "SRC", "standard") == 0
        score.assert_called_once_with(skill.resolve(), "SRC", "standard")
        table.assert_called_once()

    def test_no_threshold_no_pass_message(
        self, mocker: MockerFixture, capsys: pytest.CaptureFixture[str]
    ) -> None:
        mocker.patch.object(es, "discover_skills", return_value=[Path("/a")])
        mocker.patch.object(
            es, "score_skill", return_value=es.SkillResult(Path("/a"), 50.0, "-", 0, None)
        )
        mocker.patch.object(es, "print_table")
        assert es.run_score(_ns(), GIT, "quick") == 0
        assert "PASS" not in capsys.readouterr().out

    def test_threshold_all_pass(
        self, mocker: MockerFixture, capsys: pytest.CaptureFixture[str]
    ) -> None:
        mocker.patch.object(es, "discover_skills", return_value=[Path("/a")])
        mocker.patch.object(
            es, "score_skill", return_value=es.SkillResult(Path("/a"), 80.0, "g", 0, None)
        )
        mocker.patch.object(es, "print_table")
        assert es.run_score(_ns(threshold=57.0), GIT, "quick") == 0
        assert "PASS: all skills >= threshold 57.0." in capsys.readouterr().out

    def test_threshold_below_fails_exit_1(
        self, mocker: MockerFixture, capsys: pytest.CaptureFixture[str]
    ) -> None:
        mocker.patch.object(es, "discover_skills", return_value=[Path("/a")])
        mocker.patch.object(
            es, "score_skill", return_value=es.SkillResult(Path("/a"), 10.0, "-", 0, None)
        )
        mocker.patch.object(es, "print_table")
        assert es.run_score(_ns(threshold=57.0), GIT, "quick") == 1
        assert "FAIL" in capsys.readouterr().err

    def test_errored_skill_counts_as_failure(self, mocker: MockerFixture) -> None:
        mocker.patch.object(es, "discover_skills", return_value=[Path("/a")])
        mocker.patch.object(
            es, "score_skill", return_value=es.SkillResult(Path("/a"), None, "-", 0, "boom")
        )
        mocker.patch.object(es, "print_table")
        assert es.run_score(_ns(threshold=57.0), GIT, "quick") == 1

    def test_none_score_without_error_is_not_a_failure(self, mocker: MockerFixture) -> None:
        mocker.patch.object(es, "discover_skills", return_value=[Path("/a")])
        mocker.patch.object(
            es, "score_skill", return_value=es.SkillResult(Path("/a"), None, "-", 0, None)
        )
        mocker.patch.object(es, "print_table")
        assert es.run_score(_ns(threshold=57.0), GIT, "quick") == 0


# --------------------------------------------------------------------------- #
# _resolve_target
# --------------------------------------------------------------------------- #
class TestResolveTarget:
    def test_absolute_unchanged(self, mocker: MockerFixture, tmp_path: Path) -> None:
        mocker.patch.object(es, "REPO_ROOT", tmp_path / "repo")
        assert es._resolve_target(Path("/abs/x")) == "/abs/x"

    def test_relative_joined_to_repo_root(self, mocker: MockerFixture, tmp_path: Path) -> None:
        mocker.patch.object(es, "REPO_ROOT", tmp_path)
        assert es._resolve_target(Path("plugins/y")) == str(tmp_path / "plugins" / "y")


# --------------------------------------------------------------------------- #
# run_certify / run_compare / run_init
# --------------------------------------------------------------------------- #
class TestRunCertify:
    @pytest.mark.parametrize("targets", [[], [Path("a"), Path("b")]])
    def test_wrong_target_count_exits_2(
        self, mocker: MockerFixture, capsys: pytest.CaptureFixture[str], targets: list[Path]
    ) -> None:
        rp = mocker.patch.object(es, "run_passthrough")
        assert es.run_certify(_ns(targets=targets), "SRC") == 2
        assert "certify requires exactly one" in capsys.readouterr().err
        rp.assert_not_called()

    def test_builds_command_and_returns_passthrough_code(
        self, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        mocker.patch.object(es, "REPO_ROOT", tmp_path)
        rp = mocker.patch.object(es, "run_passthrough", return_value=9)
        rc = es.run_certify(_ns(targets=[Path("plugins/x")]), "SRC")
        assert rc == 9
        assert rp.call_args[0][0] == [
            "uvx",
            "--from",
            "SRC",
            "plugin-eval",
            "certify",
            str(tmp_path / "plugins" / "x"),
            "--output",
            "markdown",
        ]

    def test_threshold_appended_when_set(self, mocker: MockerFixture, tmp_path: Path) -> None:
        mocker.patch.object(es, "REPO_ROOT", tmp_path)
        rp = mocker.patch.object(es, "run_passthrough", return_value=0)
        es.run_certify(_ns(targets=[Path("/x")], threshold=60.0), "SRC")
        assert rp.call_args[0][0][-2:] == ["--threshold", "60.0"]


class TestRunCompare:
    @pytest.mark.parametrize("targets", [[], [Path("a")], [Path("a"), Path("b"), Path("c")]])
    def test_wrong_target_count_exits_2(
        self, mocker: MockerFixture, capsys: pytest.CaptureFixture[str], targets: list[Path]
    ) -> None:
        rp = mocker.patch.object(es, "run_passthrough")
        assert es.run_compare(_ns(targets=targets), "SRC", "quick") == 2
        assert "compare requires exactly two" in capsys.readouterr().err
        rp.assert_not_called()

    def test_builds_command_with_both_targets_and_depth(
        self, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        mocker.patch.object(es, "REPO_ROOT", tmp_path)
        rp = mocker.patch.object(es, "run_passthrough", return_value=3)
        rc = es.run_compare(_ns(targets=[Path("/a"), Path("plugins/b")]), "SRC", "deep")
        assert rc == 3
        assert rp.call_args[0][0] == [
            "uvx",
            "--from",
            "SRC",
            "plugin-eval",
            "compare",
            "/a",
            str(tmp_path / "plugins" / "b"),
            "--depth",
            "deep",
            "--output",
            "markdown",
        ]


class TestRunInit:
    @pytest.mark.parametrize("targets", [[], [Path("a"), Path("b")]])
    def test_wrong_target_count_exits_2(
        self, mocker: MockerFixture, capsys: pytest.CaptureFixture[str], targets: list[Path]
    ) -> None:
        rp = mocker.patch.object(es, "run_passthrough")
        assert es.run_init(_ns(targets=targets), "SRC") == 2
        assert "init requires exactly one" in capsys.readouterr().err
        rp.assert_not_called()

    def test_builds_command_without_corpus_dir(
        self, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        mocker.patch.object(es, "REPO_ROOT", tmp_path)
        rp = mocker.patch.object(es, "run_passthrough", return_value=0)
        es.run_init(_ns(targets=[Path("/plugins")]), "SRC")
        assert rp.call_args[0][0] == ["uvx", "--from", "SRC", "plugin-eval", "init", "/plugins"]

    def test_corpus_dir_appended_when_set(self, mocker: MockerFixture, tmp_path: Path) -> None:
        mocker.patch.object(es, "REPO_ROOT", tmp_path)
        rp = mocker.patch.object(es, "run_passthrough", return_value=0)
        es.run_init(_ns(targets=[Path("/p")], corpus_dir=Path("/corpus")), "SRC")
        assert rp.call_args[0][0][-2:] == ["--corpus-dir", "/corpus"]


# --------------------------------------------------------------------------- #
# main (argparse + env + needs_llm derivation + dispatch)
# --------------------------------------------------------------------------- #
class TestMain:
    def _argv(self, mocker: MockerFixture, *args: str) -> None:
        mocker.patch.object(es.sys, "argv", ["eval-skills.py", *args])
        mocker.patch.dict(es.os.environ, {}, clear=False)
        es.os.environ.pop("PLUGIN_EVAL_SOURCE", None)

    def test_default_dispatches_run_score_static_quick(self, mocker: MockerFixture) -> None:
        self._argv(mocker)
        rs = mocker.patch.object(es, "run_score", return_value=7)
        assert es.main() == 7
        args, source, depth = rs.call_args[0]
        assert args.command == "score"
        assert source == es.DEFAULT_SOURCE
        assert depth == "quick"

    def test_llm_judge_wraps_source(self, mocker: MockerFixture) -> None:
        self._argv(mocker, "--skill", "x", "--layer", "llm-judge")
        rs = mocker.patch.object(es, "run_score", return_value=0)
        es.main()
        _, source, depth = rs.call_args[0]
        assert depth == "standard"
        assert source == f"plugin-eval[llm] @ {es.DEFAULT_SOURCE}"

    def test_certify_forces_llm_even_with_static_layer(self, mocker: MockerFixture) -> None:
        self._argv(mocker, "--command", "certify", "--layer", "static", "p")
        rc = mocker.patch.object(es, "run_certify", return_value=0)
        es.main()
        _, source = rc.call_args[0]
        assert source == f"plugin-eval[llm] @ {es.DEFAULT_SOURCE}"

    def test_compare_dispatch_passes_depth(self, mocker: MockerFixture) -> None:
        self._argv(mocker, "--command", "compare", "--layer", "monte-carlo", "a", "b")
        rc = mocker.patch.object(es, "run_compare", return_value=0)
        es.main()
        assert rc.call_args[0][2] == "deep"

    def test_init_dispatch(self, mocker: MockerFixture) -> None:
        self._argv(mocker, "--command", "init", "plugins/")
        ri = mocker.patch.object(es, "run_init", return_value=5)
        assert es.main() == 5
        ri.assert_called_once()

    def test_env_var_overrides_source(self, mocker: MockerFixture) -> None:
        mocker.patch.object(es.sys, "argv", ["eval-skills.py"])
        mocker.patch.dict(es.os.environ, {"PLUGIN_EVAL_SOURCE": "git+custom"})
        rs = mocker.patch.object(es, "run_score", return_value=0)
        es.main()
        assert rs.call_args[0][1] == "git+custom"

    def test_invalid_layer_is_rejected(self, mocker: MockerFixture) -> None:
        self._argv(mocker, "--layer", "bogus")
        with pytest.raises(SystemExit):
            es.main()
