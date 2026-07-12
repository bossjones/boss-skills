# Plan: cmux-review-factory — a Cloudflare-style multi-agent code review factory for agent-harness

> **Status:** draft v1 — in revision with the user; implement in a fresh session once approved.
> **Deliverable:** new skill + command under `plugins/boss-dev/agent-harness`, plus two small
> extensions to `boss-cmux-team`'s spawner.

## Task Description

Take the concepts from Cloudflare's AI code review software factory
(<https://blog.cloudflare.com/ai-code-review/>, distilled with the IndyDevDan critique in
`ai_docs/cloudflare-software-factory-implementation.md` + `ai_docs/sources/cloudflare-software-factory-transcript.txt`)
and build a new **agent-harness** skill that spins up a cmux multi-agent code review session
using the user's proven **orchestrator → lead → workers** pattern (from
`~/dev/bossjones/boss-ai-monitoring` and `~/dev/bossjones/macos-ci`).

## Context

Cloudflare replaced the human-review bottleneck with a CI-triggered factory: a coordinator agent
spawns up to 7 domain specialists, **scales compute to the risk of the change**
(trivial/lite/full tiers → $0.20/$0.67/$1.68 median per review), **scopes context aggressively**
(per-file patch files + one shared context file on disk instead of 7 duplicated prompts), runs a
**judge pass** (dedupe, verify-uncertain-findings-by-reading-source, severity recategorization),
and applies an **approval rubric biased toward approving**. The tier-list critique adds the
design principles we adopt: *agents + code, not agents alone* (deterministic pipeline, agents
only where judgment is needed), *negative-scoped prompts* ("What NOT to flag"), *JSONL
everywhere* (crash-survivable output), and *measure which agent pays the bills*.

The user's existing three-tier cmux pattern supplies the runtime: an **orchestrator** (the
interactive Claude session that invokes the skill — spawns the team, watches, relays, never
reviews), a **lead** pane on a strong model, and **worker** panes on cheaper models, coordinated
through `.team/` files (spawn.json roster of stable UUIDs, artifact-based completion — never
pixels, exclusive file ownership) via the `boss-cmux` driver skill and `boss-cmux-team`'s
config-driven `spawn_team.py`.

**Decisions (confirmed with the user, 2026-07-12):**

1. **Both review targets** — GitHub PR (`gh`) and local branch diff vs merge-base.
2. **3 risk tiers** (trivial/lite/full) size the team; security-sensitive paths force Full.
3. **Findings post as inline PR comments** with critical/warning/suggestion severities + a unified summary verdict.
4. **New standalone skill** `skills/cmux-review-factory/`, reusing `boss-cmux` + `boss-cmux-team` rather than extending them.
5. **Full-tier roster = 5 specialists**: security, code-quality, performance, docs, agent-instructions (CLAUDE.md/AGENTS.md/SKILL.md staleness — Cloudflare's AGENTS.md reviewer, a natural fit for this repo).
6. **Lead is a pure JUDGE, not a dispatcher.** Every specialist receives its complete task at spawn and runs independently; the orchestrator prompts the lead only after all findings artifacts exist. This deletes the #1 failure mode from past runs (idle lead → stalled workers) and matches Cloudflare (coordinator only consumes structured findings).
7. **Re-review lite in v1** (lead reads unresolved threads via `fetch-unresolved-comments` to avoid duplicate posts); **full incremental re-review deferred to v2** (placeholder section below).
8. **Local mode reviews in place** against committed state (patches are frozen at prepare time; HEAD SHA recorded and re-checked); no worktree snapshot in v1.

## Objective

`plugins/boss-dev/agent-harness` gains (version 0.28.0 → **0.29.0**, minor):

- `skills/cmux-review-factory/` — SKILL.md orchestrator playbook, `scripts/prepare_review.py`
  (the deterministic pipeline), `scripts/validate_findings.py`, negative-scoped role prompts,
  tier config, references.
- Two small backward-compatible extensions to `boss-cmux-team/scripts/spawn_team.py`:
  `--no-exec` and a per-role `command` override.
- `commands/cmux-review.md` — thin slash-command entry point.
- Docs, CHANGELOG, version bump (via `version-bump-reviewer`).

## Problem Statement

Reviews today are either single-context (`/code-review`, `pr-review` — one agent holds
everything, no specialization, no tiered spend) or manual multi-agent one-offs (the
boss-ai-monitoring prompts — powerful but hand-rolled per run, build-shaped, and dependent on an
interactive lead that stalls). There is no reusable, risk-tiered, specialist fan-out review with
a judged, deduplicated, severity-tagged output that posts to GitHub — the thing Cloudflare
proved pays for itself. The building blocks (cmux driver, config-driven spawner, diff fetcher,
review posting rails, payload schema) all exist in agent-harness but are not composed.

## Solution Approach

**Agents + code.** Everything decidable by code is code (`prepare_review.py`); agents sit only
where judgment is needed (specialist review, lead judge pass).

### Concept mapping

| Cloudflare | Ours |
| :--- | :--- |
| GitLab CI trigger | Orchestrator session invokes `/agent-harness:cmux-review` |
| Coordinator process (Bun.spawn) | `prepare_review.py` (deterministic) + lead-judge pane (judgment) |
| `spawn_reviewers` via OpenCode SDK | `spawn_team.py --no-exec` with a generated team-config |
| 7 specialists in own sessions | 1–5 specialist claude panes (tier-sized), sonnet |
| `assessRiskTier()` | `assess_risk_tier()` in prepare_review.py (thresholds + security globs in config) |
| diff_directory patch scoping | `.team/review/<slug>/diff/*.patch` + per-role scoped path lists in briefs |
| `shared-mr-context.txt` | `.team/review/<slug>/shared-context.md` (sanitized) |
| Structured XML findings | JSONL findings per specialist (`findings/<role>.jsonl`) |
| Judge pass | Lead pane: dedupe → verify-by-reading-source → recategorize → rubric |
| Approve/unapprove/block | `github-pr-review` event: APPROVE / COMMENT / REQUEST_CHANGES |
| Prompt-injection boundary stripping | Same regex approach on PR body/comments in prepare_review.py |
| `break glass` override | Not needed — the human orchestrator user IS the escape hatch |
| Heartbeat "model is thinking" | Orchestrator heartbeat loop (existing pattern) |

### Topology & lifecycle

```text
Orchestrator (this session, invokes skill)
  │ 1. uv run prepare_review.py [--pr N | --base main] [--tier X] [--dry-run]
  │      → .team/review/<slug>/{manifest.json, diff/, shared-context.md, briefs/, team.json}
  │ 2. uv run spawn_team.py cc review-<slug> --config …/team.json --no-exec
  │      → one workspace: lead-judge pane (left) + N specialist panes (grid)
  │ 3. HEARTBEAT: poll findings/<role>.jsonl for terminal done-records (files, not pixels);
  │      stall probe = md5 screen-diff ~10s apart; per-specialist timeout 10m, overall 25m
  │ 4. all done → uv run validate_findings.py → prompt LEAD: "judge"
  │ 5. lead posts (PR mode) or writes report.md (local) → orchestrator relays verdict
  ▼
Lead-judge pane (opus; sonnet on Trivial)     Specialist panes (sonnet)
  idle until step 4, then:                      kickoff = one line: "Read
  validate → dedupe → verify uncertain          .team/review/<slug>/briefs/<role>.md
  findings by reading source (re-check          and execute it." Reads scoped patches +
  recorded HEAD SHA first) → recategorize →     shared-context.md, writes ONLY its own
  re-review-lite (fetch-unresolved-comments,    findings/<role>.jsonl, ends with a
  skip dupes) → review-payload.json             done-record. Never posts to GitHub.
  (pr-review schema) → post via
  github-pr-review rails / render report
```

Key failure-mode defenses (learned from past runs + the design critique):

- **Completion = artifact, not sentinel-on-screen.** The kickoff text itself would echo any
  `TASK-DONE` string, so the terminal signal is a `{"type":"done",…}` JSONL record in the
  specialist's findings file. `read-screen` is a stall diagnostic only.
- **Nothing big on a command line** (Cloudflare's E2BIG lesson): kickoffs are one-line pointers;
  all real context lives on disk. Also what makes prompt caching work.
- **Single-writer everywhere**: each specialist writes only `findings/<role>.jsonl`; only the
  lead posts to GitHub; only prepare_review.py writes `diff/` and `briefs/`.
- **Anchor validation**: findings must cite file:line inside the annotated diff;
  `validate_findings.py` rejects out-of-diff anchors (kills hallucinated line numbers) before
  the lead ever judges.

### Risk tiers (data, not code — `assets/review-tiers.json`)

| Tier | Conditions (defaults) | Panes | Lead model |
| :--- | :--- | :--- | :--- |
| trivial | ≤10 changed lines and ≤20 files | lead + generalist | sonnet |
| lite | ≤100 lines and ≤20 files | lead + code-quality + security + docs | opus |
| full | >100 lines, or >50 files, or any security-sensitive path | lead + all 5 specialists | opus |

Security-sensitive globs (config, extensible): `**/auth/**`, `**/crypto/**`, `**/*secret*`,
`**/.env*`, `**/hooks/**`, `**/settings*.json`, `.github/workflows/**`, `**/permissions*`.
A `--tier` flag overrides the assessment. Specialist models default to sonnet, per-role
overridable.

### Deterministic pipeline (`prepare_review.py`)

1. **Acquire diff** — PR mode: reuse `fetch-diff`'s script (annotated old/new line numbers,
   masks generated files) + `gh pr view` for metadata. Local mode: `git diff <merge-base>` vs
   `--base` (default `main`); warn on dirty tree; record HEAD SHA in `manifest.json`.
2. **Noise filter** — strip lock files (`bun.lock`, `package-lock.json`, `uv.lock`, `Cargo.lock`,
   `go.sum`, …), minified assets, sourcemaps, `@generated`-marked files — **database migrations
   exempted**.
3. **Patch scoping** — one patch file per changed file under `diff/`; per-role scoped path lists
   (e.g. security gets auth/config/workflow paths, docs gets `*.md` + docstring-heavy files;
   every role gets the full file list, scoped roles get "focus paths").
4. **Shared context** — PR title/body/comments/linked-issue text written once to
   `shared-context.md`, after **boundary-tag stripping** (case-insensitive regex over a
   configured tag list) so a PR description can't inject instructions.
5. **Tier assessment + roster** → **brief generation** (`briefs/<role>.md` = role prompt +
   scoped paths + findings contract + review-id specifics) → **team.json generation** (absolute
   prompt paths, per-role `command` overrides using the claude launcher, one-line kickoffs).
6. `--dry-run` prints tier, roster, filtered/kept files, and the generated config without
   touching cmux (CI-safe; mirrors `spawn_team.py --dry-run`).

### Findings pipeline — one pipeline, three representations

1. **Raw**: specialists append JSONL —
   `{"role","file","line_start","line_end","severity":"critical|warning|suggestion","title","body","confidence",("suggestion_patch")}`
   — terminated by `{"type":"done","counts":{…}}`. JSONL is the crash-survivability lesson:
   valid mid-flight, appendable, parseable if a pane dies.
2. **Judged**: lead emits `review-payload.json` conforming to the **existing**
   `pr-review/review-payload.schema.json`, validated by pr-review's `validate_review.py`.
3. **Posted**: PR mode rides the already-tested `github-pr-review`/`add-review-comment` rails
   (pending review, batched inline comments, suggestion blocks, severity tags); local mode
   renders the same payload to `.team/review/<slug>/report.md`.

### Approval rubric (in `lead-judge.md`, biased toward approval)

| Condition | Verdict | gh event |
| :--- | :--- | :--- |
| All LGTM / only suggestions | approved | APPROVE |
| Warnings, no production risk | approved w/ comments | APPROVE (comments attached) |
| Multiple warnings forming a risk pattern | minor issues | COMMENT |
| Any critical, or production-safety risk | significant concerns | REQUEST_CHANGES |

Local mode maps the same verdicts to a report header. No auto-merge ever; the human user is the
break-glass.

### Role prompts (`assets/roles/*.md`)

Every specialist prompt has the same skeleton: **Scope** (what you review, focus paths
placeholder), **What to Flag**, **What NOT to Flag** (the negative scoping — the
highest-leverage noise reduction; e.g. security: no theoretical risks needing unlikely
preconditions, no defense-in-depth nits when primary defenses are adequate, no issues in
unchanged files), **Severity definitions**, **Findings contract** (JSONL schema + done-record +
own-file-only), **Evidence rules** (cite the patch line numbers; if you can't anchor it, don't
emit it). `agent-instructions.md` implements the materiality ladder (high/medium/low) for
CLAUDE.md/AGENTS.md/SKILL.md staleness. `lead-judge.md` carries the judge pass, re-review-lite,
rubric, posting instructions, and "paste real command output, never paraphrase".

## Relevant Files

### Reused (existing, unchanged)

- `plugins/boss-dev/agent-harness/skills/boss-cmux/SKILL.md` — cmux driver verbs the orchestrator uses (send / send-key enter / read-screen three-step, tree diffing, close-surface).
- `plugins/boss-dev/agent-harness/skills/boss-cmux-team/assets/roles/lead.md` — style reference for role prompts.
- `plugins/boss-dev/agent-harness/skills/fetch-diff/scripts/fetch_diff.py` — annotated PR diffs (PR mode acquisition).
- `plugins/boss-dev/agent-harness/skills/fetch-unresolved-comments/` — re-review lite input.
- `plugins/boss-dev/agent-harness/skills/github-pr-review/SKILL.md` + `skills/add-review-comment/SKILL.md` — posting rails for the lead.
- `plugins/boss-dev/agent-harness/skills/pr-review/review-payload.schema.json` + `skills/pr-review/scripts/validate_review.py` — judged-payload schema + validator.
- `plugins/boss-dev/agent-harness/commands/cmux-did-spawn.md` — re-orientation if the orchestrator session is lost mid-run.
- `.claude/skills/version-bump-reviewer/SKILL.md` — governs the version bump.
- `specs/cmux.md`, `~/dev/bossjones/boss-ai-monitoring/prompts/boss-ai-monitoring-build-team.md`, `~/dev/bossjones/macos-ci/docs/contributor/team-coordination-mechanics.md` — pattern references for SKILL.md authoring.

### Modified

- `plugins/boss-dev/agent-harness/skills/boss-cmux-team/scripts/spawn_team.py` — add `--no-exec` (skip `exec_orchestrator`, print refs and exit 0) and per-role `"command"` override (used verbatim after `__MODEL__`/`__KICKOFF__`/`__PROMPT__` interpolation; fixes the pi-shaped `build_command` — `claude` has no `--name` and `--append-system-prompt` takes a string, not a path).
- `plugins/boss-dev/agent-harness/skills/boss-cmux-team/scripts/tests/test_spawn_team.py` — tests for both.
- `plugins/boss-dev/agent-harness/.claude-plugin/plugin.json` + `.claude-plugin/marketplace.json` — 0.29.0 (lockstep).
- `CHANGELOG.md`, `plugins/boss-dev/agent-harness/docs/skills.md`, `docs/commands.md`, `plugins/boss-dev/agent-harness/README.md` — document the new skill/command.

### New Files

```text
plugins/boss-dev/agent-harness/
├── skills/cmux-review-factory/
│   ├── SKILL.md                          # orchestrator playbook (trigger patterns, lifecycle, heartbeat, teardown)
│   ├── assets/
│   │   ├── review-tiers.json             # tier thresholds, security globs, per-tier roster + models, noise-filter lists, boundary tags
│   │   └── roles/
│   │       ├── lead-judge.md             # judge pass, re-review lite, rubric, posting
│   │       ├── generalist.md             # trivial-tier all-rounder
│   │       ├── security.md
│   │       ├── code-quality.md
│   │       ├── performance.md
│   │       ├── docs.md
│   │       └── agent-instructions.md     # CLAUDE.md/AGENTS.md/SKILL.md materiality ladder
│   ├── scripts/
│   │   ├── prepare_review.py             # PEP 723; pure core + IO shell; --dry-run
│   │   ├── validate_findings.py          # PEP 723; JSONL schema + anchor-in-diff validation
│   │   └── tests/
│   │       ├── conftest.py
│   │       ├── test_prepare_review.py
│   │       └── test_validate_findings.py
│   └── references/
│       ├── architecture.md               # Cloudflare mapping + design rationale (condensed from ai_docs)
│       ├── findings-schema.md            # JSONL contract, done-record, examples
│       └── orchestrator-loop.md          # heartbeat cadence, stall probe, timeout/teardown, recovery via /cmux-did-spawn
└── commands/cmux-review.md               # /cmux-review [pr#|--base ref] [--tier X] [--dry-run]
```

Runtime state (gitignored, add `.team/review/` if `.team/` isn't already covered):
`.team/review/<slug>/{manifest.json, diff/, shared-context.md, briefs/, team.json, findings/, review-payload.json, report.md}` plus `spawn_team.py`'s standard `.team/review-<slug>.spawn.json`.

## Implementation Phases

### Phase 1: Deterministic core (no cmux, fully testable)

`prepare_review.py` pure functions + tests: diff acquisition/parsing, noise filter,
`assess_risk_tier`, boundary-tag stripper, per-role scoping, brief + team-config generation.
`validate_findings.py` + tests.

### Phase 2: Spawner extension

`spawn_team.py` `--no-exec` + per-role `command` override, with tests. Pure-function changes;
existing behavior untouched (defaults preserved).

### Phase 3: Prompts + orchestration + integration

Role prompts, `review-tiers.json`, SKILL.md, `commands/cmux-review.md`, references. End-to-end
`--dry-run` on a real branch of this repo; then one live smoke run (small PR, trivial tier).

### Phase 4: Ship

Docs, CHANGELOG, `make lint && make test`, `make markdown-lint`, `scripts/verify-structure.py`,
version bump via `version-bump-reviewer`, PR via `/agent-harness:commit-push-pr`.

## Step by Step Tasks

IMPORTANT: Execute every step in order, top to bottom.

### 1. Build prepare_review.py (Phase 1)

- Scaffold PEP 723 script with pure core / IO shell split (mirror `spawn_team.py`'s structure).
- Implement + test: noise filter (migrations exempt), `assess_risk_tier` (boundary values), boundary-tag stripping (case-insensitive, tags w/ attributes), per-role path scoping, config/brief generation (absolute prompt paths, kickoffs <200 chars), manifest with HEAD SHA, `--dry-run`.

### 2. Build validate_findings.py (Phase 1)

- JSONL parse tolerance (skip malformed lines with a report), severity enum, anchors-within-diff check against `manifest.json`, done-record presence, exit codes for orchestrator use.

### 3. Extend spawn_team.py (Phase 2)

- `--no-exec` flag: after `write_spawn_file`, print `workspace/lead/spawn` line and return 0 — never reach `execvp` (test asserts this).
- Per-role `command` override with `__MODEL__`/`__KICKOFF__`/`__PROMPT__` interpolation; default path unchanged (regression tests).

### 4. Author role prompts + tier config (Phase 3)

- Write the 7 role files with the shared skeleton (Scope / What to Flag / What NOT to Flag / Severity / Findings contract / Evidence rules).
- `review-tiers.json` with the defaults tabled above.

### 5. Author SKILL.md + command (Phase 3)

- SKILL.md: concrete triggers ("review PR 123 with the review factory", "/cmux-review", "spin up a review team"), the 5-step lifecycle, heartbeat/stall/timeout policy, teardown, recovery. Use `$ command` notation (parser bug #12781); frontmatter per house style (`allowed-tools` scoped Bash patterns).
- `commands/cmux-review.md`: thin wrapper passing `$ARGUMENTS` to the skill.

### 6. Integrate + smoke (Phase 3)

- `--dry-run` end-to-end on this repo (fixture branch); verify generated team.json boots via `spawn_team.py --dry-run`.
- One live trivial-tier run against a small real PR; confirm findings JSONL → payload → posted review.

### 7. Ship (Phase 4)

- Docs + CHANGELOG; run all validation commands; `version-bump-reviewer` (minor → 0.29.0); commit-push-pr.

## Testing Strategy

- **Unit (pytest, `importlib` PEP 723 loading per repo convention):** tier boundaries exactly at 10/100 lines and 20/50 files; security glob forcing Full on a 2-line diff; lock/minified/`@generated` filtered but `migrations/` kept; boundary-tag regex; scoping (security gets `auth/*.py`, never `*.css`); generated config validity (absolute prompt paths, claude commands, no long kickoffs); `--no-exec` never execs; findings validator rejects bad severity / out-of-diff anchors / missing done-record.
- **Integration (no cmux):** `prepare_review.py --dry-run` on fixture diffs (one per tier); generated `team.json` accepted by `spawn_team.py --dry-run`.
- **Live smoke (manual, documented in SKILL.md):** trivial-tier review of a real small PR.

## Acceptance Criteria

- `/agent-harness:cmux-review --pr <N>` on a small PR spawns a tier-sized cmux team, produces validated findings, and posts a single unified review with severity-tagged inline comments and the rubric verdict.
- Local mode (`--base main`) produces `report.md` from the same pipeline.
- A 2-line diff touching `.github/workflows/` is forced to Full tier; a 5-line docs diff runs Trivial with 2 panes.
- Second run on a PR with unresolved threads does not duplicate existing findings (re-review lite).
- Specialists never post to GitHub; only the lead does; each writes only its own findings file.
- Zero lint/type errors; all new tests pass; `spawn_team.py` existing tests still pass; versions in lockstep at 0.29.0.

## Validation Commands

Execute these commands to validate the task is complete:

- `make lint && make test` — full repo checks (zero warnings required).
- `uv run pytest -s plugins/boss-dev/agent-harness/skills/cmux-review-factory/scripts/tests/` — new-skill tests.
- `uv run pytest -s plugins/boss-dev/agent-harness/skills/boss-cmux-team/scripts/tests/` — spawner regression + new flags.
- `uv run plugins/boss-dev/agent-harness/skills/cmux-review-factory/scripts/prepare_review.py --base main --dry-run` — pipeline dry-run on this repo.
- `uv run plugins/boss-dev/agent-harness/skills/boss-cmux-team/scripts/spawn_team.py cc review-smoke --config .team/review/review-smoke/team.json --no-exec --dry-run` — spawn dry-run of a generated config.
- `make markdown-lint && ./scripts/verify-structure.py` — docs + plugin-structure checks.

## Deferred to v2 (designed placeholders)

- **Full incremental re-review:** feed the previous review text + thread resolution states to the lead; omit fixed findings (auto-resolve threads), re-emit unfixed, respect human-resolved unless materially worse, handle "won't fix"/"I disagree" (argue-back). Builds on `fetch-unresolved-comments`; needs a thread-resolution writer skill.
- **Validator pane option:** a read-only ✅ validator that adversarially re-verifies findings before the lead posts (config flag; the roster is already data).
- **Worktree snapshot mode:** `--isolate` flag — detached worktree at the recorded SHA so the user can keep editing during Full-tier reviews.
- **Cost/yield attribution:** per-agent finding counts by severity + token cost (which agent pays the bills) appended to `manifest.json`; feeds roster tuning.
- **Self-improvement loop:** when agent-instructions flags High materiality, open a follow-up task/PR that updates the instruction file instead of nagging (the F→A upgrade from the tier list).
- **Model failback:** per-role fallback model in `review-tiers.json` used by the orchestrator when a pane's launcher fails.

## Notes

- No new dependencies; both scripts stay stdlib-only PEP 723 (matching `spawn_team.py`).
- The zsh gotcha applies to all examples: quote `'opus[1m]'`.
- Eval report (`docs/evals/agent-harness/cmux-review-factory.md`) is generated output — produce after implementation via `/skill-evals`, not by hand.
- Skill name keeps the `cmux-` prefix for trigger clarity; a non-cmux backend would be a v3 concern.
