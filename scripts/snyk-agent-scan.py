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
import os
import re
import sys
from pathlib import Path
from typing import ClassVar

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass  # dotenv is optional

REPO_ROOT = Path(__file__).resolve().parent.parent
_PLUGIN_HOOKS_DIR = REPO_ROOT / "plugins" / "boss-dev" / "agent-harness" / "hooks"
sys.path.insert(0, str(_PLUGIN_HOOKS_DIR))
try:
    from utils.config import snyk_token  # pyright: ignore[reportMissingImports]
    from utils.snyk import ScanStatus, run_scan, summarize  # pyright: ignore[reportMissingImports]
except ImportError:
    # utils/ is missing or broken — fail closed rather than crash the commit.
    # The stubs below mirror the real API's attribute surface (not just its
    # names) so type-checking stays consistent whichever branch is resolved.
    class ScanStatus:  # type: ignore[no-redef]
        OK = object()
        SKIP = object()
        ERROR = object()

    class _FallbackFinding:
        severity: str = "Unknown"
        code: str | None = None
        path: str | None = None
        message: str | None = None

    class _FallbackScanResult:
        status: object = ScanStatus.ERROR
        error: str | None = "utils.snyk unavailable"
        findings: ClassVar[list[_FallbackFinding]] = []
        severity_counts: ClassVar[dict[str, int]] = {}

    def snyk_token() -> str:
        return (os.environ.get("CLAUDE_PLUGIN_OPTION_SNYK_TOKEN") or os.environ.get("SNYK_TOKEN") or "").strip()

    def run_scan(targets: list[Path], *, token: str, timeout: float = 60.0) -> _FallbackScanResult:
        del targets, token, timeout  # unreachable in practice — utils/ import failed
        return _FallbackScanResult()

    def summarize(result: object) -> str:
        del result
        return ""


TARGET_RE = re.compile(r"^(plugins/.+/skills/.+/SKILL\.md|\.claude/skills/.+/SKILL\.md)$")
EXCLUDE_NAMES = frozenset({"mcp.json", ".mcp.json"})


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
