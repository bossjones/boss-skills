"""Unit tests for ``scripts/markdown_formatter.py``.

Loaded by path via importlib (mirroring ``tests/test_eval_skills.py``). The
module is import-safe — its CLI lives in ``main()`` behind an
``if __name__ == "__main__"`` guard, so loading it has no side effects.
"""

from __future__ import annotations

import importlib.util
import io
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "markdown_formatter.py"


def _load(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(path.stem.replace("-", "_"), path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


mf = _load(SCRIPT)


# --------------------------------------------------------------------------- #
# detect_language
# --------------------------------------------------------------------------- #
class TestDetectLanguage:
    def test_valid_json_object(self) -> None:
        assert mf.detect_language('{"a": 1}') == "json"

    def test_valid_json_array(self) -> None:
        assert mf.detect_language("[1, 2, 3]") == "json"

    def test_brace_but_invalid_json_is_not_json(self) -> None:
        assert mf.detect_language("{not: valid json,,}") == "text"

    @pytest.mark.parametrize(
        "code",
        ["def foo():\n    pass", "import os", "from pathlib import Path"],
    )
    def test_python(self, code: str) -> None:
        assert mf.detect_language(code) == "python"

    @pytest.mark.parametrize(
        "code",
        ["function f() {}", "const x = 1", "x => x + 1", "console.log('hi')"],
    )
    def test_javascript(self, code: str) -> None:
        assert mf.detect_language(code) == "javascript"

    @pytest.mark.parametrize(
        "code",
        ["#!/usr/bin/env bash\necho hi", "for x in a b; do echo $x; done"],
    )
    def test_bash(self, code: str) -> None:
        assert mf.detect_language(code) == "bash"

    def test_sql_case_insensitive(self) -> None:
        assert mf.detect_language("select * from t") == "sql"

    def test_empty_is_text(self) -> None:
        assert mf.detect_language("") == "text"

    def test_unknown_is_text(self) -> None:
        assert mf.detect_language("just some prose here") == "text"

    def test_json_precedence_over_python(self) -> None:
        # Valid JSON that also contains the word import-like content stays json.
        assert mf.detect_language('{"import": "from x"}') == "json"


# --------------------------------------------------------------------------- #
# format_markdown
# --------------------------------------------------------------------------- #
class TestFormatMarkdown:
    def test_unlabeled_fence_gets_language(self) -> None:
        out = mf.format_markdown("```\ndef f():\n    pass\n```\n")
        assert out.startswith("```python\n")

    def test_labeled_fence_untouched(self) -> None:
        src = "```python\ndef f():\n    pass\n```\n"
        assert mf.format_markdown(src) == src

    def test_indented_fence_indent_preserved(self) -> None:
        out = mf.format_markdown("   ```\nimport os\n   ```\n")
        assert out.startswith("   ```python\n")

    def test_collapses_three_or_more_blank_lines(self) -> None:
        assert mf.format_markdown("a\n\n\n\nb\n") == "a\n\nb\n"

    def test_two_blank_lines_preserved(self) -> None:
        assert mf.format_markdown("a\n\nb\n") == "a\n\nb\n"

    def test_trailing_whitespace_stripped_single_newline(self) -> None:
        assert mf.format_markdown("text   \n\n\n") == "text\n"

    def test_empty_input_yields_single_newline(self) -> None:
        assert mf.format_markdown("") == "\n"

    def test_multiple_unlabeled_fences_all_labeled(self) -> None:
        src = "```\nimport os\n```\n\ntext\n\n```\nSELECT 1 FROM t\n```\n"
        out = mf.format_markdown(src)
        assert "```python\n" in out
        assert "```sql\n" in out

    def test_idempotent(self) -> None:
        src = "# Title\n\n\n\n```\nconst a = 1\n```\n\n\ntrailing   \n"
        once = mf.format_markdown(src)
        assert mf.format_markdown(once) == once


# --------------------------------------------------------------------------- #
# main() — CLI mode
# --------------------------------------------------------------------------- #
class TestMainCli:
    def test_single_file_rewritten_and_message_on_stdout(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        f = tmp_path / "doc.md"
        f.write_text("```\nimport os\n```\n")
        assert mf.main([str(f)]) == 0
        assert f.read_text().startswith("```python\n")
        out = capsys.readouterr()
        assert "Fixed markdown formatting" in out.out
        assert out.err == ""

    def test_multiple_files_each_processed(self, tmp_path: Path) -> None:
        a = tmp_path / "a.md"
        b = tmp_path / "b.md"
        a.write_text("```\nimport os\n```\n")
        b.write_text("x\n\n\n\ny\n")
        assert mf.main([str(a), str(b)]) == 0
        assert a.read_text().startswith("```python\n")
        assert b.read_text() == "x\n\ny\n"

    def test_non_markdown_file_skipped(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        f = tmp_path / "code.py"
        f.write_text("x\n\n\n\ny\n")
        assert mf.main([str(f)]) == 0
        assert f.read_text() == "x\n\n\n\ny\n"  # untouched
        assert capsys.readouterr().out == ""

    def test_missing_file_warns_and_continues(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert mf.main([str(tmp_path / "nope.md")]) == 0
        assert "File not found" in capsys.readouterr().err

    def test_read_error_caught_and_continues(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str], mocker: MockerFixture
    ) -> None:
        f = tmp_path / "doc.md"
        f.write_text("```\nimport os\n```\n")
        mocker.patch.object(mf, "open", side_effect=OSError("boom"), create=True)
        assert mf.main([str(f)]) == 0
        assert "Error formatting" in capsys.readouterr().err

    def test_blocking_with_change_exits_2_message_on_stderr(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        f = tmp_path / "doc.md"
        f.write_text("```\nimport os\n```\n")
        assert mf.main(["--blocking", str(f)]) == 2
        err = capsys.readouterr()
        assert "Fixed markdown formatting" in err.err
        assert err.out == ""

    def test_blocking_no_change_exits_0(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("```python\nimport os\n```\n")  # already formatted
        assert mf.main(["--blocking", str(f)]) == 0

    def test_non_blocking_with_change_exits_0(self, tmp_path: Path) -> None:
        f = tmp_path / "doc.md"
        f.write_text("```\nimport os\n```\n")
        assert mf.main([str(f)]) == 0

    def test_unchanged_file_not_rewritten(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        f = tmp_path / "doc.md"
        f.write_text("```python\nimport os\n```\n")
        before = f.stat().st_mtime_ns
        assert mf.main([str(f)]) == 0
        assert f.stat().st_mtime_ns == before
        assert capsys.readouterr().out == ""


# --------------------------------------------------------------------------- #
# main() — hook (stdin) mode
# --------------------------------------------------------------------------- #
class TestMainHook:
    def test_valid_stdin_json_processed(
        self, tmp_path: Path, mocker: MockerFixture
    ) -> None:
        f = tmp_path / "doc.md"
        f.write_text("```\nimport os\n```\n")
        payload = f'{{"tool_input": {{"file_path": "{f}"}}}}'
        mocker.patch.object(mf.sys, "stdin", io.StringIO(payload))
        assert mf.main([]) == 0
        assert f.read_text().startswith("```python\n")

    def test_invalid_stdin_json_returns_0(
        self, capsys: pytest.CaptureFixture[str], mocker: MockerFixture
    ) -> None:
        mocker.patch.object(mf.sys, "stdin", io.StringIO("not json"))
        assert mf.main([]) == 0
        assert "Invalid JSON input" in capsys.readouterr().err

    def test_stdin_json_without_tool_input_no_files(self, mocker: MockerFixture) -> None:
        mocker.patch.object(mf.sys, "stdin", io.StringIO('{"other": 1}'))
        assert mf.main([]) == 0


# --------------------------------------------------------------------------- #
# main() — outer exception guard
# --------------------------------------------------------------------------- #
def test_outer_exception_is_non_blocking(
    capsys: pytest.CaptureFixture[str], mocker: MockerFixture
) -> None:
    mocker.patch.object(mf.os.path, "exists", side_effect=RuntimeError("kaboom"))
    assert mf.main(["x.md"]) == 0
    assert "Error in markdown formatter" in capsys.readouterr().err
