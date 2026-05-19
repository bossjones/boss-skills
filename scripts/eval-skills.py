#!/usr/bin/env -S uv run --script --quiet
# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///
"""Quality-gate boss-skills skills with plugin-eval (static depth).

Discovers every directory containing a ``SKILL.md`` under ``plugins/``, runs
``plugin-eval score --depth quick`` against each via ``uvx`` (pulled on demand
from the wshobson/agents git subdirectory — nothing is vendored), prints a
score table, and exits non-zero if any skill scores below ``--threshold``.

Usage:
    scripts/eval-skills.py                         # report all skills, never fails
    scripts/eval-skills.py --threshold 60          # fail if any skill < 60
    scripts/eval-skills.py --skill plugins/.../foo  # single skill

Escape hatch (upstream churn): pin a specific revision without editing code by
setting PLUGIN_EVAL_SOURCE, e.g.
    PLUGIN_EVAL_SOURCE='git+https://github.com/wshobson/agents.git@<sha>#subdirectory=plugins/plugin-eval'
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

# Default: always-latest from the upstream marketplace repo, no vendoring.
DEFAULT_SOURCE = "git+https://github.com/wshobson/agents.git#subdirectory=plugins/plugin-eval"
REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGINS_DIR = REPO_ROOT / "plugins"


class SkillResult:
    """One skill's evaluation outcome."""

    def __init__(
        self,
        path: Path,
        score: float | None,
        badge: str,
        anti_patterns: int,
        error: str | None,
    ) -> None:
        self.path = path
        self.score = score
        self.badge = badge
        self.anti_patterns = anti_patterns
        self.error = error

    @property
    def rel(self) -> str:
        try:
            return str(self.path.relative_to(REPO_ROOT))
        except ValueError:
            return str(self.path)


def discover_skills() -> list[Path]:
    """Return sorted skill directories (parents of a SKILL.md) under plugins/."""
    return sorted({p.parent for p in PLUGINS_DIR.rglob("SKILL.md")})


def score_skill(skill_dir: Path, source: str) -> SkillResult:
    """Run plugin-eval at quick depth and parse the composite score."""
    cmd = [
        "uvx",
        "--from",
        source,
        "plugin-eval",
        "score",
        str(skill_dir),
        "--depth",
        "quick",
        "--output",
        "json",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)  # noqa: S603
    if proc.returncode != 0 and not proc.stdout.strip():
        detail = proc.stderr.strip().splitlines()
        return SkillResult(skill_dir, None, "-", 0, detail[-1] if detail else "plugin-eval failed")
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return SkillResult(skill_dir, None, "-", 0, "unparsable plugin-eval output")

    composite = data.get("composite", {})
    score = composite.get("score")
    badge = composite.get("badge") or "-"
    anti = sum(len(layer.get("anti_patterns", [])) for layer in data.get("layers", []))
    return SkillResult(skill_dir, score, badge, anti, None)


def print_table(results: list[SkillResult]) -> None:
    """Print an aligned score table."""
    width = max((len(r.rel) for r in results), default=20)
    header = f"{'SKILL':<{width}}  {'SCORE':>6}  {'BADGE':<9}  {'ANTI':>4}  STATUS"
    print(header)
    print("-" * len(header))
    for r in results:
        if r.error is not None:
            print(f"{r.rel:<{width}}  {'-':>6}  {'-':<9}  {'-':>4}  ERROR: {r.error}")
            continue
        score_txt = f"{r.score:.1f}" if r.score is not None else "-"
        print(f"{r.rel:<{width}}  {score_txt:>6}  {r.badge:<9}  {r.anti_patterns:>4}  ok")


def main() -> int:
    parser = argparse.ArgumentParser(description="Quality-gate skills with plugin-eval.")
    parser.add_argument(
        "--threshold",
        type=float,
        default=None,
        help="Minimum composite score; exit 1 if any skill is below it.",
    )
    parser.add_argument(
        "--skill",
        type=Path,
        default=None,
        help="Evaluate a single skill directory instead of discovering all.",
    )
    args = parser.parse_args()

    source = os.environ.get("PLUGIN_EVAL_SOURCE", DEFAULT_SOURCE)

    if args.skill is not None:
        skill_dir = args.skill if args.skill.is_absolute() else REPO_ROOT / args.skill
        if not (skill_dir / "SKILL.md").is_file():
            print(f"error: no SKILL.md in {skill_dir}", file=sys.stderr)
            return 2
        skills = [skill_dir.resolve()]
    else:
        skills = discover_skills()

    if not skills:
        print("No skills found under plugins/.", file=sys.stderr)
        return 2

    results = [score_skill(d, source) for d in skills]
    print_table(results)

    failures = [
        r
        for r in results
        if r.error is not None or (args.threshold is not None and r.score is not None and r.score < args.threshold)
    ]
    if args.threshold is not None and failures:
        print(
            f"\nFAIL: {len(failures)} skill(s) below threshold {args.threshold:.1f} or errored.",
            file=sys.stderr,
        )
        return 1
    if args.threshold is not None:
        print(f"\nPASS: all skills >= threshold {args.threshold:.1f}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
