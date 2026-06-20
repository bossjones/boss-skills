#!/usr/bin/env -S uv run --script --quiet
# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///
"""Quality-gate boss-skills skills with plugin-eval.

Multi-mode wrapper around ``plugin-eval`` (pulled on demand via ``uvx`` from
the wshobson/agents git subdirectory — nothing is vendored).

``score`` (default) discovers every directory containing a ``SKILL.md`` under
``plugins/`` (or one ``--skill``), evaluates each, prints a score table, and
exits non-zero if any skill is below ``--threshold``. ``certify`` / ``compare``
/ ``init`` stream plugin-eval's native output for explicit positional targets.

``--layer`` is a friendly alias for plugin-eval's ``--depth``; pass ``--depth``
directly to bypass the alias (``--depth`` wins when both are given):

    layer                   depth      layers run                  cost
    static, static-analysis quick      static                      instant, free
    llm-judge               standard   static + judge              ~30s, 4 LLM calls
    monte-carlo             deep       static + judge + MC (50)    ~2-5 min
    all                     thorough   static + judge + MC (100)   slowest

``--concurrency`` (1-20, upstream default 4) caps plugin-eval's parallel LLM
calls; ``--auth`` (``max`` | ``api-key``, upstream default ``max``) picks the
judge backend — ``max`` needs Claude Code Max via ``claude-agent-sdk``, while
``api-key`` uses ``ANTHROPIC_API_KEY`` with the ``anthropic`` SDK. Both forward
to ``score``, ``certify``, and ``compare``.

Usage:
    scripts/eval-skills.py                              # report all skills, never fails
    scripts/eval-skills.py --threshold 60               # fail if any skill < 60
    scripts/eval-skills.py --skill plugins/.../foo      # single skill
    scripts/eval-skills.py --skill plugins/.../foo --layer llm-judge
    scripts/eval-skills.py --skill plugins/.../foo --depth deep --concurrency 8
    scripts/eval-skills.py --skill plugins/.../foo --auth api-key
    scripts/eval-skills.py --command certify plugins/.../foo --concurrency 8
    scripts/eval-skills.py --command compare plugins/.../a plugins/.../b
    scripts/eval-skills.py --command init plugins/

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

# Friendly --layer alias -> plugin-eval --depth.
LAYER_TO_DEPTH = {
    "static": "quick",
    "static-analysis": "quick",
    "llm-judge": "standard",
    "monte-carlo": "deep",
    "all": "thorough",
}

# plugin-eval --depth values (quick=static only; deeper adds judge then Monte Carlo).
DEPTHS = ("quick", "standard", "deep", "thorough")

# plugin-eval --auth values: max = Claude Code Max (claude-agent-sdk);
# api-key = ANTHROPIC_API_KEY via the anthropic SDK.
AUTH_MODES = ("max", "api-key")


def llm_flags(args: argparse.Namespace) -> list[str]:
    """Shared --concurrency/--auth passthrough, omitted when the user left them unset."""
    flags: list[str] = []
    if args.concurrency is not None:
        flags += ["--concurrency", str(args.concurrency)]
    if args.auth is not None:
        flags += ["--auth", args.auth]
    return flags


def resolve_source(base: str, needs_llm: bool) -> str:
    """uvx --from value; wrap a bare git/path source with the [llm] extra when needed."""
    if not needs_llm:
        return base
    # Already a PEP 508 spec (e.g. user-set PLUGIN_EVAL_SOURCE with extras): use as-is.
    if base.startswith("plugin-eval"):
        return base
    return f"plugin-eval[llm] @ {base}"


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


def score_skill(skill_dir: Path, source: str, depth: str, extra: list[str]) -> SkillResult:
    """Run plugin-eval at the given depth and parse the composite score."""
    cmd = [
        "uvx",
        "--from",
        source,
        "plugin-eval",
        "score",
        str(skill_dir),
        "--depth",
        depth,
        "--output",
        "json",
        *extra,
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


def run_passthrough(cmd: list[str]) -> int:
    """Run plugin-eval inheriting stdout/stderr; return its exit code."""
    return subprocess.run(cmd, check=False).returncode  # noqa: S603


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


def run_score(args: argparse.Namespace, source: str, depth: str) -> int:
    """Discover-or-single-skill scoring with the table + threshold gate."""
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

    extra = llm_flags(args)
    results = [score_skill(d, source, depth, extra) for d in skills]
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


def _resolve_target(p: Path) -> str:
    """Resolve a positional target relative to the repo root when not absolute."""
    return str(p if p.is_absolute() else REPO_ROOT / p)


def run_certify(args: argparse.Namespace, source: str) -> int:
    """Stream `plugin-eval certify` for exactly one target (always deep upstream)."""
    if len(args.targets) != 1:
        print(
            "error: --command certify requires exactly one target directory.",
            file=sys.stderr,
        )
        return 2
    cmd = [
        "uvx",
        "--from",
        source,
        "plugin-eval",
        "certify",
        _resolve_target(args.targets[0]),
        "--output",
        "markdown",
        *llm_flags(args),
    ]
    if args.threshold is not None:
        cmd += ["--threshold", str(args.threshold)]
    return run_passthrough(cmd)


def run_compare(args: argparse.Namespace, source: str, depth: str) -> int:
    """Stream `plugin-eval compare` for exactly two targets."""
    if len(args.targets) != 2:
        print(
            "error: --command compare requires exactly two target directories.",
            file=sys.stderr,
        )
        return 2
    cmd = [
        "uvx",
        "--from",
        source,
        "plugin-eval",
        "compare",
        _resolve_target(args.targets[0]),
        _resolve_target(args.targets[1]),
        "--depth",
        depth,
        "--output",
        "markdown",
        *llm_flags(args),
    ]
    return run_passthrough(cmd)


def run_init(args: argparse.Namespace, source: str) -> int:
    """Stream `plugin-eval init` to build a corpus index from one target directory."""
    if len(args.targets) != 1:
        print(
            "error: --command init requires exactly one plugins directory target.",
            file=sys.stderr,
        )
        return 2
    cmd = [
        "uvx",
        "--from",
        source,
        "plugin-eval",
        "init",
        _resolve_target(args.targets[0]),
    ]
    if args.corpus_dir is not None:
        cmd += ["--corpus-dir", str(args.corpus_dir)]
    return run_passthrough(cmd)


def main() -> int:
    parser = argparse.ArgumentParser(description="Quality-gate skills with plugin-eval.")
    parser.add_argument(
        "--command",
        choices=["score", "certify", "compare", "init"],
        default="score",
        help="plugin-eval subcommand to run (default: score).",
    )
    parser.add_argument(
        "--layer",
        choices=sorted(LAYER_TO_DEPTH),
        default="static",
        help="Evaluation layer alias for plugin-eval --depth (default: static). "
        "Ignored by certify (always deep upstream) and init.",
    )
    parser.add_argument(
        "--depth",
        choices=DEPTHS,
        default=None,
        help="plugin-eval evaluation depth; overrides --layer when set. "
        "Ignored by certify (always deep upstream) and init.",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=None,
        help="Max concurrent LLM calls passed to plugin-eval (1-20; upstream default 4).",
    )
    parser.add_argument(
        "--auth",
        choices=AUTH_MODES,
        default=None,
        help="plugin-eval judge backend: max (Claude Code Max) or api-key (ANTHROPIC_API_KEY). Upstream default: max.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=None,
        help="Minimum composite score; exit 1 if any skill is below it (score; also forwarded to certify).",
    )
    parser.add_argument(
        "--skill",
        type=Path,
        default=None,
        help="Evaluate a single skill directory instead of discovering all (score only).",
    )
    parser.add_argument(
        "--corpus-dir",
        type=Path,
        default=None,
        help="Where init stores the corpus index (default: plugin-eval's own default).",
    )
    parser.add_argument(
        "targets",
        nargs="*",
        type=Path,
        help="Positional target(s) for certify (1 dir), compare (2 dirs), init (1 dir).",
    )
    args = parser.parse_args()

    if args.concurrency is not None and not 1 <= args.concurrency <= 20:
        parser.error("--concurrency must be between 1 and 20")

    base = os.environ.get("PLUGIN_EVAL_SOURCE", DEFAULT_SOURCE)
    # Explicit --depth wins; otherwise fall back to the friendly --layer alias.
    depth = args.depth if args.depth is not None else LAYER_TO_DEPTH[args.layer]
    needs_llm = depth != "quick" or args.command == "certify"
    source = resolve_source(base, needs_llm)

    if args.command == "score":
        return run_score(args, source, depth)
    if args.command == "certify":
        return run_certify(args, source)
    if args.command == "compare":
        return run_compare(args, source, depth)
    return run_init(args, source)


if __name__ == "__main__":
    raise SystemExit(main())
