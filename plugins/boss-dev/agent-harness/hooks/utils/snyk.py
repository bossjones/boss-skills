"""
Shared Snyk agent-scan helper for agent-harness hooks.

Wraps `uvx snyk-agent-scan@latest --json <targets...>` (or an injectable override for
tests) and turns its output into a small, defensively-parsed result. Scan targets are
restricted to `SKILL.md` files: empirical testing (2026-07) showed the scanner treats
any other markdown path (e.g. an `agents/*.md` or `commands/*.md` file) as an MCP JSON5
config file and fails to parse it — it produces a harmless per-target `parse_error`, not
a real security analysis, so those paths are never worth passing to the scanner.

Exit codes are intentionally never trusted: empirically, `snyk-agent-scan --json`
(without `--ci`) exits 0 even when High-risk findings are present. `--ci` does turn the
exit code into a real signal, but it requires `--dangerously-run-mcp-servers` even when
the only targets are plain `SKILL.md` files — a flag this integration must never pass
(scanning MCP server configs can launch stdio MCP servers). So gating here is driven
entirely by parsed `--json` severity, never `proc.returncode`.
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

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


def resolve_targets(root: Path) -> list[Path]:
    """Return SKILL.md files under `root`, excluding MCP configs and test fixtures."""
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
    """Parse `--json` stdout, tolerating leading log noise before the JSON body."""
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
    """Yield (root_result, issue) pairs from the real scan-result shape:
    `{"<root path>": {"issues": [...], "path": ..., "client": ..., ...}, ...}`.
    """
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
    if not targets:
        return ScanResult(status=ScanStatus.SKIP, error="no targets")
    if not token:
        return ScanResult(status=ScanStatus.SKIP, error="no SNYK_TOKEN")

    argv = [*_resolve_cmd(cmd_override), "--json", *(str(t) for t in targets)]
    env = {**os.environ, "SNYK_TOKEN": token}

    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, env=env, check=False)
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
