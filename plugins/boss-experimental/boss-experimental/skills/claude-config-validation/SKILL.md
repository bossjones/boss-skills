---
name: claude-config-validation
description: Validates a project's Claude Code configuration (CLAUDE.md, agents, skills, rules, commands) against knowledge-architecture doctrine. Use when asked to "validate CLAUDE.md", "check my .claude config", "audit agent/skill/rule placement", "lint the knowledge architecture", or before merging Claude config changes.
allowed-tools:
  - Read
  - Glob
  - Grep
---

# Claude Config Validation

Validates a project's Claude Code configuration against the knowledge architecture defined in `../../references/knowledge-architecture.md`.

## Input

- `project_path`: Path to the project directory (e.g., `apps/example-app`). Defaults to cwd.

## Check Definitions

Read `../../references/config-validation-checks.md` for the full reference table — what each check validates, and PASS/WARN/FAIL criteria. The checks are organized in six categories: Project Structure, Knowledge Placement, Skill Quality, Discoverability & References, Compliance Placement, Loading & Registration.

## Configuration

Two aspects of this skill are meant to be tuned per repository. Defaults are given; a repo may override them (e.g. in its own copy of this skill or in a `CLAUDE.md` note):

- **Monorepo-root markers** — the file/dir markers that identify the monorepo root (see Step 0). Default set: `.git`, `pnpm-workspace.yaml`, a `package.json` containing a `workspaces` field, `lerna.json`, `nx.json`. Adjust to match the repo's tooling.
- **Canonical agent roles** — the role names treated as root-owned (see Check 2). Default set: `architect`, `coder`, `test-writer`, `tester`, `reviewer`, `pr-submission`, `learner`. This is a recommended default, not a hard requirement — a repo may define its own role list (fewer, more, or differently named). Validate against whatever set the repo declares; fall back to the default when none is declared.

## Steps

### 0. Resolve Project Path

If no `project_path` argument was provided and cwd is the monorepo root, do NOT auto-validate root. Detect the monorepo root using the configurable marker set (default: a `.git` directory, `pnpm-workspace.yaml`, a `package.json` whose top-level object has a `workspaces` field, `lerna.json`, or `nx.json`). When at root, list available projects that have `.claude/` directories (e.g., `apps/example-app`, `apps/api`) and ask the user which project to validate. Root-level `.claude/` is the canonical home for the root-owned agents and shared config — validate it only when explicitly requested via `project_path`.

### 1. Locate Configuration

Find all Claude Code config files in the project:

- `{project_path}/CLAUDE.md`
- `{project_path}/.claude/agents/*.md`
- `{project_path}/.claude/skills/*/SKILL.md`
- `{project_path}/.claude/commands/*.md`
- `{project_path}/.claude/rules/*.md`

If no `.claude/` directory exists, report that the project has no Claude Code configuration and stop.

### 2. Run Project Structure Checks (1–3)

Read checks 1–3 from the check definitions doc. For each:

- **Check 1**: Verify `.claude/` exists
- **Check 2 (Canonical agents)**: List agents in `.claude/agents/`. The canonical roles (default: `architect`, `coder`, `learner`, `pr-submission`, `reviewer`, `test-writer`, `tester` — see Configuration) are root-owned. If validating the **repo root**, verify each declared canonical role is present, with role-appropriate frontmatter (read-only roles must not request write tools). If validating a **project**, it must NOT redefine any canonical role — a same-named project agent is shadowed by the root agent and never runs, so FAIL such collisions and renamed canonical roles (e.g. `implementer`→`coder`) and canonical platform-variants (`coder-mobile.md`). A project-prefixed custom agent (e.g. `myapp-coder`) is allowed (WARN, confirm intentional) only when the project declares a pipeline that invokes it. Pipeline declaration is an **optional, documented extension point**: if the project has a pipeline-declaration file (default convention: `.claude/pipelines.json` listing pipelines and the agents they invoke), read it and confirm the custom agent is referenced; a project-prefixed agent that no pipeline declares is a stray fork (FAIL). If the repo uses no pipeline mechanism at all, treat any project-prefixed custom agent as WARN (confirm intentional). Projects specialize via substrate (skills/rules with `paths`), not by forking agents.
- **Check 3**: Parse YAML frontmatter of each agent file. Validate required fields and permission/tool consistency.

### 3. Run Knowledge Placement Checks (4–7)

Read checks 4–7 from the check definitions doc. For each:

- **Check 4**: Scan agent body content for file-type conventions that belong in rules. Also check project-level rules for monorepo-wide conventions that belong in root `.claude/rules/` instead.
- **Check 5**: Compare CLAUDE.md content against agent body content for duplication.
- **Check 6**: Count lines in CLAUDE.md.
- **Check 7**: Parse rules frontmatter. Distinguish root-level rules (FAIL without `paths`) from project-level rules (WARN without `paths`).

### 4. Run Skill Quality Checks (10–14, 22)

Read checks 10–14 and 22 from the check definitions doc. For each skill in `.claude/skills/*/SKILL.md`:

- **Check 10**: Scan for fenced code blocks with language identifiers, external dependencies, large inline data.
- **Check 11**: Parse skill frontmatter. Check `description` exists and `allowed-tools` matches actual tool references in the body.
- **Check 12**: Verify directory structure follows `{skill-name}/SKILL.md` convention. Flag flat files and unexpected files.
- **Check 13**: Compare content across all `.claude/` files for blocks of 5+ consecutive near-identical lines.
- **Check 14**: Count lines per skill. For skills over threshold, scan for domain knowledge that should be extracted (checklists, API docs, templates, config instructions). Apply the location test.
- **Check 22 (opt-in)**: Only run this check when the repo has opted into eval coverage for its skills — it is NOT a universal mandate. When opted in, verify each skill directory contains an `eval/` subdirectory with `eval.yaml`: FAIL if `eval/` is missing; WARN if `eval/` exists but `eval.yaml` is missing. When the repo has not opted in, report this check as N/A.

### 5. Run Discoverability & Reference Checks (8–9, 15–18, 23)

Read checks 8–9, 15–18, and 23 from the check definitions doc. For each:

- **Check 8**: Scan agents for skill references, verify referenced skills exist.
- **Check 9**: If CLAUDE.md has a routing table, verify all file paths resolve.
- **Check 15**: For each skill and command found, verify it appears in the nearest CLAUDE.md. Do NOT flag a domain doc as missing from the routing table if a path-scoped rule (a rule with `paths` frontmatter) already references it — the rule is the loading mechanism and loads the doc on demand. Only agent/skill references require routing entries.
- **Check 23**: Inspect the CLAUDE.md routing table for context discipline. Flag (WARN) any routing row that lists multiple docs (joined by "and" or commas) instead of a single entry doc, and any doc that appears both in a path-scoped rule and in the routing table — the latter is redundant context tax; recommend keeping the rule and removing the routing-table entry.
- **Check 16**: Scan skills and commands for references to other skills/commands. Verify targets exist. Flag `/`-prefixed references where only a skill (not a command) exists. Exclude built-in Claude Code commands (`/plan`, `/init`, etc.) — these are runtime features, not project-defined.
- **Check 17**: If CLAUDE.md has a routing table, verify no entries point to other CLAUDE.md files. Entries may target any concrete destination — a domain doc, a package doc (`README.md`, `docs/DESIGN.md`), or a skill. The only FAIL is an entry pointing to another CLAUDE.md (a map pointing to a map).
- **Check 18**: For each task-recipe domain doc reachable from the routing table, scan for (a) essential steps delegated to secondary references (e.g., "for the required boilerplate, see X") and (b) conditional behavior (gating, eligibility, feature-flag predicates) described only in prose without an explicit, testable predicate. Warn if required steps are behind a second hop, or if decision logic is left to re-derive instead of stated as `enable when A AND B AND C` with terms and default defined. Do not apply to package architecture docs (`DESIGN.md`) — their bounded-context navigation/cross-linking is intentional.

### 6. Run Compliance Placement Check (19)

Read check 19 from the check definitions doc. For each skill:

1. Count declarative constraint statements — lines containing "must", "always", "never", "do not", "required" that impose conventions rather than describe procedure steps.
2. Count procedural steps — numbered actions, imperative instructions that produce an output or transform state.
3. Compute the ratio. If constraints outnumber procedural steps 2:1 or more, the skill is primarily a compliance document.
4. WARN if the skill would be more effective as a rule (rules shape plans from the start; skills only execute when invoked).

### 7. Run Loading & Registration Checks (20–21)

Read checks 20–21 from the check definitions doc.

1. **Check 20**: Glob for `.claude/` directories below the project root (e.g., `{project_path}/*/.claude/`, `{project_path}/**/.claude/`). For each nested `.claude/` found, check its contents:
   - Contains rules/, skills/, agents/, or settings.json → FAIL (dead config, never loaded)
   - Contains only CLAUDE.md → WARN (should be a plain subdirectory CLAUDE.md, not inside a nested `.claude/`)
2. **Check 21**: Scan all CLAUDE.md files (root and subdirectory) for `@` import references. If any `@` path resolves to a file inside a `.claude/` directory, FAIL — the import gives text only, no harness registration.

### 8. Format Output

```
## Claude Config Validation: {project_path}

| # | Check | Status | Details |
|---|-------|--------|---------|
| 1 | Config exists | PASS/FAIL | |
| 2 | Canonical agents | PASS/WARN/FAIL | [misplaced/missing agents] |
| 3 | Agent frontmatter | PASS/FAIL | [issues] |
| 4 | Convention placement | PASS/WARN | [conventions in agent prompts] |
| 5 | Duplication | PASS/WARN | [duplicated content] |
| 6 | CLAUDE.md size | PASS/WARN/FAIL | [N lines] |
| 7 | Rules frontmatter | PASS/WARN/FAIL | [issues] |
| 8 | Skill references | PASS/FAIL | [missing skills] |
| 9 | Routing table | PASS/FAIL/N/A | [broken references] |
| 10 | Skill content quality | PASS/FAIL/WARN | [code blocks, external deps, inline data] |
| 11 | Skill frontmatter | PASS/WARN | [missing frontmatter, tool mismatches] |
| 12 | Skill directory structure | PASS/FAIL/WARN | [flat files, unexpected files] |
| 13 | Cross-skill duplication | PASS/WARN | [duplicated content across files] |
| 14 | Skill size & separation | PASS/WARN/FAIL | [N lines, mixed concerns] |
| 15 | Routing table completeness | PASS/WARN | [skills/commands not in routing table] |
| 16 | Cross-file references | PASS/FAIL/WARN | [broken refs, /-prefix mismatches] |
| 17 | Routing table targets | PASS/FAIL | [entries pointing to CLAUDE.md] |
| 18 | Domain doc self-containment | PASS/WARN | [essential steps behind secondary refs] |
| 19 | Compliance placement | PASS/WARN | [skills that should be rules] |
| 20 | Nested `.claude/` directories | PASS/WARN/FAIL | [nested dirs with dead config] |
| 21 | CLAUDE.md `@import` targets | PASS/FAIL | [@imports targeting .claude/ paths] |
| 22 | Skill eval present | PASS/WARN/FAIL/N/A | [opt-in; missing eval/ or eval.yaml] |
| 23 | CLAUDE.md context discipline | PASS/WARN | [multi-doc rows; rule docs duplicated in routing table] |

## Issues

### FAIL
- [file:detail]

### WARN
- [file:detail]

## Recommendations
- [actionable suggestion]
```
