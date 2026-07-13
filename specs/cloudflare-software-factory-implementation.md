# Plan: review-factory — a Cloudflare-style multi-agent code review factory

> **Status:** v2 — **part record, part plan.** The shared core and both execution arms are
> **built, tested, and green** (1114 tests, 0 lint errors, agent-harness at 0.29.0). The
> eval suites and the bake-off run itself are **not yet done**. Every section below is
> marked accordingly; nothing here describes work that does not exist.
>
> **v1 of this document (commit `ff5788a`) was written before the design interview and
> before any code, and is comprehensively wrong.** It survives in git if you want the
> archaeology. Do not act on it.

## Context

Cloudflare replaced the human-review bottleneck with a CI-triggered factory: a coordinator
spawns domain specialists, **scales compute to the risk of the change** (trivial/lite/full
tiers → $0.20/$0.67/$1.68 median per review), **scopes context aggressively** (per-file
patches + one shared context file on disk rather than N duplicated prompts, for an 85.7%
cache hit rate), runs a **judge pass** (dedupe → verify-uncertain-by-reading-source →
recategorize), and applies an **approval rubric biased toward approving**.

The design principles we adopted from the IndyDevDan critique: *agents + code, not agents
alone* (a deterministic pipeline; agents only where judgment is needed), *negative-scoped
prompts* ("What NOT to flag"), *JSONL everywhere* (crash-survivable), and *measure which
agent pays the bills*.

**What v1 got wrong, and why this document exists.** v1 pinned the runtime to cmux before
testing whether the pane machinery earned its keep. Roughly 40% of its plan — heartbeat
loops, md5 screen-diff stall probes, JSONL done-records, `--no-exec`, teardown, recovery —
existed solely to re-implement, on top of a terminal multiplexer, primitives this harness
already provides natively. Screen-scraping to detect "is the agent done" is the tell.

So instead of guessing, we **built both substrates and will let evidence choose.**

---

## Decisions

Eight decisions. **Four reversed from v1**, marked ⚠.

1. **Both review targets** — GitHub PR and local branch diff vs merge-base. *(Plus a third,
   new: `--diff-file` replay mode for hermetic runs.)*
2. **3 risk tiers** (trivial/lite/full) size the team; security-sensitive paths force Full.
3. ⚠ **Severity is `critical` / `moderate` / `nit`** — *not* v1's `critical/warning/suggestion`.
   The existing `pr-review/review-payload.schema.json` enforces this vocabulary, so adopting
   it means **zero schema change** and its validator is reused verbatim.
4. ⚠ **A bake-off, not one skill.** v1 planned a single `cmux-review-factory`. We built a
   shared deterministic core plus **two competing arms**; the winner is promoted, the loser
   deleted.
5. **Full-tier roster = 5 specialists**: security, code-quality, performance, docs,
   agent-instructions. Findings may carry a `suggestion_patch`, rendered as a one-click
   GitHub suggestion.
6. **The lead is a pure JUDGE, not a dispatcher.** Every specialist gets its complete task at
   spawn and runs independently. This deletes the #1 failure mode of past runs (idle lead →
   stalled workers) and matches Cloudflare, whose coordinator only consumes structured findings.
7. ⚠ **Re-review-lite deferred to v2.** It has zero bearing on which substrate wins, and it
   was the most complex thing on the critical path to a verdict.
8. ⚠ **The orchestrator posts, not the lead** — and only after an `AskUserQuestion` gate.
   `github-pr-review/SKILL.md:24` *mandates* explicit human approval before any post, which a
   headless pane cannot satisfy. It also makes double-posting impossible when running both
   arms against the same PR.

---

## The two constraints that forced the architecture

**Write this down or someone will undo it.**

- `pyproject.toml:82` sets `exclude = [".claude/", ...]` with **`force-exclude = true`**.
  Ruff therefore *never* lints or formats Python under `.claude/` — and `force-exclude` means
  even naming the path explicitly will not override it.
- Pytest's `testpaths = ["tests", "plugins"]`. Tests under `.claude/` are **never collected**.

Together: **Python under `.claude/skills/` escapes every quality gate this repo mandates.**

That is *why* the shared core is a plugin skill (linted, typed, tested) and only the two
disposable **markdown** playbooks live in `.claude/skills/`. If someone later "tidies" the
core into `.claude/` for symmetry, the tests and the linter silently stop running.

---

## As-built

### Layout

```text
plugins/boss-dev/agent-harness/skills/review-factory-core/   # SHARED, permanent, linted+tested
├── SKILL.md                       # disable-model-invocation: true — a library, not a playbook
├── assets/
│   ├── review-tiers.json          # tiers, security globs, roster, focus globs, boundary tags
│   ├── model-pricing.json         # USD/Mtok by model prefix + the Cloudflare baseline
│   └── roles/                     # security, code-quality, performance, docs,
│       └── *.md                   #   agent-instructions, generalist, judge
├── scripts/
│   ├── prepare_review.py          # the deterministic pipeline
│   ├── validate_findings.py       # the anchor gate
│   ├── score_run.py               # cost, cache hit rate, cost-per-finding per specialist
│   └── tests/                     # 57 tests
└── eval/graders/                  # check_manifest.py, check_no_injection.py

.claude/skills/review-factory-workflow/SKILL.md    # ARM B — Workflow-tool fan-out
.claude/skills/review-factory-cmux/SKILL.md        # ARM A — visible cmux panes
```

Both arms share the core, the role prompts, the judge, and the payload. **Only the substrate
differs** — that is what makes the comparison a fair test, and it is why neither arm's prompts
may be tuned without the other's.

### Pipeline

```text
prepare_review.py      -> .review/<slug>/   (code: tier, roster, briefs, patches, anchors)
   [ specialists ]     -> findings/*.jsonl  (agents: judgment)
validate_findings.py   -> rejects bad anchors BEFORE the judge sees them
   [ judge ]           -> review-payload.json (agent: judgment)
validate_review.py     -> schema gate (reused from pr-review, UNCHANGED)
   [ orchestrator ]    -> shows verdict, asks the human, posts
score_run.py           -> what it cost, and which agent paid the bills
```

### The workspace (`.review/<slug>/`)

| Artifact | What it is |
| :--- | :--- |
| `manifest.json` | tier, roster, models, HEAD SHA, focus map, and **every valid anchor** |
| `annotated.diff` | the full diff from `fetch-diff` — one annotator, all modes |
| `diff/*.patch` | per-file patches; a specialist reads only what it needs |
| `shared-context.md` | the author's intent, **boundary-tag stripped** |
| `briefs/<role>.md` | one complete, self-contained task per agent |
| `findings/` | each specialist writes exactly one JSONL file, and nothing else |

### Four properties the rest of the system depends on

- **Risk sizes the team.** A security-sensitive path (CI workflow, auth, hooks, secrets) forces
  Full tier no matter how small the diff. *Verified: a 1-line `.github/workflows/ci.yml` change
  → Full.* A two-line workflow edit is exactly what a size-only heuristic waves through.
- **Roles with nothing to review are pruned** *(new; absent from v1)*. A docs-only change does
  not pay for a security reviewer. *Verified: on this repo's own branch, 5 specialists → 2.*
- **Nothing big goes on a command line.** Briefs live on disk; agents launch with a one-line
  pointer. This is what keeps prompt caching effective.
- **Anchors are computed once** *(new; absent from v1)*. `manifest.json` records every
  `(file, side, line)` that genuinely exists in the diff. Without this table
  `validate_findings.py` would have nothing to check against — it is the mechanism that makes
  anchor rejection possible at all.

### Why the anchor gate matters

A hallucinated anchor is **the single most damaging thing this system can emit**: it looks
authoritative, it survives a human skim, and posted, it lands a review comment on an unrelated
line of someone's code. So findings are validated against the manifest before the judge is
allowed to read them. JSONL tolerance means one malformed line does not discard the good
findings around it — which is also why the format is JSONL and not one JSON blob: a specialist
killed mid-write still leaves everything it had already committed.

### The payload contract

One vocabulary end to end: `critical` / `moderate` / `nit`. The judge emits a payload
conforming to the **existing** `pr-review/review-payload.schema.json`, validated by the
**existing** `pr-review/scripts/validate_review.py` — both **unchanged**.

`event` is `APPROVE` or `COMMENT`. There is deliberately **no `REQUEST_CHANGES`**: the schema's
enum forbids it, this factory does not block merges, and a human decides what to do with a
critical. Cloudflare's rubric is likewise biased toward approving.

**No agent posts to GitHub.** Specialists write only their own findings file; the judge writes
only the payload; the orchestrator shows it to the human and posts on a yes.

### Concept mapping (still accurate from v1)

| Cloudflare | Ours |
| :--- | :--- |
| GitLab CI trigger | Orchestrator invokes an arm |
| Coordinator process | `prepare_review.py` (deterministic) + a judge agent (judgment) |
| 7 specialists in own sessions | 1–5 specialist agents, tier-sized, sonnet |
| `assessRiskTier()` | `assess_risk_tier()` — thresholds + security globs in config |
| diff_directory patch scoping | `.review/<slug>/diff/*.patch` + per-role focus paths |
| `shared-mr-context.txt` | `shared-context.md` (sanitized) |
| Structured XML findings | JSONL findings per specialist |
| Judge pass | dedupe → verify-uncertain-by-reading-source → recategorize → rubric |
| Approve / unapprove | `APPROVE` / `COMMENT` (no blocking) |
| Prompt-injection stripping | boundary-tag regex in `prepare_review.py` |
| `break glass` override | Not needed — the human orchestrator **is** the escape hatch |

### Risk tiers (data, in `assets/review-tiers.json`)

| Tier | Conditions | Specialists | Lead model |
| :--- | :--- | :--- | :--- |
| trivial | ≤10 changed lines and ≤20 files | generalist | sonnet |
| lite | ≤100 lines and ≤20 files | code-quality, security, docs | opus |
| full | >100 lines, or >50 files, or any security-sensitive path | all 5 | opus |

Assessment order (first match wins): security glob → size → trivial → lite → **otherwise full**.
That last rule closes v1's gap: 21–50 files with few lines is a broad blast radius, and is its
own risk signal. Specialists run on sonnet; `--tier` overrides everything.

### Prompt-injection defense

A PR title/body/comment is written by whoever opened the PR. It is untrusted input fed to five
agents. `prepare_review.py` strips conversational boundary tags (`<system>`,
`<system-reminder>`, `<instructions>`, …) case-insensitively, with or without attributes,
before any of it reaches `shared-context.md`. The prose survives; only the tags are neutralized.

This is **code, not a prompt politely asking the model to ignore instructions** — because the
latter is exactly what an injection defeats. The briefs additionally label the file untrusted,
but that is the second line of defense, not the first.

### Measurement (`score_run.py` — new; absent from v1)

Both arms leave the same trace: every Claude session (a cmux pane is one; a Workflow subagent
is one) writes a transcript with per-message `usage`. Snapshot the project dir before the run,
diff it after, sum what is new. No instrumentation, works retroactively, **identical code path
for both arms** — which is what makes the cost comparison fair.

Reports the Cloudflare-parity metrics:

- cost per review by tier (their baseline: $0.20 / $0.67 / $1.68)
- **cache hit rate** (theirs: 85.7%) — the sharpest test of "context on disk, not on argv"
- **cost-per-finding per specialist** — Cloudflare's *"which agent pays the bills."* A role that
  repeatedly costs money and finds nothing gets cut from `review-tiers.json`. Without this,
  roster decisions are a matter of taste; with it, they are arithmetic.

LangSmith/OTEL rides along behind a `--trace` flag as an **additive** view. It is never
load-bearing: a tracing misconfiguration must not be able to corrupt the comparison.

---

## Divergences from v1, and why

| v1 said | Reality | Why |
| :--- | :--- | :--- |
| One skill, `skills/cmux-review-factory/` | Core + two arms | The runtime was pinned before it was tested |
| Severities `critical/warning/suggestion` | `critical/moderate/nit` | The payload schema enforces these |
| Rubric emits `REQUEST_CHANGES` | `APPROVE`/`COMMENT` only | The schema's `event` enum has no such value |
| The **lead** posts to GitHub | The **orchestrator** posts, after a human gate | `github-pr-review` mandates approval; a pane has no human to ask |
| `fetch_diff.py` reused **unchanged** | **Modified** — see below | v1 simply asserted this without checking |
| `prepare_review.py` writes `team.json` | It does not; the cmux arm does | The core must stay backend-neutral, or the bake-off is confounded |
| Artifacts in `.team/review/<slug>/` | `.review/<slug>/` | Backend-neutral; `.team/` is what `spawn_team.py` owns |
| Role file `lead-judge.md` | `judge.md` | — |
| Tests use "importlib, per repo convention" | `sys.path` shim in `conftest.py`; subprocess for CLI | The stated convention was simply wrong |
| Re-review-lite in v1 | Deferred | No bearing on the substrate verdict |

### Changes to existing skills

`fetch-diff` — **modified**, not reused unchanged:

- New local `--base <ref>` mode (`git diff --merge-base <ref> HEAD`) sharing the **same
  annotator** as PR mode. One annotator, or a `file:line` anchor means two different things
  depending on source, and `validate_findings.py` cannot be trusted.
- Widened noise filter (all common lock files, minified bundles, sourcemaps, `@generated`
  markers) — with **migrations exempt**, because a bad migration can destroy production data
  and must always reach a reviewer.
- **Bug fixed:** a diff's trailing newline was annotated as a phantom context line, inventing a
  line number one past the end of the last hunk — a valid-*looking* anchor for a comment on a
  line that does not exist. It would have been recorded in `manifest.json` as legitimate,
  defeating the entire anchor gate. Regression-tested.

`boss-cmux-team` — `spawn_team.py` gains two backward-compatible extensions:

- **`--no-exec`**: skip `execvp`. Without it, spawning would hijack the caller's shell and hang
  the tool call the orchestrator is waiting on. *The caller is already the orchestrator.*
- **Per-role `command` override** (`__MODEL__`/`__KICKOFF__`/`__PROMPT__`): the default launch
  shape is pi's, and `claude` does not share it (no `--name`; `--append-system-prompt` takes an
  inline string, not a path). Defaults unchanged; regression-tested.

---

## ⛔ DO NOT REBUILD — read this before touching anything

Everything in **As-built** above already exists on disk, is tested, and is green. If you are
executing this plan (`/build`), your job is **only** the Step-by-Step Tasks below.

**Do not** re-create, "improve", or refactor any of these — they are done:

| Already exists | Do not touch it |
| :--- | :--- |
| `skills/review-factory-core/` — SKILL.md, 3 scripts, 7 role prompts, 2 asset configs, 57 tests | ✅ done |
| `.claude/skills/review-factory-workflow/SKILL.md` and `review-factory-cmux/SKILL.md` | ✅ done |
| `fetch-diff` `--base` mode, widened noise filter, phantom-anchor bugfix | ✅ done |
| `spawn_team.py` `--no-exec` + per-role `command` override | ✅ done |
| `eval/graders/check_manifest.py`, `eval/graders/check_no_injection.py` | ✅ done |
| `.gitignore` (`.review/`, `.team/`), `devtools/lint.py` typed paths, CHANGELOG, v0.29.0 | ✅ done |
| `commands/review-factory-{workflow,cmux}.md`, README/docs entries | ✅ done |

**Never edit one arm's prompts or the shared core to favour one substrate.** Both arms exist to
be a controlled comparison; tuning one invalidates the entire experiment.

Baseline to preserve: **1114 tests passing, 0 lint errors.**

---

## Step by Step Tasks

IMPORTANT: Execute every step in order, top to bottom. Steps 1–3 are safe and deterministic.
**Step 4 spawns real agents and costs real money — stop and ask the user before starting it.**

### 1. Build eval suite 1 — hermetic core

Create `plugins/boss-dev/agent-harness/skills/review-factory-core/eval/`:

- `eval/test-fixtures/*.diff` — canned **annotated** diffs (the `old new | line` format that
  `fetch_diff.py` emits; generate them by running `fetch_diff.py`, or hand-write them to match).
- `eval/eval.yaml` — follow the contract in
  [`run-skill-eval`](../plugins/boss-experimental/boss-experimental/skills/run-skill-eval/SKILL.md);
  copy the shape of
  [`claude-config-validation/eval/eval.yaml`](../plugins/boss-experimental/boss-experimental/skills/claude-config-validation/eval/eval.yaml).
  Use `defaults: {trials: 5, threshold: 0.8}`. A task passes only if **every** grader scores 1.0.

Each task replays a fixture hermetically — **no git, no network, no agents**:

```bash
uv run scripts/prepare_review.py --diff-file eval/test-fixtures/<name>.diff --out <workspace>
```

then grades the resulting `manifest.json` / `shared-context.md` with the **existing** graders.

Required tasks (each is a real regression guard, not a formality):

| Task | Asserts |
| :--- | :--- |
| `tier-trivial` | exactly 10 changed lines → `trivial` |
| `tier-lite` | 11 lines → `lite`; 100 lines → `lite` |
| `tier-full-by-size` | 101 lines → `full` |
| `tier-full-by-file-count` | 25 files, 1 line each → `full` (broad blast radius) |
| `security-glob-forces-full` | a **2-line** `.github/workflows/ci.yml` diff → `full` |
| `noise-filter-keeps-migrations` | `uv.lock` masked, `db/migrations/*.py` **reviewed** |
| `scoping-security-not-css` | `security` focus includes `auth/*.py`, excludes `*.css` |
| `roster-pruning` | a docs-only diff prunes `security` **and** `performance` from the roster |
| `injection-stripped` | boundary tags gone from `shared-context.md`, **prose intact** |

`check_manifest.py` already supports `--tier`, `--roles-include`, `--roles-exclude`, `--reviewed`,
`--masked`. `check_no_injection.py` supports `--must-contain`. Do not write new graders unless a
task genuinely cannot be expressed with these.

Verify: `/run-skill-eval plugins/boss-dev/agent-harness/skills/review-factory-core`

### 2. Build eval suite 2 — seeded defects

Fixtures with **known planted defects**, each with the defect's exact line recorded so a grader
can assert the finding anchors on it:

- `planted-sql-injection` — f-string interpolated into `cursor.execute`
- `planted-shell-injection` — `subprocess(..., shell=True)` with interpolated input (on-brand:
  this repo shells out everywhere)
- `planted-missing-authz` — an unguarded route handler
- `planted-perf-quadratic` — an O(n²) scan in a loop
- `planted-stale-claude-md` — a `CLAUDE.md` documenting a `make` target that no longer exists
- `planted-skill-backtick-bug` — a `SKILL.md` using the backtick-bang pattern that GitHub #12781
  makes **execute on skill load**. `agent-instructions` must catch this as `critical`.
- **`clean-no-defects`** — a correct, boring diff.

> `clean-no-defects` is the **most important task in the suite**. It must produce **zero**
> findings. It is the only task that separates a good factory from a plausible-sounding noisy
> one — every other task rewards finding things, and a factory that flags everything would ace
> them all.

Graders: a finding anchors within N lines of the planted defect **and** carries the right
severity, plus an `llm_rubric` penalizing noise. This suite spawns agents, so `trials: 1`.

### 3. Wire the scorecard into a repeatable run

Confirm end-to-end on a small local diff that `score_run.py snapshot` → run → `report` produces
the Cloudflare-parity block (cost, **cache hit rate**, **cost-per-finding per specialist**).
Fix any `$0.00` model rows by adding the missing prefix to `assets/model-pricing.json`.

### 4. ⚠ Run the bake-off — ASK THE USER FIRST

This spawns 6+ real agents per arm and costs real money. **Do not start it autonomously.**

Run **both** arms over suite 2 and 3–4 real PRs. Then have an opus judge synthesize a verdict
from both scorecards, both findings sets, and the diff between the two `review-payload.json`s.
Report to the user; **the promotion decision is theirs, not yours.**

### 5. Promote the winner (only after the user decides)

Move the winning arm's SKILL.md into `plugins/boss-dev/agent-harness/skills/` beside the core;
delete the loser and its `.claude/skills/` directory. Bump agent-harness (minor). Update
`docs/skills.md`, `docs/commands.md`, the README command count, and this spec.

### Deferred — not in scope for this plan

Re-review-lite (`fetch-unresolved-comments`) and full incremental re-review; `--isolate`
worktree mode; automatic roster tuning from cost/yield data; the **self-improvement loop**
(when `agent-instructions` flags High materiality, open a follow-up PR fixing the instruction
file rather than nagging a human — the highest-value idea in the source critique); per-role
model failback; an adversarial validator agent.

---

## Testing Strategy

- **Unit (pytest):** already green at 57 tests for the core. Any new pure helper gets a test in
  `scripts/tests/`, using the repo convention — a `sys.path` shim in `conftest.py` plus a plain
  import; **subprocess** for CLI semantics (exit codes, flags). *Not* importlib.
- **Eval suite 1:** hermetic, no agents, safe to run on every change. This is the CI gate.
- **Eval suite 2:** spawns agents; run deliberately, not in CI.
- **Regression:** `spawn_team.py` and `fetch-diff` tests must keep passing — both were modified.

## Acceptance Criteria

- `/run-skill-eval` on `review-factory-core` passes every suite-1 task, spawning **no agents**.
- A 2-line `.github/workflows/` diff is forced to **Full** tier; a docs-only diff **prunes**
  `security` and `performance` from the roster.
- `clean-no-defects` yields **zero** findings on both arms.
- A finding anchored to a line outside the diff is **rejected** by `validate_findings.py` before
  the judge sees it.
- `score_run.py report` shows cost-per-finding **per specialist** for both arms.
- No agent posts to GitHub; only the orchestrator does, and only after explicit human approval.
- `make lint && make test` stays at **0 errors / ≥1114 passing**; `./scripts/verify-structure.py`
  passes; versions stay in lockstep.

---

## Validation commands

```bash
# Repo gates — currently 0 lint errors, 1114 tests passing, structure valid
make lint && make test
./scripts/verify-structure.py

# The core's own tests
uv run pytest -s plugins/boss-dev/agent-harness/skills/review-factory-core/scripts/tests/

# Regression: the spawner and fetch-diff must still behave
uv run pytest -s plugins/boss-dev/agent-harness/skills/boss-cmux-team/scripts/tests/
uv run pytest -s plugins/boss-dev/agent-harness/skills/fetch-diff/scripts/tests/

# The pipeline, on this repo (writes nothing)
CORE=plugins/boss-dev/agent-harness/skills/review-factory-core
uv run "$CORE/scripts/prepare_review.py" --base main --dry-run

# Hermetic replay — no git, no network
uv run "$CORE/scripts/prepare_review.py" --diff-file <fixture>.diff --dry-run

# Once eval suite 1 lands
/run-skill-eval plugins/boss-dev/agent-harness/skills/review-factory-core
```

## Report

When this plan's tasks are complete, report:

1. **Eval suite 1** — the task table with pass/fail per task, and confirmation that it ran with
   **zero agents spawned** (that hermeticity is the point; if agents ran, the suite is wrong).
2. **Eval suite 2** — pass rate per planted defect, and the `clean-no-defects` result called out
   separately. A factory that catches every planted bug but also fires on the clean diff has
   failed, not succeeded.
3. **The scorecard**, per arm: total cost, cache hit rate (Cloudflare's baseline: 85.7%), and the
   cost-per-finding table **per specialist** — naming which specialist earned its keep and which
   is a candidate to cut from `review-tiers.json`.
4. **Regression status:** `make lint && make test` (baseline 0 errors / 1114 passing) and
   `./scripts/verify-structure.py`.
5. **What was NOT done**, plainly. Mislabeling unfinished work as finished is the exact failure
   that made v1 of this document worthless.

Do **not** report the bake-off verdict as decided. Present the evidence; the promotion decision
belongs to the user.

## Notes

- Both scripts are stdlib-only PEP 723, matching `spawn_team.py`. No new dependencies.
- `.gitignore` covers `.review/` and `.team/` (neither was ignored before this work).
- agent-harness is at **0.29.0** (`plugin.json` + `marketplace.json` in lockstep). Promoting the
  winning arm (Task 5) is the next bump, not this one.
- The `zsh` gotcha applies to every example: quote `'opus[1m]'`.
- **SKILL.md files must never use the backtick-bang pattern** — GitHub #12781 makes the parser
  *execute* it, even inside a fenced code block. Use `$ command` notation. (Suite 2 plants this
  very bug as a fixture; do not accidentally plant it in a real skill.)
- The eval **report** (`docs/evals/agent-harness/review-factory-core.md`) is generated output —
  produce it via `/skill-evals` after implementation, never by hand.
