#!/usr/bin/env -S uv run --script --quiet
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "python-dotenv",
# ]
# ///
"""Pre-commit gate: advisory Snyk agent-scan of staged SKILL.md files.

Snyk's `agent-scan` inspects `SKILL.md`-shaped skill folders (and real MCP JSON
configs) for prompt injection, tool poisoning, and hidden-Unicode obfuscation.
Empirically (2026-07), passing it any other markdown path (an `agents/*.md` or
`commands/*.md` file) makes it try to parse that file as an MCP JSON5 config and
fail — a harmless no-op, not a real analysis — so only `SKILL.md` paths are ever
worth scanning.

Advisory by default: prints findings and exits 0 regardless of severity. Set
SNYK_AGENT_SCAN_ENFORCE=1 to exit 1 when Critical/High findings are present.
Silently exits 0 (no output) whenever SNYK_TOKEN is not resolvable, so
contributors without a token are completely unaffected.

Usage:
    uv run scripts/snyk-agent-scan.py <staged-file-paths...>
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass  # dotenv is optional

SEVERITY_KEYS: tuple[str, ...] = ("Critical", "High", "Medium", "Low")

_SEVERITY_ALIASES: dict[str, str] = {
    "critical": "Critical",
    "high": "High",
    "medium": "Medium",
    "moderate": "Medium",
    "low": "Low",
    "info": "Low",
    "informational": "Low",
}

DEFAULT_CMD: tuple[str, ...] = ("uvx", "snyk-agent-scan@latest")

# Only SKILL.md files are meaningful scan targets — see module docstring.
TARGET_GLOBS: tuple[str, ...] = (
    "plugins/**/skills/**/SKILL.md",
    ".claude/skills/**/SKILL.md",
)

# Belt-and-suspenders: never scan MCP server config, even if a future glob edit
# loosens a pattern to also match these. Scanning MCP configs can launch stdio
# MCP servers, which this integration must never do.
EXCLUDE_NAMES: frozenset[str] = frozenset({"mcp.json", ".mcp.json"})

# Don't let test fixtures (some of which are deliberately malicious, to exercise the
# scanner) get swept into a default project-wide scan.
EXCLUDE_DIR_PREFIXES: tuple[str, ...] = ("tests/fixtures/",)


class ScanStatus(Enum):
    OK = "ok"  # scan ran, JSON parsed (findings may be empty = clean)
    SKIP = "skip"  # not attempted (disabled, no token, no targets)
    ERROR = "error"  # attempted but failed (timeout, subprocess error, unparsable JSON)


@dataclass
class Finding:
    severity: str  # normalized to one of SEVERITY_KEYS, or "Unknown"
    code: str | None = None
    path: str | None = None
    message: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class ScanResult:
    status: ScanStatus
    severity_counts: dict[str, int] = field(default_factory=lambda: dict.fromkeys(SEVERITY_KEYS, 0))
    findings: list[Finding] = field(default_factory=list)
    raw_stdout: str = ""
    error: str | None = None
    targets: list[Path] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.status is ScanStatus.OK

    @property
    def skipped(self) -> bool:
        return self.status is ScanStatus.SKIP


def snyk_token() -> str:
    """Return the configured Snyk token, or an empty string."""
    return (os.environ.get("CLAUDE_PLUGIN_OPTION_SNYK_TOKEN") or os.environ.get("SNYK_TOKEN") or "").strip()


def resolve_targets(root: Path) -> list[Path]:
    """Return SKILL.md files under ``root``, excluding MCP configs and test fixtures."""
    seen: set[Path] = set()
    targets: list[Path] = []
    for pattern in TARGET_GLOBS:
        for path in sorted(root.glob(pattern)):
            if not path.is_file() or path.name in EXCLUDE_NAMES:
                continue
            rel = path.relative_to(root).as_posix()
            if any(rel.startswith(prefix) for prefix in EXCLUDE_DIR_PREFIXES):
                continue
            if path in seen:
                continue
            seen.add(path)
            targets.append(path)
    return targets


def _resolve_cmd(cmd_override: Sequence[str] | None) -> list[str]:
    if cmd_override is not None:
        return list(cmd_override)
    env_cmd = os.environ.get("SNYK_AGENT_SCAN_CMD")
    if env_cmd:
        try:
            return shlex.split(env_cmd)
        except ValueError:
            return env_cmd.split()
    return list(DEFAULT_CMD)


def _parse_json_loose(stdout: str) -> Any | None:
    """Parse ``--json`` stdout, tolerating leading log noise before the JSON body."""
    text = stdout.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    for marker in ("{", "["):
        idx = text.find(marker)
        if idx == -1:
            continue
        try:
            return json.loads(text[idx:])
        except json.JSONDecodeError:
            continue
    return None


def _iter_issues(parsed: Any) -> Iterator[tuple[dict[str, Any], dict[str, Any]]]:
    """Yield (root_result, issue) pairs from the real scan-result shape."""
    if not isinstance(parsed, dict):
        return
    for value in parsed.values():
        if not isinstance(value, dict):
            continue
        root_result: dict[str, Any] = value
        for issue in root_result.get("issues") or []:
            if isinstance(issue, dict):
                yield root_result, issue


def _normalized_severity(issue: dict[str, Any]) -> str | None:
    extra: Any = issue.get("extra_data")
    if not isinstance(extra, dict):
        return None
    extra_data: dict[str, Any] = extra
    severity = extra_data.get("severity")
    if not severity:
        return None
    return _SEVERITY_ALIASES.get(str(severity).lower())


def severity_counts(parsed: Any) -> dict[str, int]:
    """Count findings per normalized severity bucket."""
    counts = dict.fromkeys(SEVERITY_KEYS, 0)
    for _root_result, issue in _iter_issues(parsed):
        normalized = _normalized_severity(issue)
        if normalized:
            counts[normalized] += 1
    return counts


def _extract_findings(parsed: Any) -> list[Finding]:
    findings: list[Finding] = []
    for root_result, issue in _iter_issues(parsed):
        normalized = _normalized_severity(issue)
        findings.append(
            Finding(
                severity=normalized or "Unknown",
                code=issue.get("code"),
                path=root_result.get("client") or root_result.get("path"),
                message=issue.get("message"),
                raw=issue,
            )
        )
    return findings


def run_scan(
    targets: Sequence[Path],
    *,
    token: str,
    timeout: float = 60.0,
    cmd_override: Sequence[str] | None = None,
) -> ScanResult:
    """Invoke snyk-agent-scan and parse its JSON output."""
    if not targets:
        return ScanResult(status=ScanStatus.SKIP, error="no targets")
    if not token:
        return ScanResult(status=ScanStatus.SKIP, error="no SNYK_TOKEN")

    argv = [*_resolve_cmd(cmd_override), "--json", *(str(t) for t in targets)]
    env = {**os.environ, "SNYK_TOKEN": token}

    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, env=env, check=False)  # noqa: S603
    except subprocess.TimeoutExpired:
        return ScanResult(status=ScanStatus.ERROR, error=f"scan timed out after {timeout}s", targets=list(targets))
    except (OSError, subprocess.SubprocessError) as exc:
        return ScanResult(status=ScanStatus.ERROR, error=f"scan invocation failed: {exc}", targets=list(targets))

    stdout = proc.stdout or ""
    parsed = _parse_json_loose(stdout)
    if parsed is None:
        return ScanResult(
            status=ScanStatus.ERROR,
            error=f"could not parse scanner JSON (exit={proc.returncode})",
            raw_stdout=stdout,
            targets=list(targets),
        )

    return ScanResult(
        status=ScanStatus.OK,
        severity_counts=severity_counts(parsed),
        findings=_extract_findings(parsed),
        raw_stdout=stdout,
        targets=list(targets),
    )


def summarize(result: ScanResult) -> str:
    """Render a one-line summary of the scan result."""
    if result.status is ScanStatus.SKIP:
        return ""
    if result.status is ScanStatus.ERROR:
        return f"Snyk agent-scan: error ({result.error})" if result.error else "Snyk agent-scan: error"

    counts = result.severity_counts
    parts = [f"{n} {sev}" for sev, n in counts.items() if n]
    n = len(result.targets)
    noun = "skill" if n == 1 else "skills"
    if not parts:
        return f"Snyk agent-scan: clean ({n} {noun} scanned)"
    return (
        f"Snyk agent-scan: {', '.join(parts)} in {n} {noun} — "
        "run `uvx snyk-agent-scan@latest .claude/skills` for details"
    )


TARGET_RE = re.compile(r"^(plugins/.+/skills/.+/SKILL\.md|\.claude/skills/.+/SKILL\.md)$")


def _filter_paths(paths: list[str]) -> list[Path]:
    """Keep only SKILL.md paths matching TARGET_RE, even though pre-commit's own
    `files:` regex already restricts what's passed — this script can also be
    invoked via `--all-files`, manually, or by a future misconfigured hook entry."""
    out: list[Path] = []
    for raw in paths:
        rel = raw.replace(os.sep, "/")
        candidate = Path(raw)
        if candidate.name in EXCLUDE_NAMES:
            continue
        if TARGET_RE.match(rel) and candidate.is_file():
            out.append(candidate)
    return out


def _run(argv: list[str] | None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", help="Staged file paths (from pre-commit pass_filenames)")
    args = parser.parse_args(argv)

    token = snyk_token()
    if not token:
        return 0  # no token configured — silent no-op

    targets = _filter_paths(args.paths)
    if not targets:
        return 0

    result = run_scan(targets, token=token, timeout=60.0)

    if result.status is ScanStatus.ERROR:
        print(f"snyk-agent-scan: skipped ({result.error})")
        return 0
    if result.status is ScanStatus.SKIP:
        return 0

    print(summarize(result))
    for finding in result.findings:
        print(f"  [{finding.severity}] {finding.code}: {finding.path} — {finding.message}")

    enforce = os.environ.get("SNYK_AGENT_SCAN_ENFORCE") == "1"
    high_critical = result.severity_counts.get("Critical", 0) + result.severity_counts.get("High", 0)
    if enforce and high_critical > 0:
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    # A pre-commit hook must never hard-crash a commit on an unexpected scanner
    # or parsing bug — always fail open.
    try:
        return _run(argv)
    except Exception as exc:
        print(f"snyk-agent-scan: skipped (unexpected error: {exc})")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
