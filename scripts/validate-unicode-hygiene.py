#!/usr/bin/env -S uv run --script --quiet
# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///
"""Scan repository files for invisible or visually-spoofed Unicode.

Schema validators and human review both miss non-printing or visually-spoofed
Unicode. A malicious SKILL.md / plugin.json / agent / command file can carry an
invisible tag-character instruction or a bidi-reordered install command that
renders benign to a human reviewer but executes hostile when parsed by an LLM or
a shell. This script is the gate for that attack class.

Detection is Unicode-category based (NOT "any non-ASCII"), so the legitimate
em-dashes, arrows, emoji, and box-drawing already present in this repo's docs are
never flagged. Findings carry one of three severities:

- BLOCKER  invisible tag characters (U+E0000-U+E007F, the Socket "TrapDoor"
           vector) and bidirectional control characters (Trojan Source,
           CVE-2021-42574). These fail the default scan.
- MAJOR    other zero-width / format characters (Unicode category Cf), e.g.
           zero-width space. Reported but exit 0 by default; fails under --strict.
- MINOR    mixed-script (homoglyph) identifiers on install-command lines, e.g. a
           Cyrillic letter hidden inside ``pip install requests``. Never fails.

A leading BOM (U+FEFF at offset 0) is allowed.

Usage:
    uv run scripts/validate-unicode-hygiene.py                  # default targets
    uv run scripts/validate-unicode-hygiene.py path/to/file.md  # explicit paths
    uv run scripts/validate-unicode-hygiene.py --strict         # MAJOR also fails
    uv run scripts/validate-unicode-hygiene.py --warn-only      # never fails

Exit codes:
    0 - no BLOCKER findings (and no MAJOR under --strict)
    1 - at least one BLOCKER finding (or MAJOR under --strict)
"""

from __future__ import annotations

import argparse
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT: Path = Path(__file__).resolve().parent.parent

# File classes this repo publishes that an attacker would target. ``tests/fixtures/**``
# is deliberately excluded so a default full-repo scan never trips on the malicious
# fixtures committed for the test suite.
DEFAULT_TARGETS: tuple[str, ...] = (
    "plugins/**/SKILL.md",
    "plugins/**/.claude-plugin/plugin.json",
    "plugins/**/agents/*.md",
    "plugins/**/commands/*.md",
    ".claude-plugin/marketplace.json",
    ".claude/skills/**/SKILL.md",
    ".claude/commands/*.md",
)

# BLOCKER codepoint sets, fixed by the Unicode standard. The PreToolUse gate in
# plugins/boss-dev/agent-harness/hooks/pre_tool_use.py mirrors these two sets inline;
# this module is their canonical definition.
TAG_RANGE: range = range(0xE0000, 0xE0080)
BIDI_CONTROLS: frozenset[int] = frozenset({0x202A, 0x202B, 0x202C, 0x202D, 0x202E, 0x2066, 0x2067, 0x2068, 0x2069})
ALLOWED_BOM: int = 0xFEFF

# Lines that look like a package-install command; the homoglyph check is scoped to
# these so ordinary prose with decorative non-ASCII is never flagged.
INSTALL_RE: re.Pattern[str] = re.compile(
    r"\b(?:pip3?|pipx|uv|poetry|conda|npm|npx|yarn|pnpm|bun|gem|cargo|go|apt(?:-get)?"
    r"|brew|dnf|yum|nix|docker)\b[^\n]*?\b(?:install|add|get|i|pull)\b",
    re.IGNORECASE,
)
# Runs of letters only (no digits / underscore), Unicode-aware.
TOKEN_RE: re.Pattern[str] = re.compile(r"[^\W\d_]+")

SEVERITIES: tuple[str, ...] = ("BLOCKER", "MAJOR", "MINOR")


@dataclass(frozen=True)
class Finding:
    """A single detected issue in a scanned file."""

    path: Path
    severity: str
    category: str
    codepoint: int | None
    line: int
    col: int
    message: str


def _line_col(text: str, offset: int) -> tuple[int, int]:
    """Return the 1-based (line, column) for a character offset in ``text``."""
    line = text.count("\n", 0, offset) + 1
    col = offset - text.rfind("\n", 0, offset)
    return line, col


def _char_script(ch: str) -> str | None:
    """Return the Unicode script family (e.g. ``LATIN``, ``CYRILLIC``) of a letter."""
    try:
        name = unicodedata.name(ch)
    except ValueError:
        return None
    return name.split(" ", 1)[0]


def scan_invisibles(path: Path, text: str) -> list[Finding]:
    """Detect tag characters (BLOCKER), bidi controls (BLOCKER), and other format
    / zero-width characters (MAJOR). A leading BOM is allowed."""
    findings: list[Finding] = []
    for offset, ch in enumerate(text):
        codepoint = ord(ch)
        if codepoint in TAG_RANGE:
            line, col = _line_col(text, offset)
            findings.append(
                Finding(
                    path,
                    "BLOCKER",
                    "tag-character",
                    codepoint,
                    line,
                    col,
                    f"invisible Unicode tag character at offset {offset}",
                )
            )
        elif codepoint in BIDI_CONTROLS:
            line, col = _line_col(text, offset)
            findings.append(
                Finding(
                    path,
                    "BLOCKER",
                    "bidi-control",
                    codepoint,
                    line,
                    col,
                    f"bidirectional control character at offset {offset}",
                )
            )
        elif unicodedata.category(ch) == "Cf":
            if codepoint == ALLOWED_BOM and offset == 0:
                continue
            line, col = _line_col(text, offset)
            findings.append(
                Finding(
                    path,
                    "MAJOR",
                    "zero-width-or-format",
                    codepoint,
                    line,
                    col,
                    f"zero-width or format character at offset {offset}",
                )
            )
    return findings


def scan_homoglyphs(path: Path, text: str) -> list[Finding]:
    """Detect mixed-script (homoglyph) identifiers on install-command lines (MINOR)."""
    findings: list[Finding] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if not INSTALL_RE.search(line):
            continue
        for match in TOKEN_RE.finditer(line):
            token = match.group()
            scripts = {script for script in (_char_script(c) for c in token) if script}
            if len(scripts) < 2 or "LATIN" not in scripts:
                continue
            for index, char in enumerate(token):
                if _char_script(char) not in (None, "LATIN"):
                    findings.append(
                        Finding(
                            path,
                            "MINOR",
                            "mixed-script-identifier",
                            ord(char),
                            lineno,
                            match.start() + index + 1,
                            f"mixed-script token {token!r} (scripts: {', '.join(sorted(scripts))})",
                        )
                    )
                    break
    return findings


def scan_file(path: Path) -> list[Finding]:
    """Scan a single file, returning all findings. Unreadable / non-UTF-8 files are skipped."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    return scan_invisibles(path, text) + scan_homoglyphs(path, text)


def iter_default_files(repo_root: Path) -> list[Path]:
    """Resolve DEFAULT_TARGETS globs to a de-duplicated, sorted list of files."""
    seen: set[Path] = set()
    files: list[Path] = []
    for pattern in DEFAULT_TARGETS:
        for path in sorted(repo_root.glob(pattern)):
            if path.is_file() and path not in seen:
                seen.add(path)
                files.append(path)
    return files


def collect_explicit(paths: list[Path]) -> list[Path]:
    """Expand explicitly-passed paths (files kept as-is, directories walked)."""
    files: list[Path] = []
    for path in paths:
        if path.is_dir():
            files.extend(sorted(child for child in path.rglob("*") if child.is_file()))
        elif path.is_file():
            files.append(path)
    return files


def _display_path(path: Path) -> str:
    """Render ``path`` relative to the repo root when possible."""
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def format_finding(finding: Finding) -> str:
    """Render a finding as ``path:line:col: SEVERITY category U+XXXX message``."""
    codepoint = f"U+{finding.codepoint:04X}" if finding.codepoint is not None else "-"
    return (
        f"{_display_path(finding.path)}:{finding.line}:{finding.col}: "
        f"{finding.severity} {finding.category} {codepoint} {finding.message}"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Scan files for invisible or visually-spoofed Unicode.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("paths", nargs="*", type=Path, help="Files or directories to scan (default: repo target globs)")
    parser.add_argument("--strict", action="store_true", help="Treat MAJOR findings as failures too")
    parser.add_argument("--warn-only", action="store_true", help="Always exit 0 (report only)")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT, help="Repo root for default-target resolution")
    args = parser.parse_args(argv)

    files = collect_explicit(args.paths) if args.paths else iter_default_files(args.repo_root)

    findings: list[Finding] = []
    for path in files:
        findings.extend(scan_file(path))
    findings.sort(key=lambda f: (str(f.path), f.line, f.col))

    for finding in findings:
        print(format_finding(finding))

    counts = {severity: sum(1 for f in findings if f.severity == severity) for severity in SEVERITIES}
    print(
        f"Scanned {len(files)} file(s): {counts['BLOCKER']} BLOCKER, {counts['MAJOR']} MAJOR, {counts['MINOR']} MINOR"
    )

    if args.warn_only:
        return 0
    if counts["BLOCKER"] or (args.strict and counts["MAJOR"]):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
