"""Tests for the Snyk agent-scan pre-commit integration.

Two templates, per repo convention:
- Pure-function tests load `scripts/snyk-agent-scan.py` via importlib (it has
  no import-time side effects beyond the optional `load_dotenv()` call).
- CLI/behavioral tests shell out via subprocess + sys.executable, mirroring
  tests/test_validate_unicode_hygiene.py.

No network: every scanner invocation is redirected to a fake scanner fixture
script under tests/fixtures/snyk-agent-scan/ via SNYK_AGENT_SCAN_CMD or
cmd_override. All subprocess tests pass an explicit `env` dict rather than
inheriting the real environment, so a developer's real .env never leaks in.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PRECOMMIT_SCRIPT = REPO_ROOT / "scripts" / "snyk-agent-scan.py"
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "snyk-agent-scan"


def _load(path: Path) -> ModuleType:
    """Load `scripts/snyk-agent-scan.py` by path."""
    spec = importlib.util.spec_from_file_location(path.stem.replace("-", "_"), path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


precommit = _load(PRECOMMIT_SCRIPT)
snyk = precommit  # alias used by the scan-helper tests below


def _base_env(**extra: str) -> dict[str, str]:
    """A minimal, explicit environment for subprocess tests.

    The script under test calls `load_dotenv()` with no path argument, which
    walks up from the *script's own* location (inside this real repo) looking
    for a `.env` file — not from the subprocess `cwd` used by these tests. So a
    developer's real `.env` (with a real SNYK_TOKEN) would otherwise leak into
    every subprocess here. `load_dotenv()` defaults to `override=False`, so
    pre-setting each var (even to "") blocks it from ever overwriting it.
    """
    env = {
        "PATH": "/usr/bin:/bin:/usr/local/bin",
        "SNYK_TOKEN": "",
        "SNYK_AGENT_SCAN_ENFORCE": "",
        "SNYK_AGENT_SCAN_CMD": "",
    }
    env.update(extra)
    return env


# --------------------------------------------------------------------------
# Pure-function tests: scan helpers in scripts/snyk-agent-scan.py
# --------------------------------------------------------------------------


def test_severity_counts_clean() -> None:
    parsed = {"/root": {"issues": []}}
    assert snyk.severity_counts(parsed) == dict.fromkeys(snyk.SEVERITY_KEYS, 0)


def test_severity_counts_single_high_lowercase() -> None:
    parsed = {"/root": {"issues": [{"extra_data": {"severity": "high"}}]}}
    counts = snyk.severity_counts(parsed)
    assert counts["High"] == 1
    assert counts["Critical"] == 0


def test_severity_counts_mixed_known_and_unrecognized() -> None:
    parsed = {
        "/root": {
            "issues": [
                {"extra_data": {"severity": "critical"}},
                {"extra_data": {"severity": "bogus-severity"}},
                {"extra_data": {}},
                {},
            ]
        }
    }
    counts = snyk.severity_counts(parsed)
    assert counts["Critical"] == 1
    assert sum(counts.values()) == 1


def test_severity_counts_multiple_roots() -> None:
    parsed = {
        "/root/a": {"issues": [{"extra_data": {"severity": "high"}}]},
        "/root/b": {"issues": [{"extra_data": {"severity": "high"}}, {"extra_data": {"severity": "low"}}]},
    }
    counts = snyk.severity_counts(parsed)
    assert counts["High"] == 2
    assert counts["Low"] == 1


def test_severity_counts_malformed_input_never_raises() -> None:
    for bad in ({}, [], None, "not a dict", 42):
        counts = snyk.severity_counts(bad)
        assert counts == dict.fromkeys(snyk.SEVERITY_KEYS, 0)


def test_summarize_clean() -> None:
    result = snyk.ScanResult(status=snyk.ScanStatus.OK, targets=[Path("a"), Path("b")])
    assert "clean" in snyk.summarize(result)
    assert "2 skills scanned" in snyk.summarize(result)


def test_summarize_with_findings_exact_shape() -> None:
    result = snyk.ScanResult(
        status=snyk.ScanStatus.OK,
        severity_counts={"Critical": 0, "High": 2, "Medium": 1, "Low": 0},
        targets=[Path("a"), Path("b"), Path("c")],
    )
    summary = snyk.summarize(result)
    assert summary == (
        "Snyk agent-scan: 2 High, 1 Medium in 3 skills — run `uvx snyk-agent-scan@latest .claude/skills` for details"
    )


def test_summarize_error() -> None:
    result = snyk.ScanResult(status=snyk.ScanStatus.ERROR, error="boom")
    assert "boom" in snyk.summarize(result)


def test_summarize_skip_is_empty() -> None:
    result = snyk.ScanResult(status=snyk.ScanStatus.SKIP)
    assert snyk.summarize(result) == ""


def test_parse_json_loose_clean() -> None:
    assert snyk._parse_json_loose('{"a": 1}') == {"a": 1}


def test_parse_json_loose_with_leading_noise() -> None:
    text = 'some log line\nanother line\n{"a": 1}'
    assert snyk._parse_json_loose(text) == {"a": 1}


def test_parse_json_loose_empty_and_garbage() -> None:
    assert snyk._parse_json_loose("") is None
    assert snyk._parse_json_loose("   ") is None
    assert snyk._parse_json_loose("not json at all") is None


def test_run_scan_no_targets_is_skip() -> None:
    result = snyk.run_scan([], token="t")
    assert result.status is snyk.ScanStatus.SKIP


def test_run_scan_no_token_is_skip(tmp_path: Path) -> None:
    result = snyk.run_scan([tmp_path / "x.md"], token="")
    assert result.status is snyk.ScanStatus.SKIP


def test_run_scan_clean_fixture(tmp_path: Path) -> None:
    target = tmp_path / "x.md"
    target.write_text("x")
    result = snyk.run_scan([target], token="t", cmd_override=[sys.executable, str(FIXTURES / "fake_scanner_clean.py")])
    assert result.status is snyk.ScanStatus.OK
    assert sum(result.severity_counts.values()) == 0


def test_run_scan_high_fixture_ignores_nonzero_exit(tmp_path: Path) -> None:
    target = tmp_path / "x.md"
    target.write_text("x")
    result = snyk.run_scan([target], token="t", cmd_override=[sys.executable, str(FIXTURES / "fake_scanner_high.py")])
    assert result.status is snyk.ScanStatus.OK
    assert result.severity_counts["High"] == 1


def test_run_scan_timeout() -> None:
    result = snyk.run_scan(
        [Path("x.md")],
        token="t",
        timeout=0.3,
        cmd_override=[sys.executable, str(FIXTURES / "fake_scanner_sleep.py")],
    )
    assert result.status is snyk.ScanStatus.ERROR
    assert result.error is not None
    assert "timed out" in result.error


# --------------------------------------------------------------------------
# Pure-function tests: scripts/snyk-agent-scan.py's _filter_paths
# --------------------------------------------------------------------------


def test_filter_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # _filter_paths matches the anchored regex against the raw path string as
    # given (mirroring how pre-commit passes repo-relative paths), so the cwd
    # must change to tmp_path for a relative "good" path to also resolve via
    # candidate.is_file().
    monkeypatch.chdir(tmp_path)
    good_rel = Path(".claude") / "skills" / "foo" / "SKILL.md"
    good_abs = tmp_path / good_rel
    good_abs.parent.mkdir(parents=True)
    good_abs.write_text("x")
    bad_agent = Path("plugins") / "x" / "agents" / "a.md"
    (tmp_path / bad_agent).parent.mkdir(parents=True)
    (tmp_path / bad_agent).write_text("x")
    mcp = Path("mcp.json")
    (tmp_path / mcp).write_text("{}")

    filtered = precommit._filter_paths([str(good_rel), str(bad_agent), str(mcp), "docs/foo.md"])
    assert filtered == [good_rel]


# --------------------------------------------------------------------------
# CLI/behavioral tests: scripts/snyk-agent-scan.py (pre-commit entrypoint)
# --------------------------------------------------------------------------


def _skill_file(tmp_path: Path, rel: str = ".claude/skills/demo/SKILL.md") -> Path:
    path = tmp_path / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("---\nname: demo\ndescription: demo\n---\nHello.\n")
    return path


def test_precommit_no_token_skips(tmp_path: Path) -> None:
    _skill_file(tmp_path)
    result = subprocess.run(
        [sys.executable, str(PRECOMMIT_SCRIPT), ".claude/skills/demo/SKILL.md"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env=_base_env(),
        check=False,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_precommit_advisory_clean(tmp_path: Path) -> None:
    _skill_file(tmp_path)
    result = subprocess.run(
        [sys.executable, str(PRECOMMIT_SCRIPT), ".claude/skills/demo/SKILL.md"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env=_base_env(
            SNYK_TOKEN="fake-token",
            SNYK_AGENT_SCAN_CMD=f"{sys.executable} {FIXTURES / 'fake_scanner_clean.py'}",
        ),
        check=False,
    )
    assert result.returncode == 0
    assert "clean" in result.stdout


def test_precommit_advisory_findings_no_enforce_ignores_exit_code(tmp_path: Path) -> None:
    _skill_file(tmp_path)
    result = subprocess.run(
        [sys.executable, str(PRECOMMIT_SCRIPT), ".claude/skills/demo/SKILL.md"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env=_base_env(
            SNYK_TOKEN="fake-token",
            SNYK_AGENT_SCAN_CMD=f"{sys.executable} {FIXTURES / 'fake_scanner_high.py'}",
        ),
        check=False,
    )
    assert result.returncode == 0  # fixture itself exits 1 — gating must ignore that
    assert "High" in result.stdout


def test_precommit_enforce_trips_on_high(tmp_path: Path) -> None:
    _skill_file(tmp_path)
    result = subprocess.run(
        [sys.executable, str(PRECOMMIT_SCRIPT), ".claude/skills/demo/SKILL.md"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env=_base_env(
            SNYK_TOKEN="fake-token",
            SNYK_AGENT_SCAN_CMD=f"{sys.executable} {FIXTURES / 'fake_scanner_high.py'}",
            SNYK_AGENT_SCAN_ENFORCE="1",
        ),
        check=False,
    )
    assert result.returncode == 1


def test_precommit_enforce_does_not_trip_on_medium_only(tmp_path: Path) -> None:
    _skill_file(tmp_path)
    result = subprocess.run(
        [sys.executable, str(PRECOMMIT_SCRIPT), ".claude/skills/demo/SKILL.md"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env=_base_env(
            SNYK_TOKEN="fake-token",
            SNYK_AGENT_SCAN_CMD=f"{sys.executable} {FIXTURES / 'fake_scanner_medium.py'}",
            SNYK_AGENT_SCAN_ENFORCE="1",
        ),
        check=False,
    )
    assert result.returncode == 0


def test_precommit_no_relevant_files_never_invokes_scanner(tmp_path: Path) -> None:
    sentinel = tmp_path / "sentinel"
    result = subprocess.run(
        [sys.executable, str(PRECOMMIT_SCRIPT), "README.md"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env=_base_env(
            SNYK_TOKEN="fake-token",
            SNYK_AGENT_SCAN_CMD=f"{sys.executable} {FIXTURES / 'fake_scanner_sentinel.py'}",
            FAKE_SCANNER_SENTINEL=str(sentinel),
        ),
        check=False,
    )
    assert result.returncode == 0
    assert not sentinel.exists()

