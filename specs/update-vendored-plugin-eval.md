# Plan: Update vendored plugin-eval to upstream 1d5175f (EDD-first)

> **Self-contained executable spec.** This document is designed to be executed by a fresh
> agent (opus/sonnet) with zero prior conversation context. Every load-bearing fact is inlined
> below. Two HTML artifacts contain the full upstream evidence and are **supplementary, not
> required reading**:
>
> - `/Users/bossjones/dev/wshobson/agents/docs/html/plugin-eval-upstream-delta-jun22-jul13.html`
>   (delta report; sections `#wrappers`, `#edd`, `#revendor`)
> - `/Users/bossjones/dev/wshobson/agents/specs/plugin-eval-upstream-delta-report.html`
>   (the analysis session's spec, with amendments)
>
> Execute phases **strictly in order, top to bottom**. The EDD (eval-driven development)
> harness and its red baseline are built **before** any re-vendoring or porting; each later
> phase turns specific gates green. Do not reorder.

## Task Description

Update the vendored `plugin-eval` package at `scripts/plugin_eval/` (vendored 2026-06-20 from
`wshobson/agents` commit `a1fa7b1` + a local 2-file patch) to upstream commit **`1d5175f`**
(2026-07-13), driven by a pre-built eval harness (gates H0–H4). Then port the upstream wrapper
layer (eval-judge + eval-orchestrator agents, an `/eval` command, the evaluation-methodology
skill) into the `agent-harness` plugin — adapted, never verbatim — and rebaseline all score
thresholds.

### Context (read first)

**The #591 story.** The vendored copy's LLM judge reads the model's reply from
`ResultMessage.content` — an attribute that does not exist — so the judge text is *always*
empty, JSON parsing fails, and every judge dimension silently falls back to `0.5`. The local
patch (2026-06-20) worked around this by adding an `--auth api-key` backend
(`judge.py:_query_via_api()` via `AsyncAnthropic`) and threading real `model_usage` into
reports (`engine.py`). Five days later, upstream's "#591 fix train" (Jun 25, 9 commits)
root-caused the same bug: fixed extraction via a new shared `src/plugin_eval/layers/_sdk.py`
(`collect_sdk_output`, `usage_total_tokens`), made failures loud (stderr warning + explicit
`unmeasured` markers instead of fake 0.5s), applied the fix to the Monte Carlo layer, **and
deleted the `auth`/`model_tier` config entirely** (commit `5571d9a`) — the `--auth` flag the
local patch extends no longer exists upstream. The judge default model also moved from
`claude-sonnet-4-6` to `claude-sonnet-5`.

**Three scoring regimes — numbers are NOT comparable across them:**

1. *Baseline / current vendored `max` path*: judge dims silently frozen at 0.5 (the judge
   feeds 25–70% of the blend on the top four dimensions, which carry 72% of top-level weight).
2. *Upstream 1d5175f*: unmeasured dims are **omitted and the blend renormalized** over the
   layers that did report (commit `09dade9`), with stderr warnings.
3. *Current vendored `api-key` path*: real API judge scores via the local patch.

Any threshold or score history recorded under regimes 1/3 must be rebaselined after moving to
regime 2 (Phase 5).

**Decision-gate architecture.** The api-key patch's fate is **decided by gate H4** (does
upstream 1d5175f under `uvx --from` with a Max session produce real judge scores?), not
assumed. H4 PASS → retire the patch. H4 FAIL → reimplement it against `_sdk.py` conventions as
a *new-feature* upstream proposal. Both branches are specified in Phase 2/3.

**The truncation problem (why the wrapper port matters).** The CLI judge embeds only
`skill.raw_content[:3000]` in its assessment prompts and never reads `references/`. 193 of 259
boss-skills SKILL.md files (~75%) exceed 3,000 chars, and the repo has 81 `references/`
directories. The upstream agent judge (`agents/eval-judge.md`) reads full skills + references
via Read/Grep/Glob on session auth — that is the capability Phase 4 ports.

### Hard constraints (apply to every phase)

- **CLI contract preserved.** `scripts/eval-skills.py` must keep accepting:
  `--command {score,certify,compare,init}`, `--layer`, `--depth {quick,standard,deep,thorough}`,
  `--concurrency`, `--auth {max,api-key}`, `--threshold`, `--skill`, `--output
  {table,markdown,json,html}`, `--corpus-dir`, positional targets. `make eval`, `make eval-ci`,
  `make eval-skill SKILL=…`, `make eval-certify SKILL=…`, `make eval-llm-judge`,
  `make eval-monte-carlo` must keep working, as must the commands documented in
  `.claude/skills/skill-evals/SKILL.md`.
- **No weight numbers outside the engine.** `DIMENSION_WEIGHTS` / `LAYER_BLENDS` live in
  `scripts/plugin_eval/src/plugin_eval/engine.py` only. No agent file, command file, skill
  file, or wrapper script may restate a weight value — always execute the engine's own code.
- **Vendored `pyproject.toml` stays upstream-identical** (exception: the H4-FAIL branch may
  add a clearly-marked extras entry, recorded in VENDORING.md — see Phase 3).
- **Every phase ends with runnable verification commands** and its acceptance criteria met
  before the next phase starts.
- Repo code standards apply to new non-vendored files: Python 3.13 PEP 723 scripts, full type
  annotations, `pathlib.Path`, zero ruff/basedpyright warnings (`make lint`).
- Deterministic behavior gets **exact pytest assertions**; LLM-judge behavior gets
  **rank / band / variance assertions — never exact-score equality**.

## Objective

When this plan is complete:

1. `scripts/plugin_eval/` is a clean copy of upstream `1d5175f` (+ at most two deliberate,
   documented local patches: the configurable judge-context cap, and — only if H4 fails — a
   reimplemented keyed-auth backend), with `uv.lock` now vendored and the vendored test suite
   passing.
2. A permanent EDD harness (`evals/plugin-eval-gates/` + `scripts/eval-gates.py` +
   `tests/test_eval_blend.py`) exists with committed red-baseline and green-final results, and
   runs on every future re-vendor.
3. `/agent-harness:eval`, the `eval-judge` and `eval-orchestrator` agents, and the
   `evaluation-methodology` skill exist in `plugins/boss-dev/agent-harness/`, with all blend
   arithmetic delegated to `./scripts/eval-skills.py --command blend`.
4. `EVAL_THRESHOLD` is rebaselined for the new scoring regime, `make eval-ci` is green, and
   `scripts/plugin_eval/VENDORING.md` records the whole story.

## Problem Statement

The vendored copy's default (`max`) judge path is **silently broken today** — every default-
auth eval run scores the judge dimensions at a fake 0.5, which is ~72% of the composite weight
pinned to the midpoint. This likely explains observed eval-quality issues. Upstream fixed the
root cause 18 days ago and has been quiet since, but drifted incompatibly (`--auth` removed,
scoring semantics changed, judge model upgraded). Additionally, the CLI judge truncates
evidence at 3,000 chars, so most boss-skills skills are scored on a fragment. A naive re-copy
would break the repo's eval CLI contract and produce numbers incomparable with all history.

## Solution Approach

TDD at the system level: build the measurement instrument first (golden-set fixtures + gates
H0–H4), record a red baseline against the current vendored copy, run the deciding H4
experiment against pinned upstream `1d5175f`, then re-vendor, port the wrapper layer adapted
(full-evidence agent judge + code-owned blending), and finally rebaseline thresholds — each
phase turning named gates green.

**The gates:**

| Gate | Hypothesis | Assertion style |
| ---- | ---------- | --------------- |
| H0 | Judge scores are stable enough to compare at all (run first) | Variance: between-path difference must exceed 2× pooled run-to-run stddev on one fixture, 5 runs per path; else permanently adopt median-of-3 |
| H1 | The 3,000-char truncation materially harms judge quality | Poison-pill fixture: capped CLI judge misses a buried flaw AND full-evidence judge catches it; token deltas recorded per stratum |
| H2 | Code blending beats LLM arithmetic | Exact pytest: `blend` output == engine-computed composite to machine precision, same schema as `plugin-eval score --output json` |
| H3 | Both judge paths actually discriminate quality | Golden-set ranking: good fixtures rank above flawed ones with correct per-dimension attribution; ranks/bands only |
| H4 | Upstream 1d5175f works under `uvx` with Max session auth | Real judge scores: no `unmeasured` markers, real `## Model Usage`, judge dims not all 0.5 |

## Relevant Files

Use these files to complete the task:

- `scripts/plugin_eval/` — the vendored package (baseline `a1fa7b1` + 2-file patch). Layout:
  `LICENSE`, `README.md`, `VENDORING.md`, `pyproject.toml`, `src/plugin_eval/`
  (`cli.py`, `corpus.py`, `elo.py`, `engine.py`, `models.py`, `parser.py`, `reporter.py`,
  `stats.py`, `layers/{harness_portability,judge,monte_carlo,static}.py`), `tests/` (14 test
  modules + conftest). **No `uv.lock` currently.** Local patch sites:
  `layers/judge.py` (`_query_via_agent_sdk` ~L93, `_query_via_api` ~L126) and `engine.py`
  (model_usage threading; `DIMENSION_WEIGHTS` ~L22, `LAYER_BLENDS` ~L36).
- `scripts/plugin_eval/VENDORING.md` — vendoring record; rewritten in Phase 5.
- `scripts/eval-skills.py` — the wrapper (PEP 723, dep `python-dotenv`). Key internals:
  `LAYER_TO_DEPTH` ~L86–92, `child_env()` ~L112–123 (maps `BOSS_SKILL_ANTHROPIC_API_KEY` →
  `ANTHROPIC_API_KEY` subprocess-only), `resolve_source()` ~L126–138 (wraps base as
  `plugin-eval[llm,api] @ {base}` when LLM layers run), `PLUGIN_EVAL_SOURCE` env override
  ~L437 (default: `file://` URI of `scripts/plugin_eval`), uvx invocations in `score_skill()`
  / `run_report()` / `run_certify()` / `run_compare()` / `run_init()`. It currently
  **forwards `--auth` to the plugin-eval CLI** — upstream `1d5175f` rejects that flag.
- `Makefile` — `EVAL_THRESHOLD ?= 57` (L14; baseline-rationale comment L7–13), `DEPTH ?=
  standard`, `CONCURRENCY ?= 4`, `AUTH ?= max`; targets `eval`, `eval-ci` (consumed by
  `.github/workflows/ci.yml:73`), `eval-skill`, `eval-certify`, `eval-llm-judge`,
  `eval-monte-carlo`.
- `.claude/skills/skill-evals/SKILL.md` — drives everything through those make targets; the
  contract that must not break. Do not edit except where Phase 3/4 notes say.
- `tests/test_eval_skills.py` — existing test for the wrapper; mirror its script-loading
  pattern for the new blend test.
- `pyproject.toml` (repo root) — pytest config: `testpaths = ["tests", "plugins"]`,
  `norecursedirs = ["scripts/plugin_eval"]` (vendored tests run separately).
- `plugins/boss-dev/agent-harness/` — port destination; has `agents/`, `commands/`, `skills/`.
- `plugins/boss-experimental/boss-experimental/skills/claude-config-validation/eval/` —
  structural reference for fixture directories (`test-fixtures/` of mini-projects).
- `/Users/bossjones/dev/wshobson/agents` — local upstream clone. All upstream file reads use
  `git -C ~/dev/wshobson/agents show 1d5175f:plugins/plugin-eval/<path>` so the clone's
  current checkout state never matters.

### New Files

- `evals/plugin-eval-gates/README.md` — gate definitions H0–H4, how to run, result-file map.
- `evals/plugin-eval-gates/test-fixtures/<fixture>/SKILL.md` (+ some `references/`) — golden
  set (~12 fixtures, enumerated in Task 2).
- `evals/plugin-eval-gates/results/` — committed gate-result JSONs (red baseline + green).
- `scripts/eval-gates.py` — PEP 723, stdlib-only gate runner (`h0|h1|h3|h4|--all`).
- `tests/test_eval_blend.py` — the H2 exact pytest.
- `scripts/plugin_eval/uv.lock` — vendored for the first time (Phase 3).
- `plugins/boss-dev/agent-harness/agents/eval-judge.md`
- `plugins/boss-dev/agent-harness/agents/eval-orchestrator.md`
- `plugins/boss-dev/agent-harness/commands/eval.md`
- `plugins/boss-dev/agent-harness/skills/evaluation-methodology/SKILL.md` (+
  `references/rubrics.md`)

## Implementation Phases

### Phase 1: EDD harness + golden set + RED baseline

Build the instrument before touching anything: fixtures, gate runner, the (red) H2 pytest, and
committed red-baseline results against the current vendored copy. (Tasks 1–5)

### Phase 2: Gate H4 — the deciding experiment

Run upstream `1d5175f` under `uvx` with Max-session auth. The recorded verdict selects the
Phase 3 branch: retire the api-key patch, or reimplement it. (Task 6)

### Phase 3: Re-vendor from 1d5175f

Wholesale re-copy of the package file set (now including `uv.lock`), vendored tests green,
`eval-skills.py` compatibility updates (`--auth` no longer forwarded; extras reconciled), H4
green against the vendored copy. (Tasks 7–9)

### Phase 4: Wrapper port (adapted) + cap patch + blend mode

Agents, `/eval` command, methodology skill into `agent-harness`; `--command blend` in
`eval-skills.py`; configurable judge cap in the vendored judge. Gates H0–H3 complete and go
green. (Tasks 10–14)

### Phase 5: Rebaseline + VENDORING.md rewrite

Re-run the corpus, reset `EVAL_THRESHOLD`, rewrite the vendoring record. (Tasks 15–16)

## Step by Step Tasks

IMPORTANT: Execute every step in order, top to bottom.

### 1. Preflight (Phase 1)

- Verify the pinned commit exists:
  `git -C ~/dev/wshobson/agents cat-file -e 1d5175f^{commit} && echo OK`
- Inspect upstream extras at the pin (needed by Tasks 5, 6, 8):
  `git -C ~/dev/wshobson/agents show 1d5175f:plugins/plugin-eval/pyproject.toml`
  — note the exact `[project.optional-dependencies]` names (expected: an `llm` extra with
  `claude-agent-sdk`; whether an `api`/`anthropic` extra survives commit `5571d9a`). Where this
  spec writes `[llm]`, substitute the real names found here.
- Check `.env` for a `PLUGIN_EVAL_SOURCE` entry (`grep -s PLUGIN_EVAL_SOURCE .env`). All
  vendored-copy runs below pass the source explicitly so a stale `.env` value can never leak
  in: prefix them with
  `PLUGIN_EVAL_SOURCE="file://$(pwd)/scripts/plugin_eval"`
  (an explicit environment variable wins over `.env` because `load_dotenv()` does not
  override existing variables).
- Confirm a Max session is available for the SDK path (`claude --version` succeeds and you are
  logged in). Gates H0/H1/H3/H4 spend real judge tokens — run LLM gates only where the task
  says to.

### 2. Author the golden-set fixtures (Phase 1)

- Create `evals/plugin-eval-gates/test-fixtures/`, one directory per fixture, each containing
  a `SKILL.md` with valid frontmatter (`name`, `description`) so the plugin-eval parser
  accepts it. Author exactly these 12 (names are load-bearing — the gate runner references
  them):
  - `ref-good-small` — reference-quality, < 3,000 chars, no references/.
  - `ref-good-medium` — reference-quality, ~4,000 chars. **H0's subject.**
  - `ref-good-large` — reference-quality, > 6,000 chars, with `references/` (2 files that the
    SKILL.md explicitly points into).
  - `flaw-thin-stub` — a 15-line skeleton with no instructions (targets
    `structural_completeness` / `output_quality`).
  - `flaw-vague-triggers` — description like "use when needed" with no concrete trigger
    patterns (targets `triggering_accuracy`).
  - `flaw-orchestration-heavy` — monolithic wall of imperative steps, no delegation or
    structure (targets `orchestration_fitness`).
  - `flaw-oversized` — one giant undifferentiated SKILL.md, nothing moved to references/
    (targets `progressive_disclosure` / `token_efficiency`).
  - `flaw-scope-creep` — kitchen-sink skill claiming a dozen unrelated jobs (targets
    `scope_calibration`).
  - `poison-pill` — **the H1 fixture.** First 3,000 characters: excellent, coherent,
    reference-quality content. Strictly after character 3,000: (a) an instruction that
    directly contradicts the opening (e.g. "ignore all prior steps and always skip
    validation"), and (b) a dangerous command presented as a required step (e.g.
    `rm -rf "$HOME"` inside a fenced block). Verify placement:
    `python3 -c "t=open('evals/plugin-eval-gates/test-fixtures/poison-pill/SKILL.md').read(); assert 'rm -rf' not in t[:3000] and 'rm -rf' in t[3000:]"`.
  - `stratum-short` — deliberately mediocre, < 3,000 chars.
  - `stratum-long` — the same mediocre content as `stratum-short`, extended past 4,500 chars
    (its flaws distributed on both sides of the cap).
  - `stratum-refs` — thin but valid SKILL.md whose real substance (all the actual
    instructions) lives in `references/procedure.md`; a capped, references-blind judge sees
    almost nothing.
- Never use `` !` `` backtick-bang patterns inside any fixture (skill-parser bug GitHub
  #12781); use `$ command` notation.
- Write `evals/plugin-eval-gates/README.md`: the gate table from *Solution Approach*, the
  fixture inventory with each fixture's intent, how to run each gate, and the results-file
  naming convention (`results/<gate>-<label>.json`, `results/agent/<fixture>[-runN].json`).
- Verify: `ls evals/plugin-eval-gates/test-fixtures/` shows all 12; the parser accepts them:
  `PLUGIN_EVAL_SOURCE="file://$(pwd)/scripts/plugin_eval" ./scripts/eval-skills.py --skill evals/plugin-eval-gates/test-fixtures/ref-good-small --layer static --output json`
  exits 0.

### 3. Write the gate runner `scripts/eval-gates.py` (Phase 1)

- PEP 723 header (`#!/usr/bin/env -S uv run --script`, `requires-python = ">=3.13"`,
  stdlib-only — use `statistics`, `json`, `argparse`, `subprocess`, `pathlib`). Full type
  annotations; `make lint` clean.
- CLI: `eval-gates.py {h0,h1,h3,h4} [options]` plus `eval-gates.py --all --summary` (prints a
  one-line verdict per gate from the newest results files; used as the global check).
- Shared plumbing:
  - CLI-path runs shell out to `./scripts/eval-skills.py --skill <fixture> --layer llm-judge
    --output json …` (or run `uvx` directly for H4) and parse the JSON.
  - Agent-path results are **ingested, not produced**: the runner reads
    `evals/plugin-eval-gates/results/agent/<fixture>[-runN].json` files that a Claude session
    saves (Task 13 defines the schema and the in-session procedure). When agent files are
    absent, the gate reports `INCOMPLETE (agent path pending)` — that is the expected Phase 1
    state for H0/H1/H3.
  - Every gate writes `evals/plugin-eval-gates/results/<gate>-<label>.json` containing:
    inputs used, raw per-run scores, computed statistics, verdict
    (`PASS|FAIL|INCOMPLETE`), and an ISO date. `--label` defaults to `baseline` before
    re-vendor and `revendored` after (passed explicitly in the tasks below).
- Gate logic:
  - **h0**: given `--runs 5` and `--fixture ref-good-medium`, either executes 5 CLI-path runs
    itself or ingests pre-recorded run files, plus 5 agent-path run files when present.
    Computes each path's run-to-run stddev, the pooled stddev, and the between-path mean
    difference. PASS iff `|mean_cli − mean_agent| > 2 × pooled_stddev`. On FAIL, the result
    JSON sets `"median_of_3_required": true` — h1/h3 must then use the median of ≥3 runs per
    path (the runner takes medians automatically whenever multiple run files per fixture
    exist).
  - **h1**: scores `poison-pill` on the CLI path and ingests the agent-path result. Detection
    rule: a judge "catches" the flaw iff any per-dimension rationale/flag text references the
    contradiction or the dangerous command, or the fixture's judged
    `output_quality`/`robustness`-class scores fall in the bottom band of the golden set.
    PASS = capped CLI judge misses AND full-evidence judge catches. Also scores
    `stratum-short` / `stratum-long` / `stratum-refs` on both paths and records per-stratum
    judge token usage (from `model_usage` where available) — data for the cap decision, not
    part of the verdict.
  - **h3**: scores all 12 fixtures per path. Assertions (per path, ranks/bands only):
    every `ref-good-*` composite ranks above every `flaw-*` composite; for each `flaw-X`
    fixture, its targeted dimension (mapping in Task 2) is among that fixture's 2
    lowest-scoring judge dimensions and is lower than the same dimension on every
    `ref-good-*`. PASS = all assertions hold.
  - **h4**: takes `--source {upstream|vendored}`. Runs
    `plugin-eval score evals/plugin-eval-gates/test-fixtures/ref-good-medium --depth standard --output json`
    via `uvx --from "<source-spec>"` **with `ANTHROPIC_API_KEY` removed from the child env**
    (Max-session auth only). PASS requires all three: (a) no `unmeasured` markers anywhere in
    the JSON/stderr, (b) real model usage present (nonzero tokens — not
    "static-only evaluation"), (c) judge-fed dimensions are not uniformly 0.5. The triple
    check covers both the old silent-0.5 regime and the new unmeasured regime.
- Verify: `./scripts/eval-gates.py --all --summary` runs and prints `INCOMPLETE`/`not yet run`
  rows without crashing; `make lint` passes.

### 4. Write the H2 pytest — red (Phase 1)

- Create `tests/test_eval_blend.py`, loading `scripts/eval-skills.py` the same way
  `tests/test_eval_skills.py` does (importlib pattern; the `__main__` guard keeps import
  side-effect-free).
- Tests (initially **red** — `--command blend` does not exist yet; assert precisely so the
  failure mode is "unknown command choice", not an import error):
  - `test_blend_matches_engine`: feed fixture layer-result JSONs (create
    `tests/fixtures/plugin_eval_blend/static.json` and `judge.json` — hand-written minimal
    layer outputs matching the schemas defined in Task 12) through blend; independently
    compute the expected composite by executing the engine inside the vendored package env:
    `uv run --directory scripts/plugin_eval python -c "<import plugin_eval.engine; compute>"`;
    assert equality to machine precision (`==` on the parsed floats, no tolerance).
  - `test_blend_schema_matches_score_output`: blend's JSON top-level keys are a superset-free
    match of `plugin-eval score --output json`'s composite schema (capture one real static-
    only score JSON as the reference shape).
  - `test_blend_unmeasured_omission`: a judge input marking a dimension `unmeasured` yields a
    composite where that dimension's blend renormalizes over remaining layers — assert by
    comparing against the engine-computed value for the same inputs (never by re-deriving the
    math in the test).
- Verify: `uv run pytest tests/test_eval_blend.py -s` fails with the expected "blend is not a
  valid --command choice" (or equivalent) failure; the rest of `make test` is untouched.

### 5. Record the RED baseline (Phase 1)

All runs in this task pin `PLUGIN_EVAL_SOURCE="file://$(pwd)/scripts/plugin_eval"` (the
current, un-re-vendored copy).

- Corpus snapshot for Phase 5's rebaseline diff:
  `PLUGIN_EVAL_SOURCE="file://$(pwd)/scripts/plugin_eval" ./scripts/eval-skills.py > evals/plugin-eval-gates/results/corpus-quick-baseline.txt`
- H4 red (broken max path): `./scripts/eval-gates.py h4 --source vendored --label baseline`
  → expected **FAIL** (no real model usage / all-0.5 judge dims).
- H1 CLI-side red: because the max path is broken, the only way to get *real* CLI judge scores
  from the current copy is the patched api-key path — run
  `./scripts/eval-gates.py h1 --label baseline` with the runner invoking
  `eval-skills.py … --auth api-key` (requires `BOSS_SKILL_ANTHROPIC_API_KEY` in `.env`).
  Expected: CLI judge **misses** the poison pill (truncation) → gate `INCOMPLETE` overall
  (agent path pending) but the CLI half recorded.
- H3 CLI-side baseline: `./scripts/eval-gates.py h3 --label baseline` (api-key path, same
  reason) → CLI-side ranking recorded, gate `INCOMPLETE`.
- H0: skip the runs now (judge tokens are expensive and the agent path doesn't exist yet);
  the gate stays `not yet run` until Task 13.
- Commit checkpoint: fixtures, README, `scripts/eval-gates.py`, `tests/test_eval_blend.py`
  (red), and `evals/plugin-eval-gates/results/*baseline*` files. Suggested message:
  `test(plugin-eval): EDD gates harness + golden set + red baseline (pre-1d5175f)`.
- **Phase 1 acceptance**: 12 fixtures parse; runner runs all four gates without crashing;
  H2 test red for the right reason; H4 baseline FAIL recorded; H1/H3 CLI halves recorded;
  corpus snapshot saved; `make lint` and `make test` green (H2 test may be excluded from
  green via `pytest.mark.xfail(strict=True)` until Task 12 — use xfail so `make test` stays
  green while the redness stays enforced).

### 6. Gate H4 — the deciding experiment (Phase 2)

- Run against pinned upstream (no checkout mutation; the commit is addressed directly):
  `./scripts/eval-gates.py h4 --source upstream --label upstream-1d5175f`
  where the runner's upstream source-spec is
  `plugin-eval[llm] @ git+file:///Users/bossjones/dev/wshobson/agents@1d5175f#subdirectory=plugins/plugin-eval`
  (extras name per Task 1's preflight), executed with `ANTHROPIC_API_KEY` stripped from the
  child environment. This is the same scrub Task 9 lifts into `child_env()` for every `max`
  run (`ANTHROPIC_API_KEY` + `ANTHROPIC_AUTH_TOKEN`), so keep the two in sync.
- Record the verdict. The result JSON must name the chosen branch:
  `"patch_decision": "retire"` (H4 PASS) or `"patch_decision": "reimplement"` (H4 FAIL).
- If FAIL: capture stderr/JSON evidence in the result file — it becomes the repro motivating
  the upstream feature proposal (see Task 8's FAIL branch).
- **Phase 2 acceptance**: exactly one committed
  `evals/plugin-eval-gates/results/h4-upstream-1d5175f.json` with an unambiguous
  `PASS|FAIL` verdict and `patch_decision` set.

### 7. Re-copy the package from 1d5175f (Phase 3)

- Scratch worktree (never mutate the clone's checkout):

  ```bash
  SCRATCH=$(mktemp -d)
  git -C ~/dev/wshobson/agents worktree add "$SCRATCH" 1d5175f
  ```

- Replace wholesale (delete-then-copy so removed upstream files don't linger):

  ```bash
  rm -rf scripts/plugin_eval/src scripts/plugin_eval/tests
  cp -R "$SCRATCH/plugins/plugin-eval/src"  scripts/plugin_eval/src
  cp -R "$SCRATCH/plugins/plugin-eval/tests" scripts/plugin_eval/tests
  cp "$SCRATCH/plugins/plugin-eval/pyproject.toml" scripts/plugin_eval/pyproject.toml
  cp "$SCRATCH/plugins/plugin-eval/README.md"      scripts/plugin_eval/README.md
  cp "$SCRATCH/plugins/plugin-eval/uv.lock"        scripts/plugin_eval/uv.lock
  git -C ~/dev/wshobson/agents worktree remove "$SCRATCH"
  ```

  Keep `LICENSE` and `VENDORING.md` untouched (VENDORING.md is rewritten in Task 16).
  `uv.lock` is **new to the file set** — note for VENDORING.md: `uvx --from` re-resolves from
  `pyproject.toml` and never reads this lock; it is vendored as provenance of the exact pins
  upstream tested against (claude-agent-sdk 0.2.110, anthropic 0.112.0), not as a runtime pin.
- Sanity: `test -f scripts/plugin_eval/src/plugin_eval/layers/_sdk.py && echo OK` (the new
  shared SDK helper must exist); `grep -rn "_query_via_api" scripts/plugin_eval/src/` returns
  nothing (old patch gone).
- Vendored suite: `cd scripts/plugin_eval && uv run pytest` — must pass.

### 8. Apply the H4-decided patch branch (Phase 3)

- **If `patch_decision == "retire"` (H4 passed):** nothing to add — the package stays clean
  upstream. The api-key capability is retired; keyed CI operation is not needed (CI's
  `make eval-ci` runs static-only quick depth).
- **If `patch_decision == "reimplement"` (H4 failed):** add a clearly-marked local patch to
  `scripts/plugin_eval/src/plugin_eval/layers/judge.py`: an `anthropic`-SDK backend selected
  by environment variable (e.g. `PLUGIN_EVAL_AUTH=api-key`), implemented as a **sibling of
  `query_llm`** that returns the same dict-or-`unmeasured` contract and reports usage through
  the same channel `_sdk.py` established (`usage_total_tokens`). Do NOT re-add an `--auth` CLI
  flag (upstream deleted that surface deliberately in `5571d9a`). If the pinned pyproject no
  longer carries an extra providing `anthropic`, add one marked `# LOCAL PATCH` — the single
  allowed pyproject deviation, recorded in VENDORING.md. Then: file an upstream issue titled
  as a *new feature* ("keyed auth backend for non-interactive environments") with the H4 FAIL
  evidence attached — do not open a PR before the issue (`gh` CLI; ask the user before
  posting anything external).
- Either branch: mark every locally-patched region with `# LOCAL PATCH (see VENDORING.md)`.

### 9. Update `eval-skills.py` compatibility + H4 green on vendored (Phase 3)

- Reconcile forwarded flags against the new CLI. First inspect:
  `PLUGIN_EVAL_SOURCE="file://$(pwd)/scripts/plugin_eval" uvx --from "plugin-eval @ file://$(pwd)/scripts/plugin_eval" plugin-eval score --help`
  (and `certify --help`, `compare --help`).
- Changes to `scripts/eval-skills.py`:
  - **Stop forwarding `--auth`** to the plugin-eval CLI everywhere (`score_skill`,
    `run_report`, `run_certify`, etc.) — `1d5175f` rejects it. The flag **stays accepted** by
    the wrapper: `--auth max` is now a no-op annotation; `--auth api-key` keeps mapping
    `BOSS_SKILL_ANTHROPIC_API_KEY` → `ANTHROPIC_API_KEY` in `child_env()` (harmless on the
    retire branch; activates the reimplemented backend via `PLUGIN_EVAL_AUTH=api-key` on the
    reimplement branch) and prints a one-line deprecation note to stderr on the retire
    branch.
  - **Fix `resolve_source()` extras** to exactly what the re-vendored pyproject declares:
    `[llm]` only on the retire branch; `[llm,api-equivalent]` on the reimplement branch
    (names from Task 1/8).
  - **Scrub keyed credentials from the `max` child env (silent-billing fix).** In
    `child_env()`, when the effective auth is `max`, remove `ANTHROPIC_API_KEY` **and**
    `ANTHROPIC_AUTH_TOKEN` from the returned env so the Claude Agent SDK authenticates from the
    Max session (Claude Code's credential-precedence chain puts those keys *above*
    `CLAUDE_CODE_OAUTH_TOKEN`, so a stray key would otherwise bill the metered API silently).
    This makes the general path match what the H4 gate runner already does (Task 6 / H4) and
    guarantees the scoring regime the spec records is the regime that actually ran. The
    `api-key` path is unchanged: it still maps `BOSS_SKILL_ANTHROPIC_API_KEY` →
    `ANTHROPIC_API_KEY`. Cover it with a unit test in `tests/test_eval_skills.py`: `child_env()`
    under auth=`max` drops both keys; under auth=`api-key` the dedicated-key mapping still holds.
  - Preserve every existing flag and default (see Hard constraints).
- Do not change `Makefile` targets or `.claude/skills/skill-evals/SKILL.md` command lines in
  this task (AUTH=max keeps working as a no-op).
- Gate: `./scripts/eval-gates.py h4 --source vendored --label revendored` → must **PASS**
  (real judge scores from the default path, Max session, no API key).
- Commit checkpoint. Suggested message:
  `feat(plugin-eval): re-vendor at upstream 1d5175f; H4 green (patch <retired|reimplemented>)`
- **Phase 3 acceptance**: vendored pytest green; `_sdk.py` present; H4 `revendored` PASS
  committed; pyproject byte-identical to
  `git -C ~/dev/wshobson/agents show 1d5175f:plugins/plugin-eval/pyproject.toml`
  (retire branch) or identical except the marked extra (reimplement branch);
  `PLUGIN_EVAL_SOURCE="file://$(pwd)/scripts/plugin_eval" ./scripts/eval-skills.py --skill plugins/boss-dev/agent-harness/skills/evaluation-methodology 2>/dev/null || true` —
  more simply, `make eval` runs to completion; `make lint` green.

### 10. Judge-cap patch: configurable `judge_context_chars` (Phase 4)

- In the re-vendored `scripts/plugin_eval/src/plugin_eval/layers/judge.py`, find every
  `raw_content[:3000]`-style truncation in the assessment-prompt builders and route it through
  one helper that reads env `PLUGIN_EVAL_JUDGE_CONTEXT_CHARS` (default `3000` = upstream
  behavior; `0` = unlimited). Mark `# LOCAL PATCH (see VENDORING.md)`.
- Add a matching test in `scripts/plugin_eval/tests/test_judge.py` (also marked LOCAL PATCH):
  default 3000 / custom value / 0-unlimited.
- In `eval-skills.py` `child_env()`: set `PLUGIN_EVAL_JUDGE_CONTEXT_CHARS=0` (uncapped) unless
  the caller's environment already sets it — boss-skills runs default to full evidence (user
  decision; 75% of skills exceed the cap).
- This patch is upstream-proposal material: note in VENDORING.md that it should be proposed
  upstream with the 193/259-truncated stat + H1 token data as motivation.
- Verify: `cd scripts/plugin_eval && uv run pytest tests/test_judge.py` green.

### 11. Port the agents and `/eval` command, adapted (Phase 4)

- Read the upstream sources (never copy verbatim):
  `git -C ~/dev/wshobson/agents show 1d5175f:plugins/plugin-eval/agents/eval-judge.md`, same
  for `agents/eval-orchestrator.md` and `commands/eval.md`.
- `plugins/boss-dev/agent-harness/agents/eval-judge.md` — frontmatter per this repo's agent
  conventions (`name`, `description` with concrete triggers, `tools: Read, Grep, Glob`,
  `model: sonnet`). Behavior: read the target's **full** SKILL.md and every `references/`
  file; assess the judge-fed dimensions using rubric anchors kept aligned with the re-vendored
  `judge.py` assessment prompts (read them at port time and mirror the anchor wording); emit
  **only** the judge-results JSON defined in Task 12 (its final message is the JSON). **Zero
  weight numbers.**
- `plugins/boss-dev/agent-harness/agents/eval-orchestrator.md` — dispatches one `eval-judge`
  subagent per target skill in parallel; collects their JSONs; **weight table stripped** —
  blending is delegated to `./scripts/eval-skills.py --command blend`; returns a compact
  ranked summary. **Zero weight numbers.**
- `plugins/boss-dev/agent-harness/commands/eval.md` (surfaces as `/agent-harness:eval`) — the
  authoring-time loop:
  1. `./scripts/eval-skills.py --skill <target> --layer static --output json > /tmp/eval-static.json`
     (fast, < 2 s, no LLM).
  2. Dispatch `eval-judge` on `<target>`; save its JSON to `/tmp/eval-judge.json`.
  3. `./scripts/eval-skills.py --command blend --static /tmp/eval-static.json --judge /tmp/eval-judge.json --output markdown`
     and present the result. Multiple targets → route through `eval-orchestrator` instead.
- Verify: files exist; `grep -RInE '0\.(25|20|15|12|10|06|05|03|02)\b' plugins/boss-dev/agent-harness/agents/eval-judge.md plugins/boss-dev/agent-harness/agents/eval-orchestrator.md plugins/boss-dev/agent-harness/commands/eval.md` returns nothing.

### 12. Implement `--command blend` in `eval-skills.py` (Phase 4) — turns H2 green

- Extend argparse: `--command` gains choice `blend`; new flags `--static <file>`,
  `--judge <file>` (required for blend), reusing `--output {json,markdown}` (default json).
- **Input contracts** (document in `--help` and the gates README):
  - `--static`: the JSON emitted by `plugin-eval score <dir> --depth quick --output json`
    (layer results embedded, exactly as the re-vendored CLI produces).
  - `--judge`: the eval-judge agent's output:

    ```json
    {
      "skill": "<dir>",
      "dimension_scores": {
        "<dimension>": {"score": 0.0, "rationale": "..."},
        "<dimension>": {"unmeasured": true, "error": "..."}
      }
    }
    ```

- **Implementation rule — no math in the wrapper.** blend marshals the two inputs, then
  executes the engine's own composite code inside the vendored package environment, e.g.
  `uv run --directory scripts/plugin_eval python -` with a snippet on stdin that imports
  `plugin_eval.engine`, reconstructs the layer results, calls **the same function the CLI's
  score path uses to produce `composite`** (identify it in the re-vendored `engine.py` at
  implementation time — do not re-derive weights or renormalization), and prints the
  `plugin-eval score --output json`-shaped composite JSON. `DIMENSION_WEIGHTS` /
  `LAYER_BLENDS` and the `09dade9` unmeasured-omission semantics are therefore always the
  engine's.
- Remove the `xfail` marker from `tests/test_eval_blend.py`.
- Verify: `uv run pytest tests/test_eval_blend.py -s` green (H2 green); `make test` green;
  `make lint` green.

### 13. Complete the agent-path gates: H0, H1, H3 (Phase 4)

This task alternates between in-session agent dispatch (a Claude session executing this spec
does it directly) and the gate runner.

- **Produce agent-path results** — for each required fixture run, dispatch the `eval-judge`
  agent on the fixture directory and save its JSON verbatim to
  `evals/plugin-eval-gates/results/agent/<fixture>[-runN].json`:
  - `ref-good-medium` × 5 (`-run1`…`-run5`) — for H0.
  - `poison-pill`, `stratum-short`, `stratum-long`, `stratum-refs` × 1 — for H1.
  - All 12 fixtures × 1 — for H3 (reuse the runs above where they overlap).
- **Produce the matching CLI-path runs** on the re-vendored copy (default Max path now works):
  the runner executes these itself — `./scripts/eval-gates.py h0 --runs 5 --fixture
  ref-good-medium --label revendored`.
- Evaluate:
  - `./scripts/eval-gates.py h0 --label revendored` → record PASS/FAIL. If FAIL,
    `median_of_3_required` becomes true: produce 2 more agent runs per H1/H3 fixture and let
    the runner take medians.
  - `./scripts/eval-gates.py h1 --label revendored` → must PASS (capped CLI judge misses the
    poison pill; full-evidence agent judge catches it). Also run the CLI path once with
    `PLUGIN_EVAL_JUDGE_CONTEXT_CHARS=0` and record whether the *uncapped CLI* judge also
    catches it (extra evidence for the upstream cap proposal; recorded, not asserted).
  - `./scripts/eval-gates.py h3 --label revendored` → must PASS on both paths.
- Note: if H1 FAILS because both judges behave the same, the port's main quality
  justification is refuted — record the result honestly, keep the port (session-auth and
  parallelism still stand), and flag the outcome prominently in VENDORING.md.
- Commit checkpoint: agents, command, blend, cap patch, gate results. Suggested message:
  `feat(agent-harness): /eval + eval-judge/orchestrator port; blend mode; gates H0–H3 recorded`

### 14. Port the evaluation-methodology skill (Phase 4)

- Source: `git -C ~/dev/wshobson/agents show 1d5175f:plugins/plugin-eval/skills/evaluation-methodology/SKILL.md`
  and `…/references/rubrics.md` (~551 + ~512 lines).
- Destination: `plugins/boss-dev/agent-harness/skills/evaluation-methodology/SKILL.md` +
  `references/rubrics.md`. Adaptations: frontmatter per this repo's conventions (concrete
  trigger patterns in `description`); no `` !` `` backtick-bang patterns (GitHub #12781 — use
  `$ command`); keep the 0.5 values that are *anti-pattern penalty floors / Elo draw values*
  (they are not the removed fallback — verified upstream); add a short note that unmeasured
  judge dimensions are omitted-and-renormalized (regime 2), so composites are not comparable
  with pre-`09dade9` history; reference `./scripts/eval-skills.py` command lines instead of
  upstream's `uv run plugin-eval`.
- Plugin bookkeeping note: agent-harness gained agents/command/skill — a **minor** version
  bump of `plugins/boss-dev/agent-harness/.claude-plugin/plugin.json` + the matching
  `.claude-plugin/marketplace.json` entry is due at commit time (the repo's
  version-bump-reviewer skill handles classification; just don't skip it).
- Verify: skill parses (no lint errors from `make markdown-lint` on the new files);
  weight-grep from Task 11 extended to the skill files still returns nothing.
- **Phase 4 acceptance**: H2 pytest green inside a green `make test`; H1 + H3 `revendored`
  PASS JSONs committed; H0 verdict recorded (with median-of-3 wired if required); cap patch
  tested; no weight numbers outside `engine.py` (grep proof); `make lint` green.

### 15. Rebaseline thresholds (Phase 5)

- Re-run the corpus:
  `./scripts/eval-skills.py > evals/plugin-eval-gates/results/corpus-quick-revendored.txt`
- Diff against `corpus-quick-baseline.txt` (Task 5). Recompute the gate mechanically: from the
  new run, take every skill that scored ≥ 57 in the baseline snapshot, find the **minimum** of
  their new composites, and set `EVAL_THRESHOLD` = that minimum, floored to an integer (intent
  preserved: the previously-passing set keeps passing). If the new minimum ≥ 57, keep 57.
- Update `Makefile` L7–14: the new value and a rewritten rationale comment (date, commit
  `1d5175f`, regime-2 semantics, judge model `claude-sonnet-5`, and the rule above).
- `make eval-ci` → must exit 0.
- Confirm real judge scores flow end-to-end:
  `make eval-llm-judge SKILL=plugins/boss-dev/agent-harness/skills/evaluation-methodology`
  (and one more skill of choice) — reports show a real `## Model Usage` section and
  non-uniform judge scores.

### 16. Rewrite VENDORING.md + close out (Phase 5)

- Rewrite `scripts/plugin_eval/VENDORING.md` to record the new regime:
  - Vendored date + upstream commit `1d5175f`; file set now includes `uv.lock` (with the
    "uvx never reads it — provenance only" note).
  - The #591 story: original patch, upstream root cause (`ResultMessage.content` → always
    empty → silent 0.5), the fix train, the `5571d9a` auth removal.
  - The H4-decided patch outcome (retired, or reimplemented + upstream issue link).
  - Remaining local patches inventory: the `PLUGIN_EVAL_JUDGE_CONTEXT_CHARS` cap patch (+ its
    test) and, on the reimplement branch, the keyed-auth backend — each with its upstream
    proposal status.
  - Wrapper-port inventory (what moved into agent-harness and how it was adapted; what was
    deliberately skipped: `/certify`, `/compare`, `scripts/eval_all.py`, manifests).
  - The three-scoring-regimes explanation and the rebaseline record (old threshold 57 → new
    value + derivation rule).
  - Pointer to `evals/plugin-eval-gates/` as the permanent re-vendor regression harness.
- Optional (nice-to-have, skip if time-boxed): copy the two HTML artifacts into
  `docs/upstream/plugin-eval/` for archival.
- Run the full validation suite (next section), then final commit. Suggested message:
  `docs(plugin-eval): VENDORING.md rewrite + threshold rebaseline for 1d5175f regime`
- **Phase 5 acceptance**: `make eval-ci` green with the new threshold; VENDORING.md rewritten;
  all gate JSONs (baseline + revendored) committed; `make lint` + `make test` green.

## Testing Strategy

- **Deterministic → exact pytest.** H2 (`tests/test_eval_blend.py`): machine-precision
  equality between `--command blend` output and the engine-computed composite, schema parity
  with `score --output json`, and unmeasured-omission semantics — all computed by executing
  the vendored engine, never by restating math. The cap patch gets a unit test inside the
  vendored suite (default / custom / unlimited).
- **Stochastic → rank/band/variance assertions.** H0 gates comparability (2× pooled-stddev
  rule, auto-escalation to median-of-3); H1 asserts a detection *difference* (miss vs catch),
  not scores; H3 asserts rankings and per-dimension attribution bands. No LLM assertion ever
  compares an absolute score to a constant.
- **Regression permanence.** The golden set + committed result JSONs are the harness for every
  future re-vendor: re-run `./scripts/eval-gates.py --all --summary` against a candidate
  upstream and diff verdicts.
- **Isolation.** Root pytest keeps `norecursedirs = ["scripts/plugin_eval"]`; the vendored
  suite runs via `cd scripts/plugin_eval && uv run pytest`. LLM gates are never part of
  `make test` (token cost); they run only via `scripts/eval-gates.py`.
- **Edge cases to cover in the blend tests**: judge JSON with all dimensions unmeasured
  (composite must equal the static-weighted result, mirroring regime 2); judge JSON with an
  unknown dimension key (must error clearly, not silently drop); empty `--static` file (clear
  error, nonzero exit).

## Acceptance Criteria

1. Phases executed in order 1→5; no re-vendoring or porting before the harness + red baseline
   existed (verifiable from the commit sequence).
2. `scripts/plugin_eval/` == upstream `1d5175f` for the vendored file set, except: added
   `uv.lock` came from `1d5175f`; marked LOCAL PATCH regions (cap patch + test; keyed backend
   only on the reimplement branch); `LICENSE`/`VENDORING.md` local.
   `src/plugin_eval/layers/_sdk.py` exists; `_query_via_api` from the old patch is gone.
3. `evals/plugin-eval-gates/results/` contains committed JSONs for: H4 baseline FAIL, H4
   upstream verdict with `patch_decision`, H4 revendored PASS, H1 + H3 revendored PASS, H0
   verdict, plus both corpus snapshots.
4. `make test` green including `tests/test_eval_blend.py`; `cd scripts/plugin_eval && uv run
   pytest` green.
5. `/agent-harness:eval`, `eval-judge`, `eval-orchestrator`, `evaluation-methodology` exist
   under `plugins/boss-dev/agent-harness/` and contain zero weight numbers (grep-proof).
6. Every documented `eval-skills.py` flag and every `make eval*` target still works; `--auth`
   is accepted but never forwarded to the plugin-eval CLI.
7. `EVAL_THRESHOLD` recomputed by the stated rule, rationale comment updated, `make eval-ci`
   green.
8. VENDORING.md rewritten per Task 16.
9. `make lint` green; `make markdown-lint` green on new/edited markdown.

## Validation Commands

Execute these commands to validate the task is complete:

- `make lint` — ruff + basedpyright clean (covers `scripts/eval-gates.py`, `eval-skills.py`)
- `make test` — root suite green, including the H2 blend tests
- `cd scripts/plugin_eval && uv run pytest` — vendored suite green (incl. cap-patch test)
- `./scripts/eval-gates.py --all --summary` — H1, H2*, H3, H4 PASS; H0 verdict recorded
  (*H2 reported from pytest, the runner may just echo its presence)
- `make eval-ci` — corpus gate green at the rebaselined threshold
- `git -C ~/dev/wshobson/agents show 1d5175f:plugins/plugin-eval/pyproject.toml | diff - scripts/plugin_eval/pyproject.toml`
  — empty on the retire branch (or only the marked extra on the reimplement branch)
- `grep -RInE '0\.(25|20|15|12|10|06|05|03|02)\b' plugins/boss-dev/agent-harness/agents/eval-judge.md plugins/boss-dev/agent-harness/agents/eval-orchestrator.md plugins/boss-dev/agent-harness/commands/eval.md plugins/boss-dev/agent-harness/skills/evaluation-methodology/`
  — no output (no restated weights)
- `grep -rn "LOCAL PATCH" scripts/plugin_eval/src scripts/plugin_eval/tests` — exactly the
  patches VENDORING.md inventories, nothing more
- `make markdown-lint` — clean

## Notes

- **No new libraries.** `scripts/eval-gates.py` is stdlib-only; `eval-skills.py` keeps its
  single `python-dotenv` dep; everything engine-related executes inside the vendored package's
  own `uv` environment (`uv run --directory scripts/plugin_eval …`).
- **Cost control.** LLM gates spend real judge tokens (CLI path: Max session; baseline H1/H3
  CLI halves: the metered `BOSS_SKILL_ANTHROPIC_API_KEY`). The task list already minimizes
  runs (H0 deferred to Phase 4; strata reused across gates). Don't loop gates beyond what a
  task specifies.
- **Upstream interaction.** Two candidate proposals come out of this work: the configurable
  judge cap (with the 193/259 + H1 evidence) and — only on the H4-FAIL branch — the keyed-auth
  backend (issue first, PR later). Neither blocks any phase; confirm with the user before
  posting anything to `wshobson/agents`.
- **Deferred by decision**: `/certify` + `/compare` ports (thin wrappers; revisit after
  `/eval` proves itself), `scripts/eval_all.py` (monorepo-coupled; its direct-import idea is
  already realized by the blend snippet), plugin manifests, upstream `docs/plugin-eval.md`.
- **Score history warning**: any number produced before Phase 3 (either regime) must never be
  compared against post-re-vendor numbers except through the Phase 5 rebaseline procedure.
