# specs/eval-loop.md — Raise eval scores for the 6 weakest agent-harness skills

> Self-contained spec. Authored to be executed by a fresh agent with **zero prior
> conversation context**. Read top to bottom, then work the phases in order.

## Context (read first — no prior context assumed)

This repo scores its skills with **wshobson PluginEval** (pulled via `uvx`, nothing
vendored). Each skill has an `EVALS.md` report. Twelve skills under
`plugins/boss-dev/agent-harness/skills/` were last scored at **51–62/100**; the six weakest
all sit at ~51.x. Goal: raise those six, honestly.

**The pivotal fact:** every existing `EVALS.md` says *"No model usage (static-only
evaluation)"* — the **LLM judge layer never ran**. That freezes ~72% of the score weight at
heuristic defaults: Triggering Accuracy (25%, stuck ~0.52), Orchestration Fitness (20%,
~0.53), Output Quality (15%, flat 0.500), Scope Calibration (12%, flat 0.500). The skills'
descriptions are already good "Use when…" form, but the judge never read them, so the score
can't reflect that.

**Why that's now fixable:** the eval wrapper supports `--auth api-key`, which authenticates
the judge from `BOSS_SKILL_ANTHROPIC_API_KEY` in `.env` (mapped to `ANTHROPIC_API_KEY` for
the plugin-eval subprocess only — see `scripts/eval-skills.py:child_env`). The user has that
key set. So **running the judge is the single biggest lever** — it likely lifts scores
before any edit. Only after a judge-active re-baseline do we know which weaknesses are real.

### Prerequisites (verify before starting)
- `BOSS_SKILL_ANTHROPIC_API_KEY` is set in `/Users/bossjones/dev/bossjones/boss-skills/.env`.
- Work on branch `feature-improve-evals` (or a branch off it). All commands run from the
  repo root `/Users/bossjones/dev/bossjones/boss-skills`.
- The `/skill-evals` skill, the `make eval-skill` target, and `scripts/eval-skills.py`
  already support `--depth` and `--auth`; `make eval-skill` routes through the script so the
  dedicated key reaches review-mode runs.

### Target skills (6 weakest, all paths under plugins/boss-dev/agent-harness/skills/)
| Skill | Current (static-only) | Has references/? | Notes |
|-------|-----------------------|------------------|-------|
| fetch-unresolved-comments | 51.1 | no | GraphQL util; no error-handling docs |
| git-worktree-remove | 51.3 | no | good safety docs inline |
| git-worktree-status | 51.3 | no | check-status reporter |
| fetch-diff | 51.4 | no | diff+line-annotation util; no error docs |
| git-worktree-clean | 51.4 | no | has "Common mistakes" inline |
| add-review-comment | 51.5 | no | no error-handling docs |

All six are script-backed and lack a `references/` dir → Progressive Disclosure floored at
~0.20 (10% weight) and Robustness/Code-Template at 0.000 (static layer reads SKILL.md, not
scripts).

## Levers (mapped from `.claude/skills/skill-evals/references/fix-playbook.md`)
1. **Judge (biggest, no edit):** run standard depth with `--auth api-key` so Triggering/
   Output/Scope/Orchestration get real scores instead of defaults.
2. **Progressive Disclosure (10%, static):** add a `references/` dir per skill by extracting
   *genuine* detail out of the body — API/GraphQL notes, output schemas, troubleshooting/
   failure modes. This is honest (the three PR utilities truly lack error-handling docs) and
   raises PD from ~0.2 toward ~0.9 (cf. release-notes-generator at 0.90 with 2 refs).
3. **Ecosystem Coherence (2%, static):** add a short "Related skills" cross-link section —
   PR family: fetch-diff → add-review-comment → pr-review → fetch-unresolved-comments;
   worktree family: git-worktree → clean / remove / status / doctor.
4. **Robustness + Code Template (script-backed, static):** document each script's inputs/
   outputs/failure modes + example invocations in the body. **Do NOT inline code to game
   these** (fix-playbook is explicit) — the honest fix is documentation quality.
5. **Triggering (25%, judge):** only sharpen the `description` if the judge flags it after
   the re-baseline; add near-miss inclusions/exclusions. Don't over-stuff.

## Workflow

### Phase A — Judge-active re-baseline (do this first; may finish much of the job)
Run the six through the judge and overwrite their EVALS.md. Use the skill so output stays
out of context and fans out one subagent per skill:

```
/skill-evals --review --depth standard --auth api-key \
  plugins/boss-dev/agent-harness/skills/fetch-unresolved-comments \
  plugins/boss-dev/agent-harness/skills/git-worktree-remove \
  plugins/boss-dev/agent-harness/skills/git-worktree-status \
  plugins/boss-dev/agent-harness/skills/fetch-diff \
  plugins/boss-dev/agent-harness/skills/git-worktree-clean \
  plugins/boss-dev/agent-harness/skills/add-review-comment
```

Record the new composite + per-dimension scores for each (this is the new "before" for the
fix step). Confirm the reports now show model usage (judge ran), not "static-only".

### Phase B — Diagnose real weaknesses
For each skill, read the refreshed EVALS.md and list its lowest *real* dimensions. Expect
Progressive Disclosure (static) and Robustness/Code-Template (script-backed) to remain low
regardless of the judge; Triggering/Output/Scope now reflect reality.

### Phase C — Targeted, principled fixes (one skill at a time, lowest score first)
Edit only `SKILL.md` + add `references/` files. Keep edits principled: explain *why* in the
prose, generalise, avoid piling on rigid MUST/NEVER. Per skill:

- **fetch-diff / fetch-unresolved-comments / add-review-comment** (the PR utilities): create
  `references/` holding the API/GraphQL detail + output schema + a **Troubleshooting /
  failure-modes** section (auth errors, missing PR, large diffs, line-anchor pitfalls,
  resolved-vs-unresolved). Document the backing `scripts/` script's inputs/outputs in the
  body. Add a "Related skills" cross-link to the PR family.
- **git-worktree-clean / -remove / -status**: extract the deeper detail into `references/`
  (e.g. clean → database-branch cleanup + flag semantics; remove → safety-check matrix +
  branch-cleanup; status → PASS/FAIL/RUNNING/NOT_RUN semantics + re-running checks). Add a
  "Related skills" cross-link to the worktree family (and point shared detail at
  git-worktree's existing `references/` where apt rather than duplicating).

(If you prefer automation for some skills, `/skill-evals --fix --depth standard --auth
api-key <path>` will review→edit→re-score one skill — but prefer the manual, principled
edits above for honesty; never inline script code to lift Robustness/Code-Template.)

### Phase D — Re-eval + commit (per skill)
1. Re-score the skill judge-active and overwrite its EVALS.md:
   `make eval-skill SKILL=<path> DEPTH=standard AUTH=api-key` (or `/skill-evals --review
   --depth standard --auth api-key <path>`). Record before→after composite.
2. **skill-review** (hook-required): dispatch the `plugin-dev:skill-reviewer` agent with the
   skill path **and nothing else** (audit protocol: no tainting context). Resolve any
   critical/high findings before continuing.
3. **version-bump-reviewer** (hook-required): run it on the SKILL.md; it classifies the tier,
   bumps the plugin version (these are **plugin** skills → bump
   `plugins/boss-dev/agent-harness/.claude-plugin/plugin.json` **and** the matching
   `.claude-plugin/marketplace.json` entry in lockstep), and commits with a `(vX.Y.Z)`
   anchor. Stage the SKILL.md + new references/ + EVALS.md + the version artifacts together.

> Note: these are **plugin** skills (not repo-internal), so the version artifact is the
> agent-harness plugin's `plugin.json` + `marketplace.json` entry, bumped in lockstep — not a
> per-SKILL `metadata.version`. Six skills in one plugin → expect the plugin version to climb
> one tier per committed skill (or batch several skills into one bump if you commit them
> together; version-bump-reviewer takes the highest tier across the group).

## Guardrails
- **Judge key:** confirm `BOSS_SKILL_ANTHROPIC_API_KEY` in `.env` first; without it the judge
  silently no-ops back to static-only (flat 0.500) and the whole premise collapses.
- **No metric-gaming:** never paste script code into SKILL.md to lift Robustness/Code
  Template; document the scripts instead (fix-playbook.md).
- **Audit protocol** (`.claude/rules/audit-protocol.md`): invoke skill-review with only the
  path — no "I just fixed X", no hints.
- **Hooks fire on every SKILL.md edit:** skill-edit-review + version-bump-reviewer. Address
  skill-review findings first, then version-bump.
- **EVALS.md is regenerated output** — overwrite freely.

## Verification (definition of done)
- All six EVALS.md show the judge ran (no "static-only") after Phase A.
- Each fixed skill's composite **rose** vs its Phase-A judge-active baseline (record the
  delta per skill in the commit body, e.g. `plugin-eval: Δscore +X, Δanti_patterns ≤ 0`).
- `make lint` and `make test` stay green (no script changes expected, but run them if any
  tooling was touched).
- Each skill: skill-review PASS (0 critical/high); committed via version-bump-reviewer with a
  `(vX.Y.Z)` anchor and the agent-harness plugin.json + marketplace.json in sync.
- Nothing pushed unless the user asks.

## Cost
Judge-active standard depth ≈ 4 LLM calls/skill/round. Six skills × (1 baseline + 1 post-fix
re-score) ≈ ~48 calls, plus any `--fix` re-rolls. Keyed to `BOSS_SKILL_ANTHROPIC_API_KEY`
(metered API), not the Max plan.

## Out of scope
- The other six agent-harness skills (git-worktree, pr-review, release-notes-generator,
  stop-slop, unicode-hygiene, worktree-doctor) — revisit after the weakest cluster.
- Any change to the eval tooling itself (already shipped: `--depth/--concurrency/--auth`,
  dedicated-key auth).
