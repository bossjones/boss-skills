# Plan: review-factory — a Cloudflare-style multi-agent code review factory

> **Status:** v3 — **part record, part plan.** The shared core, both execution arms, and **both
> eval suites** are built. Suite 1 passes 10/10. The core is at **86 tests**; the repo at
> **1143 passing, 0 lint errors**.
>
> **What v3 adds that v2 could not know:** the factory has now actually been *run*. That run
> **proved it works** — three specialists independently returned *zero findings* on a clean diff —
> and simultaneously **deadlocked for an hour**, exposing three defects and one bake-off-invalidating
> confound. Those are Step 0 below. **Nothing here describes work that does not exist.**
>
> v1 (`ff5788a`) predates the design interview and is comprehensively wrong. v2 was accurate when
> written but its "DO NOT REBUILD" table is now stale — see [Corrections](#corrections-to-v2).

## Context

Cloudflare replaced the human-review bottleneck with a CI-triggered factory: a coordinator
spawns domain specialists, **scales compute to the risk of the change** (trivial/lite/full
tiers → $0.20/$0.67/$1.68 median per review), **scopes context aggressively** (per-file
patches + one shared context file on disk rather than N duplicated prompts, for an 85.7%
cache hit rate), runs a **judge pass** (dedupe → verify-uncertain-by-reading-source →
recategorize), and applies an **approval rubric biased toward approving**.

The design principles adopted from the IndyDevDan critique: *agents + code, not agents alone*
(a deterministic pipeline; agents only where judgment is needed), *negative-scoped prompts*
("What NOT to flag"), *JSONL everywhere* (crash-survivable), and *measure which agent pays the
bills*.

We **built both substrates and will let evidence choose.**

---

## Decisions

1. **Both review targets** — GitHub PR and local branch diff vs merge-base, plus `--diff-file`
   replay for hermetic runs.
2. **3 risk tiers** (trivial/lite/full) size the team; security-sensitive paths force Full.
3. **Severity is `critical` / `moderate` / `nit`** — the existing
   `pr-review/review-payload.schema.json` enforces this vocabulary, so zero schema change.
4. **A bake-off, not one skill.** A shared deterministic core plus **two competing arms**; the
   winner is promoted, the loser deleted.
5. **Full-tier roster = 5 specialists**: security, code-quality, performance, docs,
   agent-instructions.
6. **The lead is a pure JUDGE, not a dispatcher.** Every specialist gets its complete task at
   spawn and runs independently.
7. **Re-review-lite deferred.**
8. **The orchestrator posts, not the lead** — and only after an `AskUserQuestion` gate.
9. ⭐ **NEW (v3): specialists never improvise their write path.** Findings are appended through a
   deterministic CLI (`append_finding.py`), not through shell redirection. See
   [Known defects](#known-defects) — this is the fix for the deadlock, and it is what makes the
   Workflow arm able to run headless at all.

---

## The two constraints that forced the architecture

**Write this down or someone will undo it.**

- `pyproject.toml:82` sets `exclude = [".claude/", ...]` with **`force-exclude = true`**. Ruff
  therefore *never* lints or formats Python under `.claude/`.
- Pytest's `testpaths = ["tests", "plugins"]`. Tests under `.claude/` are **never collected**.

Together: **Python under `.claude/skills/` escapes every quality gate this repo mandates.** That
is *why* the shared core is a plugin skill (linted, typed, tested) and only the two disposable
**markdown** playbooks live in `.claude/skills/`.

---

## As-built

```text
plugins/boss-dev/agent-harness/skills/review-factory-core/   # SHARED, permanent, linted+tested
├── SKILL.md                       # disable-model-invocation: true — a library, not a playbook
├── assets/
│   ├── review-tiers.json          # tiers, security globs, roster, focus globs, boundary tags
│   ├── model-pricing.json         # USD/Mtok by model prefix + the Cloudflare baseline
│   └── roles/*.md                 # security, code-quality, performance, docs,
│                                  #   agent-instructions, generalist, judge
├── scripts/
│   ├── prepare_review.py          # the deterministic pipeline
│   ├── append_finding.py          # ⭐ Step 0 — NOT YET BUILT — the ONLY sanctioned write path
│   ├── validate_findings.py       # the anchor gate
│   ├── score_run.py               # cost, cache hit rate, cost-per-finding per specialist
│   └── tests/                     # 86 tests
└── eval/
    ├── eval.yaml + test-fixtures/ # SUITE 1 — hermetic, 10 tasks, 10/10 passing
    ├── graders/                   # check_manifest, check_no_injection, check_findings
    └── defects/                   # SUITE 2 — 7 seeded-defect fixtures + planted.json

.claude/skills/review-factory-workflow/SKILL.md    # ARM B — Workflow-tool fan-out
.claude/skills/review-factory-cmux/SKILL.md        # ARM A — visible cmux panes
```

### Pipeline

```text
prepare_review.py      -> .review/<slug>/   (code: tier, roster, briefs, patches, anchors)
   [ specialists ]     -> append_finding.py -> findings/*.jsonl   (agents judge; CODE writes — Step 0)
validate_findings.py   -> rejects bad anchors BEFORE the judge sees them
   [ judge ]           -> review-payload.json (agent: judgment)
validate_review.py     -> schema gate (reused from pr-review, UNCHANGED)
   [ orchestrator ]    -> shows verdict, asks the human, posts
score_run.py           -> what it cost, and which agent paid the bills
```

### Four properties the rest of the system depends on

- **Risk sizes the team.** A security-sensitive path forces Full no matter how small the diff.
  *Verified: a 2-line `.github/workflows/ci.yml` change → Full.*
- **Roles with nothing to review are pruned.** *Verified: a docs-only diff prunes `security` and
  `performance`.*
- **Nothing big goes on a command line.** Briefs live on disk; agents launch with a pointer.
- **Anchors are computed once.** `manifest.json` records every `(file, side, line)` that genuinely
  exists in the diff. Without this table there is nothing to validate against.

### Why the anchor gate matters

A hallucinated anchor is **the single most damaging thing this system can emit**: it looks
authoritative, survives a human skim, and lands a review comment on an unrelated line of someone's
code. As of Step 0 the gate moves **earlier** — `append_finding.py` rejects a bad anchor *at write
time*, so it never lands at all and the agent is told to correct itself.

### The payload contract

One vocabulary end to end: `critical` / `moderate` / `nit`. `event` is `APPROVE` or `COMMENT` —
deliberately **no `REQUEST_CHANGES`**; this factory does not block merges.

**No agent posts to GitHub.** Specialists write only their own findings file; the judge writes only
the payload; the orchestrator shows it to the human and posts on a yes.

### Risk tiers (data, in `assets/review-tiers.json`)

| Tier | Conditions | Specialists | Lead model |
| :--- | :--- | :--- | :--- |
| trivial | ≤10 changed lines and ≤20 files | generalist | sonnet |
| lite | ≤100 lines and ≤20 files | code-quality, security, docs | opus |
| full | >100 lines, or >50 files, or any security-sensitive path | all 5 | opus |

Assessment order (first match wins): security glob → size → trivial → lite → **otherwise full**.
That last rule catches the 21–50-file, few-line case: broad blast radius is its own risk signal.

### Measurement (`score_run.py`)

Both arms leave the same trace: every Claude session writes a transcript with per-message `usage`.
Snapshot the project dir before the run, diff after, sum what is new.

Reports cost per review by tier (baseline $0.20/$0.67/$1.68), **cache hit rate** (theirs: 85.7%),
and **cost-per-finding per specialist** — Cloudflare's *"which agent pays the bills."*

---

## Known defects

All three were found by actually running the factory. **All three are unfixed until Step 0 lands.**

### 1. 🔴 BLOCKER — the Workflow arm deadlocks on its own write path

`prepare_review.py:344` renders into every specialist brief:

> Append **one JSON object per line, as you go — not one blob at the end.**

The `Write` tool **cannot append** — it truncates. That clause therefore leaves the model exactly
one primitive: shell redirection. It emitted `mkdir -p … && printf … > findings/security.jsonl`.
Claude Code's Bash matcher splits on `&&` and requires **every** subcommand to match the allowlist:
`Bash(mkdir:*)` is allowed, **`printf` is not**. The call fell through to a permission prompt — and
a background Workflow subagent **has no UI to render a prompt on**. It parked at
`stop_reason=tool_use` for an hour.

Two of three specialists hung. The third happened to reach for the `Write` tool (bare-allowlisted)
and sailed through. **It was nondeterministic model choice, not a role difference** — which is the
real indictment: *the write path was never pinned down, so it worked by luck.*

The `mkdir` was not even necessary — `prepare_review.py:544` already creates `findings/`.

### 2. 🔴 `score_run.py` could not see Workflow agents *(FIXED)*

The transcript glob was `*/subagents/*.jsonl`. Workflow subagents live a level deeper, under
`*/subagents/workflows/<run-id>/`. The scorer reported **"agents seen 0, $0.00"** for a run that
demonstrably spawned three.

cmux panes are top-level sessions and *were* counted. **So the bake-off would have handed the
Workflow arm a $0.00 win on a glob bug.** Fixed test-first; 4 regression tests added.

### 3. 🟡 `args` never reaches the Workflow script

`review-factory-workflow/SKILL.md:109` does `const { workspace, roles, … } = args`. `args` arrives
as a JSON **string**, so every field is `undefined` and the script dies on `roles.map`. The
documented script has therefore never worked.

---

## Bake-off confounds — read before trusting any comparison

**`review-factory-cmux/SKILL.md:86,92` launches every pane with
`claude --dangerously-skip-permissions`.**

The cmux arm therefore *cannot* hit defect #1, and never could. The Workflow arm inherits session
permissions and always can. Combined with defect #2 (Workflow agents costing $0.00), **any
comparison run before v3 would have been measuring the permission model and a glob bug, not the
substrate.**

This is not a reason to "fix" cmux — a visible pane you can interrupt is a legitimate design, and
skipping permissions is part of what that design *buys* (and part of what it *costs*, in safety).
It is a reason to (a) record the asymmetry, and (b) make both arms share **one** write path, so the
comparison is about the substrate and nothing else.

**Never edit one arm's prompts or the shared core to favour one substrate.**

---

## Corrections to v2

v2's "⛔ DO NOT REBUILD" table asserted things that are no longer true:

| v2 said | Reality |
| :--- | :--- |
| "57 tests" (3 places) | **86** in the core; **1143** repo-wide |
| Core scripts ✅ done, untouched | `prepare_review.py`, `score_run.py`, `check_manifest.py` were all **modified** |
| "Do not write new graders" | Suite 2 genuinely needed one: **`check_findings.py`** |
| Step 5: update `docs/skills.md`, `docs/commands.md` | **Neither file exists.** Phantom paths — use the plugin README + `docs/evals/README.md` |
| README/docs entries ✅ done | Only the *plugin* README. The root README has zero mentions |
| Both arms built and green | **Neither arm had ever been executed.** The Workflow arm is broken |

Still true, and still not to be rebuilt: the role prompts, `review-tiers.json`, `model-pricing.json`,
`validate_findings.py`, the `pr-review` payload schema and its validator, `fetch-diff`'s `--base`
mode and phantom-anchor fix, `spawn_team.py`'s `--no-exec`, and both suites' fixtures.

---

## Step by Step Tasks

IMPORTANT: Execute in order. **Steps 0 is free and deterministic. Steps 1–2 spend real money —
they are approved up to ~$9. Steps 4–5 are NOT approved; stop and ask.**

### 0. Fix the blocker — free, no agents

**0a. `scripts/append_finding.py`** — new PEP 723 stdlib CLI in the shared core.

`Bash(uv run:*)` is **already** in `.claude/settings.json` `permissions.allow`, so this needs **zero
settings changes** and can never prompt. It gives the agent *one deterministic command shape*
instead of letting it improvise shell, and preserves the incremental-append durability this design
prizes.

```bash
uv run "$CORE/scripts/append_finding.py" <workspace> --role security \
  --file src/db/queries.py --line 7 --side RIGHT --severity critical \
  --title "SQL injection" --body "..." [--confidence high] [--suggestion-patch ...]

uv run "$CORE/scripts/append_finding.py" <workspace> --role security --done
```

Behaviour:

- Appends exactly one JSON object per call to `<workspace>/findings/<role>.jsonl`.
- **Validates the anchor against `manifest.json` at write time**, exiting non-zero on a bad one, so
  a hallucinated anchor is rejected *before it lands* and the agent can self-correct. This is
  strictly stronger than the after-the-fact gate.
- Refuses a role not on the roster, and a `--file` not in the diff.
- `--done` appends the terminal record with counts computed **from the file**, not from the agent's
  say-so.
- Reuses `validate_findings.py`'s `REQUIRED_FIELDS` / `SEVERITIES` / `SIDES` — do **not** duplicate
  the vocabulary.

Tests (`scripts/tests/test_append_finding.py`, **written first**): good anchor accepted; bad anchor
rejected non-zero; bad severity rejected; `--done` counts computed from disk; append is additive.

**0b. `prepare_review.py` → `render_brief()`** — replace the "append as you go / not one blob"
prose with the `append_finding.py` invocation. Keep the JSONL contract and anchor rules verbatim;
only the *mechanism* changes. **Shared by both arms — this is what keeps the bake-off fair.** Drop
anything that invites a `mkdir`.

**0c. `review-factory-workflow/SKILL.md:109`** — fix the `args` bug:

```javascript
const cfg = typeof args === 'string' ? JSON.parse(args) : args
const { workspace, roles, specialist_model, lead_model } = cfg
```

The root cause is the *caller*: the Workflow tool passes `args` verbatim, so a stringified
object arrives as a string. The skill must also instruct the orchestrator to pass `args` as a
**real JSON object**, never `JSON.stringify`'d; the defensive parse stays as a belt-and-braces.

**0d. `review-factory-workflow/SKILL.md`** — bound the hang. `.catch(() => null)` at line 148
catches *rejections*, not *hangs*; nothing bounded that hour. Add an explicit timeout to each
`agent()` call so a stuck specialist fails loudly. `agent()` has **no timeout option** — the bound
must be a `Promise.race` against a `setTimeout` rejection inside the Workflow script (a rejection
timer needs no clock, so the `Date.now()` ban does not apply). **A specialist that can hang
unbounded is a defect regardless of the write path.**

### 1. Re-run the smoke — ~$1

`clean-no-defects` on the Workflow arm, end to end **through the judge**. Must reach a schema-valid
`review-payload.json` with **zero findings**, and `score_run.py report` must show **4 agents** (the
3 pruned specialists — security, code-quality, performance — plus the judge; not 0) at non-zero cost.

### 2. Run suite 2 — ~$5–8

All 7 seeded-defect fixtures on **one** arm (`review-factory-workflow`), `trials: 1`.

| Task | Planted defect | Anchor | Expect |
| :--- | :--- | :--- | :--- |
| **`clean-no-defects`** | **none — the control** | — | **zero findings** |
| `planted-sql-injection` | f-string into `cursor.execute` | `src/db/queries.py:7` | `critical` |
| `planted-shell-injection` | `subprocess(..., shell=True)` | `scripts/deploy.py:6` | `critical` |
| `planted-missing-authz` | `DELETE` route with no `@require_auth` | `src/api/routes.py:13` | `critical` |
| `planted-perf-quadratic` | O(n²) scan in a loop | `src/report/aggregate.py:6` | `moderate` |
| `planted-stale-claude-md` | documents a `make` target that no longer exists | `CLAUDE.md:9` | `moderate` |
| `planted-skill-backtick-bug` | the GitHub #12781 backtick-bang pattern | `skills/example/SKILL.md:11` | `critical` |

> **`clean-no-defects` is the most important task in the suite.** Every other task *rewards finding
> things*; a factory that flagged every line would score 6/7 and be worthless. It is the only task
> that separates a real reviewer from a plausible-sounding noisy one. **If it fails, the suite has
> failed regardless of the other six.**

### 3. Land it

- `make lint && make test && ./scripts/verify-structure.py`
- Bump agent-harness **0.29.0 → 0.30.0** (minor) in `plugins/boss-dev/agent-harness/.claude-plugin/plugin.json`
  **and** the matching `.claude-plugin/marketplace.json` entry — **lockstep**.
- CHANGELOG `[Unreleased]`: both eval suites, `append_finding.py`, the three bug fixes.
- Generate `docs/evals/agent-harness/review-factory-core.md` via `/skill-evals` (**never by hand** —
  it is regenerated output) and link it from the `docs/evals/README.md` index.
- Commit. **Do not** target `docs/skills.md` / `docs/commands.md` — they do not exist.

### 4. ⛔ NOT APPROVED — the bake-off

Both arms × suite 2 × 3–4 real PRs (~$30–60), then an opus judge synthesizing a verdict from both
scorecards, both findings sets, and the diff between the two payloads. **Ask the user first.**

**The cmux arm has still never been executed.** Do not imply otherwise.

### 5. ⛔ NOT APPROVED — promote the winner

Only after the user decides. Move the winner beside the core, delete the loser, bump minor.

### Deferred

Re-review-lite; `--isolate` worktree mode; automatic roster tuning from cost/yield data; the
**self-improvement loop** (when `agent-instructions` flags High materiality, open a follow-up PR
fixing the instruction file rather than nagging a human); per-role model failback.

---

## Testing Strategy

- **Unit (pytest):** 86 tests, the real CI gate. `sys.path` shim in `conftest.py` + plain import;
  **subprocess** for CLI semantics. *Not* importlib.
- **Suite 1:** hermetic, replays canned diffs, spawns **no specialist or judge agent**. Honest
  caveat: the eval harness is *itself* agent-driven — a task's `instruction` is always run by an
  agent, which here only executes a deterministic script. The literal zero-agent gate is
  `scripts/tests/test_fixtures_replay.py`, which runs in `make test`.
- **Suite 2:** spawns agents and costs money; run deliberately, never in CI.
- **Regression:** `spawn_team.py` and `fetch-diff` tests must keep passing.

## Acceptance Criteria

- A specialist can record a finding **with no permission prompt**, and a bad anchor is **rejected
  non-zero at write time**.
- The Workflow arm completes `clean-no-defects` end to end, producing a schema-valid payload with
  **zero findings**, and never hangs.
- `score_run.py report` shows **4 agents** (3 specialists + judge) and a cost-per-finding table
  **per specialist**.
- Suite 1 stays 10/10, spawning no review agents.
- No agent posts to GitHub; only the orchestrator, after explicit human approval.
- `make lint && make test` at **0 errors / ≥1143 passing**; `verify-structure.py` passes; versions
  in lockstep.

## Validation commands

```bash
CORE=plugins/boss-dev/agent-harness/skills/review-factory-core

# The deterministic gate — zero agents, zero cost
uv run pytest -s "$CORE/scripts/tests/"

# The blocker is fixed only if this writes with NO prompt...
uv run "$CORE/scripts/append_finding.py" <ws> --role security \
  --file src/db/queries.py --line 7 --side RIGHT --severity critical --title t --body b
# ...and a hallucinated anchor is REJECTED non-zero
uv run "$CORE/scripts/append_finding.py" <ws> --role security \
  --file src/db/queries.py --line 9999 --side RIGHT --severity critical --title t --body b

# Regression: the spawner and fetch-diff must still behave
uv run pytest -s "$CORE/../boss-cmux-team/scripts/tests/" "$CORE/../fetch-diff/scripts/tests/"

# Repo gates — baseline 0 lint errors, 1143 tests
make lint && make test && ./scripts/verify-structure.py

# Suite 1, through the graders
/run-skill-eval "$CORE"
```

## Report

1. **Suite 1** — the task table, pass/fail per task, and confirmation that **no specialist or judge
   agent was spawned** (stating plainly that the harness's own driver is agent-based).
2. **Suite 2** — pass rate per planted defect, with **`clean-no-defects` called out on its own
   line.** A factory that catches every plant but fires on the clean diff has **failed**.
3. **The scorecard** — total cost, cache hit rate (baseline 85.7%), and cost-per-finding **per
   specialist**, naming which specialist earned its keep.
4. **The three defects** — what each was and that each is fixed, with the deadlock's root cause
   named (not just "a permission issue").
5. **What was NOT done, plainly** — the bake-off, promotion, and the fact that **the cmux arm has
   still never been run.** Mislabeling unfinished work as finished is the exact failure that made
   v1 of this document worthless. It must not happen twice.

Do **not** report a bake-off verdict. The promotion decision belongs to the user.

## Notes

- All scripts are stdlib-only PEP 723. No new dependencies.
- `.gitignore` covers `.review/` and `.team/`; the eval workspaces (`ws/`) are covered by nested
  `.gitignore` files inside `eval/` and `eval/defects/` — **which only work once those files are
  committed.**
- agent-harness is at **0.29.0**; Step 3 bumps it to **0.30.0**.
- The `zsh` gotcha applies to every example: quote `'opus[1m]'`.
- **SKILL.md files must never use the backtick-bang pattern** — GitHub #12781 makes the parser
  *execute* it, even inside a fenced code block. Use `$ command` notation. Suite 2 plants this very
  bug as a `.diff` fixture; **never let it into a real `SKILL.md`.**
