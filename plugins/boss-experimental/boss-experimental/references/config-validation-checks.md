# Claude Config Validation Checks

Reference table for the checks run by `/claude-config-validation`. Organized in six categories.

## Project Structure

| # | Check | What it validates | Pass | Warn | Fail |
|---|-------|-------------------|------|------|------|
| 1 | Config exists | The config home (or root) has a `.claude/` directory | Config found | — | No `.claude/` at all |
| 2 | Canonical agents | The canonical roles (default: `architect`, `coder`, `learner`, `pr-submission`, `reviewer`, `test-writer`, `tester` — the set is config-driven and overridable, not a hard requirement) are root-owned and live **only** at the repo root. A config home must not redefine them — a same-named override is shadowed by the root agent and never runs; config homes specialize via substrate (skills/rules with `paths`). A domain-prefixed custom agent (e.g. `myapp-coder`) is allowed only when a pipeline declared by the config home invokes it (an **optional, documented extension point** — default convention: a `.claude/pipelines.json` listing pipelines and the agents they invoke). | **Config home:** no agent reuses a canonical role name and none is a renamed canonical role. **Root:** each declared canonical role present, with role-appropriate frontmatter (read-only roles request no write tools). | **Config home:** a domain-prefixed custom agent (confirm it is intentional and pipeline-declared; if the repo uses no pipeline mechanism, treat as WARN pending confirmation). **Root:** extra non-canonical agents. | **Config home:** an agent named as a canonical role (collision, silently shadowed), a renamed canonical role (e.g. `implementer`→`coder`), or a canonical platform-variant (`coder-mobile.md`). **Root:** a declared canonical role missing, or a read-only role requesting write tools. |
| 3 | Agent frontmatter | `name`, `description`, `tools` fields; permission/tool consistency | All fields valid | — | Missing fields; non-writing agent has Write/Edit; permission mismatch |

## Knowledge Placement

| # | Check | What it validates | Pass | Warn | Fail |
|---|-------|-------------------|------|------|------|
| 4 | Convention placement | File-type conventions (copyright, imports, naming) belong in rules, not agent prompts. Monorepo-wide conventions (copyright header, `import type`, build-tool conventions) belong in root `.claude/rules/` with `paths`, not duplicated in each config home's rules. | No conventions in agents; no monorepo-wide conventions in config-home rules | Convention in >1 agent; monorepo-wide convention in config-home rule | — |
| 5 | Duplication | CLAUDE.md content not copy-pasted into agents | No duplication | Significant duplication found | — |
| 6 | CLAUDE.md size | Under 200 lines; extract to rules/docs/skills if larger | Under 200 lines | 200–300 lines | Over 300 lines |
| 7 | Rules frontmatter | Rules have `paths` for context loading (`paths` is a loading trigger, not a scope enforcer — see Rules section in architecture doc) | Valid `paths` present | Config-home-level rule without `paths` (may be intentional) | Root-level rule without `paths` (loads for everyone) |
| 23 | CLAUDE.md context discipline | CLAUDE.md loads into every session and agent monorepo-wide, so every line is a context tax. Routing rows point to a single entry doc per task. A doc only relevant to a narrow file pattern already covered by a path-scoped rule must not also be added to the routing table — the rule loads it on demand, so the routing entry is redundant context tax with no added discovery. | Each routing row has one entry doc; no doc duplicated between a path-scoped rule and the routing table | Routing row lists multiple docs (joined by "and"/comma), or a path-scoped rule's doc is also listed in the routing table | — |

## Skill Quality

| # | Check | What it validates | Pass | Warn | Fail |
|---|-------|-------------------|------|------|------|
| 10 | Skill content quality | Declarative only — no code blocks with language identifiers, no external dependencies, no large inline data. Code examples and coding patterns belong in domain docs (`docs/`), not inline in SKILL.md or in `references/`. Skill-internal templates (output formats, sub-agent rubrics) may live in `references/`. | Clean | External deps suspected; >50 lines non-prose | Code blocks with language identifiers |
| 11 | Skill frontmatter | `description` field exists; `allowed-tools` matches actual tool usage in body | Frontmatter valid | Missing frontmatter; tool mismatch | — |
| 12 | Skill directory structure | Follows `{skill-name}/SKILL.md` convention | Correct structure | Unexpected files (README.md) in skills/ | Flat files instead of SKILL.md in subdirectory |
| 13 | Cross-skill duplication | No 5+ consecutive near-identical lines across `.claude/` files | No duplication | Duplicated content found (report files + suggest single source of truth) | — |
| 14 | Skill size & separation | Under 150 lines; procedure only, not domain knowledge | Under 150 lines | 150–250 lines (review for mixed concerns) | Over 250 lines (checklists >10 items, inline API docs, code templates, config instructions belong in `docs/`) |
| 22 | Skill eval present (opt-in) | **Opt-in — not a universal mandate.** When the repo has opted into eval coverage for its skills, every skill under `.claude/skills/` should have an `eval/` directory with `eval.yaml`. When the repo has not opted in, report N/A. | Opted in: `eval/` exists with `eval.yaml`. Not opted in: N/A | Opted in: `eval/` directory exists but missing `eval.yaml` | Opted in: no `eval/` directory |

## Discoverability & References

| # | Check | What it validates | Pass | Warn | Fail |
|---|-------|-------------------|------|------|------|
| 8 | Skill references | Agent says "use the X skill" — skill must exist | All references resolve | — | Referenced skill not found |
| 9 | Routing table | File paths in CLAUDE.md routing table resolve | All entries resolve | — | Broken references |
| 15 | Routing table completeness | Every domain doc referenced by agents/skills appears in nearest CLAUDE.md routing table. Skills may have routing entries. Agents (auto-discovered via `description`) and commands (auto-discovered via `/`) never need routing entries. **Docs referenced only by a path-scoped rule never need a routing entry** — the rule's `paths` frontmatter is itself the loading trigger and loads the doc on demand (when a matching file is touched), which is strictly cheaper than the always-loaded routing table. Do not flag a doc as missing from the routing table when a path-scoped rule already references it. | All domain doc references have routing entries | Domain doc referenced by an agent/skill but not in routing table | — |
| 16 | Cross-file references | Skills referencing other skills/commands — targets exist; `/`-prefix matches real commands. Built-in Claude Code commands (`/plan`, `/init`, etc.) are excluded — these are runtime features, not project-defined skills. | All references valid | `/`-prefix used but only skill exists (not a command) | Referenced project skill/command doesn't exist at all |
| 17 | Routing table targets | Routing table entries point to a concrete destination — a domain doc, a package doc (`README.md`, `docs/DESIGN.md`), or a skill — never to another CLAUDE.md file. The anti-pattern is a map pointing to another map; any real content file is a valid target. | All entries point to a destination doc or skill | — | Entry points to a CLAUDE.md file |
| 18 | Domain doc self-containment | Task-recipe domain docs reachable from the routing table contain essential steps **and essential decision logic** inline, not behind secondary references. Conditional behavior (gating, eligibility, feature-flag predicates) must be stated as an explicit, testable predicate (`enable when A AND B AND C`, terms + default defined) — not left as prose to re-derive. Applies to *task recipes* — not to package architecture docs (`DESIGN.md`) whose intentional shape is bounded-context navigation/cross-linking. | Required steps and decision predicates are inline | Task-recipe doc delegates essential steps to another doc, or describes conditional behavior only in prose without a stated predicate | — |

## Compliance Placement

| # | Check | What it validates | Pass | Warn | Fail |
|---|-------|-------------------|------|------|------|
| 19 | Compliance placement | Skills containing primarily convention constraints ("must", "always", "never") rather than procedural steps — these would be more effective as rules, which shape plans; skills only execute | Skills contain procedures, not conventions | Skill body is primarily declarative constraints rather than procedural steps | — |

## Loading & Registration

| # | Check | What it validates | Pass | Warn | Fail |
|---|-------|-------------------|------|------|------|
| 20 | Nested `.claude/` directories | No `.claude/` directories exist below the config home root. CLAUDE.md and skills lazy-load from subdirectories, but nested rules, agents, and settings never load — and one `.claude/` per config home is mandated regardless, for governance and predictable orchestrator detection. | No nested `.claude/` directories | Nested `.claude/` contains only CLAUDE.md (should be a plain subdirectory CLAUDE.md instead) | Nested `.claude/` contains rules, skills, agents, or settings (violates one-`.claude/`-per-config-home; nested rules/agents/settings are also dead config) |
| 21 | CLAUDE.md `@import` targets | CLAUDE.md `@path` imports do not reference files inside `.claude/` directories. Importing `.claude/` artifacts gives text-in-context only — no path-matching, no compaction survival, no invocability, no shell preprocessing. | No `@` imports targeting `.claude/` paths | — | `@import` references `.claude/rules/`, `.claude/skills/`, or `.claude/agents/` files |

## Location Test

For checks 12 and 14, apply: "If this content would be useful to someone who's never heard of Claude Code, it belongs in `docs/`, not `.claude/`."

## Source of Truth

This document defines what each check validates. The validation procedure (how to run the checks) is in `../skills/claude-config-validation/SKILL.md`.
