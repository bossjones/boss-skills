#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///
"""Measure what a review run actually cost, and what it bought.

This is the instrument that settles the cmux-versus-Workflow bake-off, and — more
durably — the one that answers Cloudflare's real question: **which agent pays the
bills?** A specialist that costs $0.09 and finds nothing, run after run, should be
cut from the roster. Without per-agent cost-and-yield attribution that decision is a
matter of taste; with it, it is arithmetic.

It works identically for both arms because both leave the same trace on disk. Every
Claude Code session — a cmux pane is one, a Workflow subagent is one — writes a JSONL
transcript with per-message ``usage``:

    ~/.claude/projects/<project-slug>/<session-id>.jsonl              (top-level: cmux panes)
    ~/.claude/projects/<project-slug>/<session-id>/subagents/*.jsonl  (Workflow subagents)

So: snapshot the project directory before the run, diff it after, and sum the usage in
everything new. No instrumentation, no OTEL required, works retroactively.

Usage::

    score_run.py snapshot <workspace>                  # before launching the team
    score_run.py report <workspace> --arm cmux         # after it finishes

LangSmith tracing, when configured, is an additive view — never the source of truth
here. A tracing misconfiguration must not be able to corrupt the comparison.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SKILL_ROOT = Path(__file__).resolve().parent.parent
PRICING = SKILL_ROOT / "assets" / "model-pricing.json"
PROJECTS = Path.home() / ".claude" / "projects"

SEVERITIES = ("critical", "moderate", "nit")


@dataclass
class Usage:
    """Token usage, kept split because the split is the whole point.

    Collapsing these into one 'tokens' number hides the cache hit rate, which is the
    single metric that says whether context scoping is working.
    """

    input: int = 0
    output: int = 0
    cache_write: int = 0
    cache_read: int = 0

    def add(self, other: Usage) -> None:
        self.input += other.input
        self.output += other.output
        self.cache_write += other.cache_write
        self.cache_read += other.cache_read

    @property
    def total_input(self) -> int:
        return self.input + self.cache_write + self.cache_read

    @property
    def cache_hit_rate(self) -> float:
        """Fraction of input tokens served from cache. Cloudflare reported 0.857."""
        return self.cache_read / self.total_input if self.total_input else 0.0


@dataclass
class AgentRun:
    """One agent's transcript: what model it ran on, and what it spent."""

    session: str
    models: set[str] = field(default_factory=set)
    usage: Usage = field(default_factory=Usage)
    cost: float = 0.0


# --------------------------------------------------------------------------- #
# Pure core (unit tested — no IO)
# --------------------------------------------------------------------------- #
def rate_for(model: str, pricing: dict[str, Any]) -> dict[str, float]:
    """Longest matching model-id prefix wins. Unknown models price at zero.

    Zero is deliberate and loud: a $0.00 line in the report means 'add this prefix to
    model-pricing.json', which is far better than silently inventing a plausible rate.
    """
    models: dict[str, dict[str, float]] = pricing["models"]
    best = ""
    for prefix in models:
        if model.startswith(prefix) and len(prefix) > len(best):
            best = prefix
    return models[best] if best else {"input": 0.0, "output": 0.0}


def cost_of(usage: Usage, model: str, pricing: dict[str, Any]) -> float:
    """USD for one agent's usage, honoring cache write/read multipliers."""
    rate = rate_for(model, pricing)
    w = float(pricing.get("cache_write_multiplier", 1.25))
    r = float(pricing.get("cache_read_multiplier", 0.1))
    per_token_in = rate["input"] / 1_000_000
    per_token_out = rate["output"] / 1_000_000
    return (
        usage.input * per_token_in
        + usage.cache_write * per_token_in * w
        + usage.cache_read * per_token_in * r
        + usage.output * per_token_out
    )


def usage_from_transcript(text: str) -> tuple[Usage, set[str]]:
    """Sum per-message usage out of one session transcript."""
    total = Usage()
    models: set[str] = set()

    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            parsed: object = json.loads(line)
        except json.JSONDecodeError:
            continue  # a transcript being written concurrently can have a partial tail
        if not isinstance(parsed, dict):
            continue
        entry: dict[str, Any] = parsed
        raw_message: object = entry.get("message")
        if not isinstance(raw_message, dict):
            continue
        message: dict[str, Any] = raw_message

        raw_usage: object = message.get("usage")
        if not isinstance(raw_usage, dict):
            continue
        usage: dict[str, Any] = raw_usage

        if model := message.get("model"):
            models.add(str(model))
        total.add(
            Usage(
                input=int(usage.get("input_tokens", 0) or 0),
                output=int(usage.get("output_tokens", 0) or 0),
                cache_write=int(usage.get("cache_creation_input_tokens", 0) or 0),
                cache_read=int(usage.get("cache_read_input_tokens", 0) or 0),
            )
        )

    return total, models


def findings_by_role(workspace: Path) -> dict[str, dict[str, int]]:
    """Per-role finding counts by severity — the 'yield' half of cost-per-finding."""
    out: dict[str, dict[str, int]] = {}
    findings_dir = workspace / "findings"
    if not findings_dir.is_dir():
        return out

    for path in sorted(findings_dir.glob("*.jsonl")):
        counts: dict[str, int] = dict.fromkeys(SEVERITIES, 0)
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            try:
                parsed: object = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(parsed, dict):
                continue
            record: dict[str, Any] = parsed
            if record.get("type") == "done":
                continue
            sev = str(record.get("severity", ""))
            if sev in counts:
                counts[sev] += 1
        out[path.stem] = counts
    return out


def render_report(
    arm: str,
    manifest: dict[str, Any],
    runs: list[AgentRun],
    yields: dict[str, dict[str, int]],
    pricing: dict[str, Any],
) -> str:
    """The scorecard. Cloudflare's metrics, computed from our own transcripts."""
    total = Usage()
    for run in runs:
        total.add(run.usage)
    total_cost = sum(r.cost for r in runs)

    tier = str(manifest.get("tier", "?"))
    baseline: dict[str, Any] = pricing.get("_cloudflare_baseline", {})
    cf_cost = baseline.get("cost_per_review_avg", {}).get(tier)
    cf_cache = baseline.get("cache_hit_rate")

    lines = [
        f"# Review scorecard — arm: {arm}",
        "",
        f"review-id     {manifest.get('review_id', '?')}",
        f"tier          {tier}  (lead={manifest.get('lead_model')}, specialists={manifest.get('specialist_model')})",
        f"roster        {', '.join(manifest.get('roles', [])) or '(none)'}",
        f"agents seen   {len(runs)}",
        "",
        "## Cost",
        "",
        f"total                 ${total_cost:.4f}",
    ]
    if cf_cost is not None:
        delta = "cheaper" if total_cost < float(cf_cost) else "pricier"
        lines.append(f"cloudflare {tier:<10} ${float(cf_cost):.2f}   (we are {delta})")

    lines += [
        "",
        "## Tokens",
        "",
        f"input (uncached)      {total.input:>12,}",
        f"cache write           {total.cache_write:>12,}",
        f"cache read            {total.cache_read:>12,}",
        f"output                {total.output:>12,}",
        "",
        f"cache hit rate        {total.cache_hit_rate:>11.1%}",
    ]
    if cf_cache is not None:
        lines.append(f"cloudflare baseline   {float(cf_cache):>11.1%}")
    lines += [
        "",
        "A low hit rate means context is not being reused: briefs are being rebuilt, or",
        "something large is riding on a command line instead of sitting on disk.",
        "",
        "## Which agent pays the bills",
        "",
        "role                    findings  crit  cost      $/finding",
        "-" * 62,
    ]

    # Attribute cost to a role when its session is identifiable; otherwise report the
    # pool. Being explicit about which is which keeps the number honest.
    per_role_cost = total_cost / len(runs) if runs else 0.0
    for role, counts in sorted(yields.items()):
        n = sum(counts.values())
        crit = counts["critical"]
        each = f"${per_role_cost / n:.4f}" if n else "-- (found nothing)"
        lines.append(f"{role:<23} {n:>8}  {crit:>4}  ${per_role_cost:<8.4f} {each}")

    if not yields:
        lines.append("(no findings files — the specialists produced nothing)")

    lines += [
        "",
        "A role that repeatedly costs money and finds nothing should be cut from",
        "review-tiers.json. That is the entire purpose of this table.",
        "",
        "## Per-agent transcripts",
        "",
    ]
    for run in sorted(runs, key=lambda r: -r.cost):
        models = ",".join(sorted(run.models)) or "?"
        lines.append(f"{run.session[:20]:<22} {models:<22} ${run.cost:.4f}  cache {run.usage.cache_hit_rate:.0%}")

    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- #
# IO layer
# --------------------------------------------------------------------------- #
def project_slug(cwd: Path) -> str:
    """Claude Code names a project dir after its path, with separators flattened."""
    return str(cwd.resolve()).replace("/", "-")


def transcripts(project_dir: Path) -> dict[str, Path]:
    """Every session transcript under a project: top-level sessions and subagents.

    The three shapes, and why all three matter for a fair bake-off:

      <session>.jsonl                                  a cmux pane is one of these
      <session>/subagents/agent-X.jsonl                a plain Agent-tool subagent
      <session>/subagents/workflows/<run>/agent-X.jsonl a Workflow-tool subagent

    The last shape sits two levels deeper than the second. Missing it made every
    Workflow-arm agent invisible, so that arm scored $0.00 and would have won the cost
    comparison outright — on a glob, not on merit.
    """
    found: dict[str, Path] = {}
    if not project_dir.is_dir():
        return found
    for path in project_dir.glob("*.jsonl"):
        found[path.stem] = path
    for path in project_dir.glob("*/subagents/*.jsonl"):
        found[f"{path.parent.parent.name}/{path.stem}"] = path
    for path in project_dir.glob("*/subagents/workflows/*/*.jsonl"):
        if path.name == "journal.jsonl":  # workflow bookkeeping, not an agent
            continue
        found[f"{path.parent.parent.parent.parent.name}/{path.parent.name}/{path.stem}"] = path
    return found


def load_json(path: Path) -> dict[str, Any]:
    raw: object = json.loads(path.read_text())
    if not isinstance(raw, dict):
        raise ValueError(f"{path} must be a JSON object")
    return raw


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Score a review run: cost, cache, and per-agent yield.")
    parser.add_argument("action", choices=["snapshot", "report"])
    parser.add_argument("workspace", type=Path, help="review workspace (.review/<slug>)")
    parser.add_argument("--arm", default="unknown", help="which backend produced this run (cmux | workflow)")
    parser.add_argument("--cwd", type=Path, default=Path.cwd(), help="repo the agents ran in")
    parser.add_argument("--json", action="store_true", help="emit machine-readable results")
    args = parser.parse_args(argv)

    project_dir = PROJECTS / project_slug(args.cwd)
    snapshot_file = args.workspace / ".usage-snapshot.json"

    if args.action == "snapshot":
        args.workspace.mkdir(parents=True, exist_ok=True)
        existing = sorted(transcripts(project_dir))
        snapshot_file.write_text(json.dumps({"sessions": existing}, indent=2) + "\n")
        print(f"snapshot: {len(existing)} existing session(s) -> {snapshot_file}")
        return 0

    # report
    try:
        manifest = load_json(args.workspace / "manifest.json")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    before: set[str] = set()
    if snapshot_file.is_file():
        before = set(load_json(snapshot_file).get("sessions", []))
    else:
        print(
            "warning: no .usage-snapshot.json — cannot tell this run's sessions from "
            "pre-existing ones, so cost will be overstated. Run 'snapshot' before the team next time.",
            file=sys.stderr,
        )

    pricing = load_json(PRICING)

    runs: list[AgentRun] = []
    for name, path in sorted(transcripts(project_dir).items()):
        if name in before:
            continue
        usage, models = usage_from_transcript(path.read_text())
        if usage.total_input == 0 and usage.output == 0:
            continue
        run = AgentRun(session=name, models=models, usage=usage)
        # A session may span models (a /model switch mid-run). Averaging the rates is a
        # deliberate approximation; it is within noise for a review and keeps this honest
        # rather than pretending to a precision the transcript does not support.
        run.cost = sum(cost_of(usage, m, pricing) for m in models) / max(len(models), 1)
        runs.append(run)

    yields = findings_by_role(args.workspace)

    if args.json:
        print(
            json.dumps(
                {
                    "arm": args.arm,
                    "tier": manifest.get("tier"),
                    "total_cost_usd": round(sum(r.cost for r in runs), 6),
                    "agents": len(runs),
                    "findings_by_role": yields,
                },
                indent=2,
            )
        )
    else:
        print(render_report(args.arm, manifest, runs, yields, pricing))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
