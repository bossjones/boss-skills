#!/usr/bin/env -S uv run --script --quiet
# /// script
# requires-python = ">=3.13"
# dependencies = [
#   "pyyaml>=6.0.0",
#   "rich>=13.0.0",
# ]
# ///
"""
Validate SKILL.md files against the agent skills open standard best practices.

Recursively finds all SKILL.md files under a given directory and checks them
against 16 validation rules covering required fields, description quality,
structure, and known parser bugs.

Usage:
    ./scripts/skill_validation.py <directory>           # Normal mode
    ./scripts/skill_validation.py <directory> --strict   # Warnings fail

Exit codes:
    0 - All checks passed (warnings allowed in normal mode)
    1 - Validation errors found (or warnings in strict mode)
"""

from __future__ import annotations

import argparse
import contextlib
import dataclasses
import enum
import re
import sys
from pathlib import Path
from typing import Any

import yaml
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


class Level(enum.Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclasses.dataclass
class CheckResult:
    rule: str
    level: Level
    message: str


@dataclasses.dataclass
class FileReport:
    path: Path
    results: list[CheckResult] = dataclasses.field(default_factory=list)

    @property
    def errors(self) -> list[CheckResult]:
        return [r for r in self.results if r.level is Level.ERROR]

    @property
    def warnings(self) -> list[CheckResult]:
        return [r for r in self.results if r.level is Level.WARNING]

    @property
    def infos(self) -> list[CheckResult]:
        return [r for r in self.results if r.level is Level.INFO]


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

NAME_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")
MAX_NAME_LEN = 64
MAX_DESC_LEN = 1024
MAX_LINES = 500

KNOWN_TOOLS: frozenset[str] = frozenset(
    {
        "Bash",
        "Read",
        "Write",
        "Edit",
        "Glob",
        "Grep",
        "WebSearch",
        "WebFetch",
        "Agent",
        "TodoRead",
        "TodoWrite",
        "NotebookEdit",
        "TaskCreate",
        "TaskUpdate",
        "AskUserQuestion",
    }
)

VALID_MODELS: frozenset[str] = frozenset({"sonnet", "opus", "haiku"})

TRIGGER_KEYWORDS: tuple[str, ...] = (
    "use when",
    "trigger when",
    "activate when",
    "invoke when",
    "use this",
    "use for",
    "use to",
)

VAGUE_PHRASES: tuple[str, ...] = (
    "when needed",
    "as appropriate",
    "if necessary",
    "as required",
    "when applicable",
)


# ---------------------------------------------------------------------------
# Frontmatter parsing
# ---------------------------------------------------------------------------


def parse_frontmatter(text: str) -> tuple[dict[str, Any] | None, str, str | None]:
    """Parse YAML frontmatter delimited by --- markers.

    Returns:
        (frontmatter_dict, body_text, error_message_or_None)
    """
    stripped = text.lstrip("\n")
    if not stripped.startswith("---"):
        return None, text, "no YAML frontmatter found (missing opening ---)"

    end = stripped.find("---", 3)
    if end == -1:
        return None, text, "no closing --- for frontmatter"

    raw_fm = stripped[3:end]
    body = stripped[end + 3 :].lstrip("\n")

    try:
        fm = yaml.safe_load(raw_fm)
    except yaml.YAMLError as exc:
        return None, body, f"YAML parse error: {exc}"

    if not isinstance(fm, dict):
        return None, body, "frontmatter is not a YAML mapping"

    return fm, body, None


# ---------------------------------------------------------------------------
# Validation checks — pure functions, no I/O
# ---------------------------------------------------------------------------


def check_frontmatter_valid(
    _path: Path, fm: dict[str, Any] | None, _body: str, _lines: list[str], fm_error: str | None
) -> list[CheckResult]:
    """Rule 16: YAML frontmatter is valid and parseable."""
    if fm is None:
        return [CheckResult("frontmatter-valid", Level.ERROR, fm_error or "invalid frontmatter")]
    return []


def check_name(
    path: Path, fm: dict[str, Any] | None, _body: str, _lines: list[str]
) -> list[CheckResult]:
    """Rules 1-3: name exists, format valid, matches directory."""
    if fm is None:
        return []
    results: list[CheckResult] = []
    name = fm.get("name")

    if name is None:
        results.append(CheckResult("name-exists", Level.ERROR, "missing required field: name"))
        return results

    name = str(name)
    if not NAME_RE.match(name):
        results.append(
            CheckResult(
                "name-format",
                Level.ERROR,
                f"name '{name}' must be lowercase letters, numbers, and hyphens only",
            )
        )
    if len(name) > MAX_NAME_LEN:
        results.append(
            CheckResult(
                "name-length",
                Level.ERROR,
                f"name is {len(name)} chars, max {MAX_NAME_LEN}",
            )
        )

    dir_name = path.parent.name
    if name != dir_name:
        results.append(
            CheckResult(
                "name-matches-dir",
                Level.ERROR,
                f"name '{name}' does not match directory '{dir_name}'",
            )
        )

    return results


def check_description(
    _path: Path, fm: dict[str, Any] | None, _body: str, _lines: list[str]
) -> list[CheckResult]:
    """Rules 4-6: description exists, length, trigger keywords."""
    if fm is None:
        return []
    results: list[CheckResult] = []
    desc = fm.get("description")

    if desc is None:
        results.append(
            CheckResult("desc-exists", Level.ERROR, "missing required field: description")
        )
        return results

    desc = str(desc)
    if len(desc) > MAX_DESC_LEN:
        results.append(
            CheckResult(
                "desc-length",
                Level.ERROR,
                f"description is {len(desc)} chars, max {MAX_DESC_LEN}",
            )
        )

    desc_lower = desc.lower()
    has_trigger = any(kw in desc_lower for kw in TRIGGER_KEYWORDS)
    if not has_trigger:
        results.append(
            CheckResult(
                "desc-trigger",
                Level.WARNING,
                "description should indicate when to use this skill "
                "(e.g. 'Use when...', 'Use this to...')",
            )
        )

    return results


def check_optional_fields(
    _path: Path, fm: dict[str, Any] | None, _body: str, _lines: list[str]
) -> list[CheckResult]:
    """Rules 7-8: allowed-tools and model format."""
    if fm is None:
        return []
    results: list[CheckResult] = []

    allowed = fm.get("allowed-tools")
    if allowed is not None:
        tools = [t.strip() for t in str(allowed).split(",")]
        for tool in tools:
            if tool and tool not in KNOWN_TOOLS and not tool.startswith("mcp__"):
                results.append(
                    CheckResult(
                        "allowed-tools",
                        Level.WARNING,
                        f"unknown tool '{tool}' in allowed-tools",
                    )
                )

    model = fm.get("model")
    if model is not None and str(model) not in VALID_MODELS:
        results.append(
            CheckResult(
                "model-valid",
                Level.WARNING,
                f"model '{model}' not in {sorted(VALID_MODELS)}",
            )
        )

    return results


def check_description_quality(
    _path: Path, fm: dict[str, Any] | None, _body: str, _lines: list[str]
) -> list[CheckResult]:
    """Rule 9: description is not vague."""
    if fm is None:
        return []
    desc = fm.get("description")
    if desc is None:
        return []

    results: list[CheckResult] = []
    desc_lower = str(desc).lower()
    for phrase in VAGUE_PHRASES:
        idx = desc_lower.find(phrase)
        if idx == -1:
            continue
        after = desc_lower[idx + len(phrase) :]
        if len(after.strip()) < 10:
            results.append(
                CheckResult(
                    "desc-vague",
                    Level.WARNING,
                    f"description contains vague phrase '{phrase}' without specifics",
                )
            )
            break

    return results


def check_structure(
    path: Path, _fm: dict[str, Any] | None, _body: str, lines: list[str]
) -> list[CheckResult]:
    """Rules 10-11: line count and progressive disclosure."""
    results: list[CheckResult] = []
    count = len(lines)

    if count > MAX_LINES:
        results.append(
            CheckResult(
                "line-count",
                Level.WARNING,
                f"SKILL.md is {count} lines, recommended max {MAX_LINES}",
            )
        )
        skill_dir = path.parent
        has_subdirs = any((skill_dir / d).is_dir() for d in ("scripts", "references", "assets"))
        if not has_subdirs:
            results.append(
                CheckResult(
                    "progressive-disclosure",
                    Level.WARNING,
                    "over 500 lines with no scripts/, references/, or assets/ "
                    "— consider progressive disclosure",
                )
            )

    return results


def check_directory_conventions(
    path: Path, _fm: dict[str, Any] | None, _body: str, _lines: list[str]
) -> list[CheckResult]:
    """Rule 12: recommended subdirectories."""
    results: list[CheckResult] = []
    skill_dir = path.parent

    for subdir in ("scripts", "references", "assets"):
        if not (skill_dir / subdir).is_dir():
            results.append(
                CheckResult(
                    "dir-conventions",
                    Level.INFO,
                    f"no {subdir}/ directory (optional)",
                )
            )

    return results


def check_body_content(
    _path: Path, _fm: dict[str, Any] | None, body: str, _lines: list[str]
) -> list[CheckResult]:
    """Rules 13-14: instructions and example commands."""
    results: list[CheckResult] = []

    has_numbered = bool(re.search(r"^\d+\.", body, re.MULTILINE))
    has_headers = bool(re.search(r"^#{2,}\s", body, re.MULTILINE))
    if not has_numbered and not has_headers:
        results.append(
            CheckResult(
                "body-instructions",
                Level.WARNING,
                "no step-by-step instructions found (numbered lists or section headers)",
            )
        )

    has_code_block = "```" in body
    if not has_code_block:
        results.append(
            CheckResult(
                "body-examples",
                Level.WARNING,
                "no example code blocks found",
            )
        )

    return results


def check_backtick_bang(
    _path: Path, _fm: dict[str, Any] | None, body: str, _lines: list[str]
) -> list[CheckResult]:
    """Rule 15: no backtick-bang patterns in fenced code blocks (parser bug #12781)."""
    results: list[CheckResult] = []
    in_fence = False

    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence and re.search(r"`![^`]*`", line):
            results.append(
                CheckResult(
                    "backtick-bang",
                    Level.ERROR,
                    f"backtick-bang pattern in fenced code block (parser bug #12781): {line.strip()}",
                )
            )
            break

    return results


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

ALL_CHECKS = [
    check_name,
    check_description,
    check_optional_fields,
    check_description_quality,
    check_structure,
    check_directory_conventions,
    check_body_content,
    check_backtick_bang,
]


def validate_skill_file(path: Path) -> FileReport:
    """Run all validation checks on a single SKILL.md file."""
    report = FileReport(path=path)
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    fm, body, fm_error = parse_frontmatter(text)

    report.results.extend(check_frontmatter_valid(path, fm, body, lines, fm_error))
    for check_fn in ALL_CHECKS:
        report.results.extend(check_fn(path, fm, body, lines))

    return report


def find_skill_files(root: Path) -> list[Path]:
    """Recursively find all SKILL.md files under root."""
    return sorted(root.rglob("SKILL.md"))


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

LEVEL_STYLE: dict[Level, tuple[str, str]] = {
    Level.ERROR: ("bold red", "x"),
    Level.WARNING: ("yellow", "!"),
    Level.INFO: ("dim", "-"),
}


def print_file_report(report: FileReport) -> None:
    """Print per-file validation results."""
    rel: Path | str = report.path
    with contextlib.suppress(ValueError):
        rel = report.path.relative_to(Path.cwd())

    if not report.results:
        console.print(f"  [green]PASS[/green]  {rel}")
        return

    console.print(f"\n  [bold]{rel}[/bold]")
    for result in report.results:
        style, icon = LEVEL_STYLE[result.level]
        console.print(f"    [{style}][{icon}][/{style}] {result.rule}: {result.message}")


def print_summary(reports: list[FileReport], strict: bool) -> int:
    """Print summary table and return exit code."""
    console.print()
    table = Table(title="Skill Validation Summary")
    table.add_column("File", style="bold")
    table.add_column("Errors", justify="right", style="red")
    table.add_column("Warnings", justify="right", style="yellow")
    table.add_column("Info", justify="right", style="dim")
    table.add_column("Status", justify="center")

    total_errors = 0
    total_warnings = 0

    for report in reports:
        errors = len(report.errors)
        warnings = len(report.warnings)
        infos = len(report.infos)
        total_errors += errors
        total_warnings += warnings

        rel = str(report.path)
        with contextlib.suppress(ValueError):
            rel = str(report.path.relative_to(Path.cwd()))

        if errors:
            status = "[red]FAIL[/red]"
        elif warnings and strict:
            status = "[yellow]FAIL[/yellow]"
        elif warnings:
            status = "[yellow]WARN[/yellow]"
        else:
            status = "[green]PASS[/green]"

        table.add_row(rel, str(errors), str(warnings), str(infos), status)

    console.print(table)

    failed = total_errors > 0 or (strict and total_warnings > 0)

    if failed:
        msg = f"[red]FAILED[/red] — {total_errors} error(s), {total_warnings} warning(s)"
        if strict:
            msg += " (strict mode)"
        console.print(Panel.fit(msg, border_style="red"))
        return 1

    msg = f"[green]PASSED[/green] — {total_errors} error(s), {total_warnings} warning(s)"
    console.print(Panel.fit(msg, border_style="green"))
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    """Entry point."""
    parser = argparse.ArgumentParser(
        description="Validate SKILL.md files against best practices.",
    )
    parser.add_argument(
        "directory",
        type=Path,
        help="Root directory to search for SKILL.md files",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors (for CI/CD)",
    )
    args = parser.parse_args()

    root: Path = args.directory.resolve()
    if not root.is_dir():
        console.print(f"[red]Error:[/red] '{args.directory}' is not a directory")
        return 1

    skill_files = find_skill_files(root)
    if not skill_files:
        console.print(f"[yellow]No SKILL.md files found under {args.directory}[/yellow]")
        return 0

    console.print(
        Panel.fit(
            f"Validating {len(skill_files)} SKILL.md file(s) under [bold]{args.directory}[/bold]",
            border_style="blue",
        )
    )

    reports: list[FileReport] = []
    for skill_file in skill_files:
        report = validate_skill_file(skill_file)
        reports.append(report)
        print_file_report(report)

    return print_summary(reports, strict=args.strict)


if __name__ == "__main__":
    sys.exit(main())
