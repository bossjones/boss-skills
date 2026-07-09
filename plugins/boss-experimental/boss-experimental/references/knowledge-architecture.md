# Claude Code Knowledge Architecture

A cheatsheet for deciding where knowledge lives across Claude Code's five knowledge facilities.

---

## The Five Knowledge Facilities

```
┌──────────────────────────────────────────────────────────────┐
│  KNOWLEDGE                                                    │
│                                                               │
│  CLAUDE.md ──→ Agent ──→ Skill ──→ Domain Doc                │
│  (context)    (role)   (procedure)  (recipe)                  │
│                                                               │
│  Rules (.claude/rules/)                                       │
│  Path-scoped instructions that compose with all of the above  │
│                                                               │
├──────────────────────────────────────────────────────────────┤
│  ENFORCEMENT                                                  │
│                                                               │
│  Hooks (pre-tool, post-tool, pre-commit, session-start)       │
│  Mechanical guardrails that run regardless of agent intent    │
│                                                               │
├──────────────────────────────────────────────────────────────┤
│  CAPABILITIES                                                 │
│                                                               │
│  Plugins (MCP Servers)                                        │
│  External service access with structured I/O and scoped auth  │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

| Facility | What it is | Scope | Loaded when |
|----------|-----------|-------|-------------|
| **CLAUDE.md** | Project context — structure, conventions | Entire project | Ancestors at launch; subdirectories on demand |
| **Rules** | Path-scoped instructions (`.claude/rules/*.md`) | File types or directories | Unconditionally at launch, or when matching files are opened (`paths` frontmatter) |
| **Agent** | Role definition — tools, workflow, output type | One role | When that agent is invoked (discovered at session start) |
| **Skill** | Reusable procedure — ordered steps with verification. User-invokable via `/skill-name`. | Cross-cutting | On `/`-invocation, `description` match, or `paths` frontmatter match (body lazy-loads on use) |
| **Domain Doc** | Domain-specific recipe — patterns, gotchas, examples | One task type | When a skill or agent references it |
| **Hook** | Shell command triggered by Claude Code events | One constraint | Automatically on matching event |
| **Plugin** | MCP server providing external service access | One integration | When agent calls the plugin's tools |

---

## Placement Test

When new knowledge needs a home, ask these in order. First "yes" wins.

```
Q1: Does every agent need this on every task?           → CLAUDE.md
Q2: Does this apply only to specific file types/paths?  → Rule (.claude/rules/ with paths frontmatter)
Q3: Does this define a role's tools or workflow?        → Agent
Q4: Is this a reusable multi-step procedure?            → Skill
Q5: Is this a recipe for a specific domain task?        → Domain Doc
Q6: Can violation be mechanically detected?             → Hook
Q7: Does this require external service access?          → Plugin
```

| Signal | Goes in | Why |
|--------|---------|-----|
| Project-wide convention | CLAUDE.md | Every agent reads it |
| Convention scoped to file types or paths | Rule (`.claude/rules/`) | Loaded only when relevant files are touched |
| Role with specific tools and workflow | Agent | Defines a persona |
| Multi-step procedure used across tasks | Skill | Reusable, composable, user-invokable via `/` |
| Recipe for one type of domain task | Domain Doc | Specific, evolvable |
| Constraint with concrete consequences | Hook | Mechanical enforcement |
| External service integration | Plugin | Structured I/O, scoped auth |
| One-time fix or workaround | **Nowhere** | Let it die |
| Pattern that recurs 3+ times | Promote to Skill or Doc | Proven through repetition |

### Three-Occurrence Rule

Don't encode on first discovery. 1st = anomaly. 2nd = coincidence. 3rd = pattern. Only on the third occurrence does knowledge earn a permanent home.

---

## Knowledge Layers in Detail

### CLAUDE.md — The Map

Treat it like expensive context window real estate. Target under 200 lines per file.

**`CLAUDE.md` (file) is not `.claude/` (folder).** They share a name and get conflated; their placement rules are opposite. `CLAUDE.md` is context for a folder — it can live at **any depth** (root, project, any subfolder), as many as are useful. `.claude/` is harness-loaded config (rules, skills, settings, root agents) with restricted placement — **one per config home + monorepo root, never deeper** (see Monorepo Scoping). Adding a subfolder `CLAUDE.md` is normal; adding a subfolder `.claude/` is the nested-`.claude/` anti-pattern.

**Loading**: CLAUDE.md files in ancestor directories (from cwd upward) load at launch. CLAUDE.md files in subdirectories load on demand when Claude reads files there — specifically, only the **Read** tool triggers subdirectory loading. `cd` alone does not trigger discovery. Other tools (Bash, Glob, Grep) that touch files do **not** trigger CLAUDE.md or rules. Edit and Write require a prior Read of the target file (Write only when overwriting), so subdirectory CLAUDE.md and `paths`-scoped rules load before the edit fires. User-level `~/.claude/CLAUDE.md` loads always.

**Put here**: project structure, build/test/lint commands, code conventions, architecture overview, domain routing table.

**Routing tables are for domain docs and skills.** Domain docs always need routing entries — without them, agents don't know they exist. Skills can have routing entries to help agents match tasks to procedures. Agents never need routing entries (auto-discovered via `description` frontmatter).

**Never route to other CLAUDE.md files.** Routing table entries must point to domain docs or skills — never to another CLAUDE.md. CLAUDE.md files have their own loading mechanism (ancestors at launch, subdirectories on Read). Routing to them creates a parallel loading path that conflicts with the built-in one, and forces agents to hop through indirection to find actual knowledge. Maps should point to destinations, not to other maps.

**Subdirectory CLAUDE.md files must add new context.** Don't create a subdirectory CLAUDE.md that just points to the parent CLAUDE.md or lists rules — ancestors load automatically and rules activate via `paths` frontmatter. Only create one when the subdirectory has genuinely different conventions (e.g., `mobile/CLAUDE.md` with "use the mobile build target, mobile-specific conventions").

**Nested directories: only CLAUDE.md and skills lazy-load; rules, agents, and settings do not.** In a subdirectory, that directory's CLAUDE.md (on Read) and its `.claude/skills/` (on demand) are picked up; settings, rules, commands, and agents are ignored unless Claude Code launches from there (or `--add-dir`). The one-`.claude/`-per-config-home mandate below is governance discipline, not a platform limit — see the nested-directory anti-pattern.

**Anti-pattern — `@import` of `.claude/` artifacts**: CLAUDE.md supports `@path/to/file` imports, but importing `.claude/rules/`, `.claude/skills/`, or `.claude/agents/` files gives text-in-context only — no harness registration. Path-matching won't trigger, compaction survival won't work, skills won't be invocable, shell preprocessing won't run. The result is rules that work intermittently (present until compaction, then gone) or skills missing their core mechanics. Import `docs/` files freely; never import `.claude/` artifacts.

**Don't put here**: step-by-step procedures (→ skill), domain-specific recipes (→ domain doc), file-type-specific rules (→ `.claude/rules/`).

**Size discipline**: If a section exceeds 20 lines, ask: does the narrowest agent (e.g., tester — which only runs tests and reports results) need all of this? If not, it's not universal context. Extract to a rule, doc, or skill — leave a one-line pointer.

### Rules — Path-Scoped Instructions

`.claude/rules/*.md` files organize instructions that are too specific for CLAUDE.md but too general for a skill. They support `paths` frontmatter for file-pattern activation.

```markdown
---
paths:
  - "src/api/**/*.ts"
---
# API rules: all endpoints must include input validation...
```

| Frontmatter | Behavior |
|-------------|----------|
| No `paths` field | Loaded unconditionally at launch (same as CLAUDE.md) |
| `paths: ["**/*.ts"]` | Loaded when Claude reads a matching file |

**`paths` is a loading trigger, not a scope enforcer.** Once a path-scoped rule loads into context (triggered by a Read on a matching file), it stays in context for the rest of the session and influences all subsequent work — including edits to files that don't match the pattern. After context compaction, path-scoped rules are evicted until a matching file is read again. Mitigations: (1) add self-scoping language in the rule body ("Apply ONLY when editing `*.ts` files"), (2) for directory-bound conventions, prefer subdirectory `CLAUDE.md` over path-scoped rules — it reloads more reliably after compaction, (3) for hard constraints, use hooks.

**Use rules for**: coding standards scoped to file types, domain conventions tied to directory paths, guidelines that don't need to be in every session.

**Don't use rules for**: multi-step procedures (→ skill), tool-agnostic domain knowledge (→ `docs/`), constraints that need enforcement (→ hook).

**Rules vs CLAUDE.md — the common ambiguous case**: "All React components must use functional syntax." This applies to `*.tsx` files only. Put it in a rule with `paths: ["**/*.tsx"]`, not CLAUDE.md. The tester agent working on shell scripts doesn't need it in context. If it applies regardless of file type — like "use American English in all strings" — it goes in CLAUDE.md.

**Rules shape plans; skills execute later.** In plan mode, rules are in context and influence which steps Claude designs. Skills are referenced as steps to run but don't shape the plan itself. Compliance that should be baked in from the start (copyright headers, naming conventions) → rule. Post-hoc verification ("run security audit after implementation") → skill. For compliance rules that must shape all plans in a project, use broad `paths` or omit `paths`. Keep the bar high for root-level broad rules — they load for every developer in the monorepo.

**Enforcement ladder — match constraint severity to facility:**

| Severity | Facility | Behavior |
|----------|----------|----------|
| MUST (violation = incident) | Hook | Harness-enforced, zero trust, survives compaction |
| SHOULD (violation = defect) | Rule (unconditional) | Always in context, shapes plans, survives compaction |
| SHOULD (file-scoped) | Rule (path-conditional) | In context when matching files read, evicted on compaction |
| CONTEXT (good to know) | CLAUDE.md | Always in context, shapes all work |
| ON-DEMAND | Skill | Loaded when invoked, budget-limited after compaction |

Critical constraints ("must never expose PII", "required by security policy") in path-conditional rules will silently disappear after compaction. If the constraint has real consequences, make it unconditional or use a hook.

Rules support symlinks for sharing across projects and recursive subdirectory organization.

**Anti-pattern — conventions in agent prompts**: File-type-scoped conventions (copyright headers, import style, naming patterns) belong in rules, not repeated in every agent. Rules compose with all agents automatically. Agent prompts duplicated N times rot N times faster.

**Anti-pattern — monorepo-wide conventions in config-home rules**: Conventions that apply across the monorepo (copyright headers, `import type`, build-tool conventions) belong in root `.claude/rules/` with `paths` frontmatter (e.g., `paths: ["**/*.ts", "**/*.tsx"]`), not duplicated in each config home's `.claude/rules/`. A config home's rules should contain only what's genuinely specific to it.

### Commands (Legacy — Use Skills Instead)

Commands (`.claude/commands/`) and skills (`.claude/skills/`) both create `/foo` entry points. Skills are the recommended path — they support directories, frontmatter controls (`user-invocable`, `disable-model-invocation`), and agent auto-discovery. Existing commands keep working.

### Agents — Roles, Not Domains

An agent defines a role (tools, workflow, output type). Not a domain. Within any one config home, there is exactly one agent per role — no platform or domain variants.

- **Right**: One `coder` role (the canonical root agent), with platform variation in CLAUDE.md + rules + docs
- **Wrong**: `coder-mobile` and `coder-web` in the same project

#### Standard Agent Set

The standard roles below are a **recommended default set**, not a fixed requirement — a repo may adopt fewer, more, or differently named roles. When used, these roles live at the **monorepo root** `.claude/agents/` as generic, project-agnostic definitions, and every config home inherits them via discovery (which walks up from cwd). A config home does **not** redefine them by default — it gets the canonical set for free. What matters is that the roles, tool lists, and permission modes are consistent — and keeping the single root copy is what guarantees that.

| Agent | Tools | permissionMode | Output |
|-------|-------|----------------|--------|
| **architect** | Read, Glob, Grep, Write | bypassPermissions | Design doc, component boundaries, API contracts |
| **coder** | Read, Write, Edit, Bash, Glob, Grep | bypassPermissions | Code changes |
| **test-writer** | Read, Write, Edit, Bash, Glob, Grep | bypassPermissions | Test files |
| **tester** | Read, Bash, Glob, Grep | bypassPermissions | Pass/fail report |
| **reviewer** | Read, Bash, Glob, Grep | bypassPermissions | Review feedback |
| **pr-submission** | Read, Bash, Glob, Grep | bypassPermissions | Commit, branch, PR |
| **learner** | Read, Write, Edit, Bash, Glob, Grep | bypassPermissions | Config/doc updates from run learnings |

All agents use `bypassPermissions` because they are designed for orchestrated (subagent) execution. The **tool list is the permission boundary** — reviewer/tester can't write files, architect can only Write docs. Agents with `default` or `acceptEdits` fail silently when spawned as background subagents (Bash prompts get auto-denied), causing duplicated work and wasted tokens. For interactive sessions, use `auto` mode at the session level instead — it overrides agent `permissionMode` with a background safety classifier.

One agent per role. No platform variants (e.g., `coder-mobile` and `coder-web`) — platform variation is handled through CLAUDE.md hierarchy, rules, and domain docs.

The root agents are generic by construction — no hardcoded project paths, package names, or skill names. Domain knowledge they need at runtime comes from the substrate (the config home's CLAUDE.md, docs, and path-scoped rules/skills), not from a per-config-home copy of the agent. A config home overrides a canonical role only when it genuinely can't be served by substrate alone; that override is the **exception**, lives in the config home's `.claude/agents/`, and is **domain-prefixed** (e.g. `example-coder`) so it doesn't shadow the root role. (Governance agents are a separate category — see the Rules section below.)

The architect→coder handoff matters: architect decides scope and approach (cross-module, writes design docs only), then coder implements (read/write, single module). This prevents the "jump straight to code" failure mode.

**Rules:**
- The standard roles live once at the monorepo root and every config home inherits them. A config home does not copy or redefine them just to use them.
- A config home may add *additional* agents for genuinely unique roles (e.g., a `migration` agent for database schema work), and may override a canonical role only as a justified exception — domain-prefixed (`example-coder`), never a same-name shadow of the root role.
- Within any one config home, there is exactly one agent per role. If it feels it needs a variant coder, the variation belongs in CLAUDE.md, a rule, or a domain doc — not a second agent.
- **Governance agents** also live at root `.claude/agents/`, alongside the canonical roles but in a separate category. These are cross-cutting roles that operate on `.claude/` *configurations* (e.g., reviewing config structure against the knowledge architecture), not on *code*. They are read-only, do not count toward the standard set, and are owned by the platform team.

#### Agent Definition Structure

The canonical agent file has two parts: standard config (frontmatter) and a **generic, project-agnostic** body. It names no app, package, or language — everything domain-specific is derived at runtime from the substrate (CLAUDE.md, docs, rules) of whatever config home it runs in.

```yaml
---
name: coder
description: Use when implementing features or fixing bugs
tools: [Read, Write, Edit, Bash, Glob, Grep]
permissionMode: bypassPermissions
maxTurns: 50
---

You are the coder. Implement features and fix bugs in whatever
codebase you're invoked in.

## Workflow
1. Read task requirements
2. Check routing table in CLAUDE.md — load relevant domain docs
3. Read a source file in the target directory (triggers subdirectory CLAUDE.md loading)
4. Implement following the conventions the substrate gives you
5. Run the build the way CLAUDE.md/docs prescribe
6. Self-review against conventions in CLAUDE.md and active rules
```

The single root copy serves every config home. A config-home override (the exception) keeps the same frontmatter shape but is renamed with a domain prefix (`example-coder`) and adds only the framing substrate can't supply.

**`permissionMode` must match execution context.** All standard agents use `bypassPermissions` because they run as subagents in orchestrated workflows. The tool list (not `permissionMode`) is the safety boundary. When the parent session uses `auto` mode, agent `permissionMode` is ignored entirely — the session-level classifier handles all approvals.

#### How Platform Variation Works Within a Config Home

The canonical (root) coder working on the mobile build in `example-app` sees:

```
coder.md (root, generic)              ← the canonical role definition, inherited
  + root CLAUDE.md                    ← monorepo conventions
  + apps/example-app/CLAUDE.md        ← config-home conventions, routing table
  + apps/example-app/mobile/CLAUDE.md ← mobile build targets, mobile conventions (lazy-loaded on Read)
  + .claude/rules/mobile.md           ← paths: ["**/*.mobile.ts"] — mobile coding standards
  + docs/mobile-development.md        ← mobile recipes (loaded via routing table)
```

The same generic coder working on web sees different context from the same layers — different CLAUDE.md, different rules, different docs. **Same root agent, different substrate, different knowledge** — which is exactly why the agent itself doesn't need a per-config-home copy.

#### Agent Discovery

Agent discovery walks **up** from cwd, accumulating agents from all `.claude/agents/` directories in the ancestor chain. When the same agent name exists at multiple levels, the closest (deepest) wins — there is no merging of individual agent files across levels. **Because same-name resolution across levels has shown inconsistencies in current Claude Code, config-home overrides are domain-prefixed (`example-coder`) rather than same-name (`coder`)** — a prefixed name resolves predictably and never silently shadows the root role.

| Source | Priority | Notes |
|--------|----------|-------|
| `--agents` CLI flag (inline JSON) | 1 (highest) | Session-only |
| `.claude/agents/` (accumulates walking up) | 2 | Closest wins for name conflicts |
| `~/.claude/agents/` (user-level) | 3 | Personal agents |
| Plugin agents | 4 (lowest) | From installed plugins |

Example (recommended pattern): root has the canonical roles plus `config-reviewer`. A config home adds `example-coder` (a domain-prefixed override) and `product-manager` (a unique role). Launching from the config home, discovery accumulates all of them — the canonical roles and `config-reviewer` from root, plus the two local ones. Because the local additions are uniquely named, nothing shadows a root role and resolution is unambiguous. (Same-name resolution — a local `coder` overriding root's — is what's buggy and what the domain-prefix convention avoids.)

Directories added with `--add-dir` grant file access only — they are NOT scanned for agents.

**Locally:** developers launch Claude Code from the config home. The canonical roles are discovered by walking up to root; any local additions come along too. No `--agents` flag needed for the standard roles.

**Remotely:** an orchestrator — a platform layer that sequences agents deterministically in remote environments — sets cwd to the config home so the canonical roles resolve by natural walk-up, or injects via `--agents` CLI flag (highest priority). Governance agents are injected separately when the orchestrator runs configuration validation.

#### Routing Table

Agents route to domain knowledge via a routing table in CLAUDE.md:

```markdown
## Domain References (in CLAUDE.md)
| Task involves... | Read first |
|------------------|------------|
| New component | `packages/components/docs/creating-a-component.md` |
| UI component | `apps/example-app/docs/adding-a-ui-component.md` |
| Service integration | `packages/components/docs/service-integration.md` |
```

The table lives in CLAUDE.md so every agent sees it. It's small (one line per domain). The knowledge itself lives in tool-agnostic `docs/` directories owned by the relevant team.

### Skills — Generic vs. Domain

Skills come in two types. Both are valid. Don't mix them.

**Generic** (portable across projects):
- `tdd-methodology` — works in any codebase
- `systematic-debugging` — works in any codebase
- `security-review` — works in any codebase

**Domain** (specific to this project):
- `component-creation` — component lifecycle, locator patterns
- `ui-component-creation` — custom elements, base classes

A domain skill may reference a generic skill as a sub-step ("invoke tdd-methodology for step 5"). A generic skill must never contain project-specific patterns. If it accumulates them, extract to a domain doc.

**Orchestrator skills** (e.g., `run-pipeline` that sequences architect → coder → test-writer → tester → reviewer → pr-submission) legitimately need the `Agent` tool in `allowed-tools` to spawn subagents. Regular skills should not include `Agent` — if a skill needs another agent, the calling session should invoke it.

#### Skill Activation

A skill can activate three independent ways, composable on one SKILL.md:

- `/skill-name [args]` — explicit invocation (the legacy command path; args live here)
- `description` match — Claude auto-invokes when the prompt/context fits the description
- `paths` frontmatter — auto-loads when you work with files matching the glob (same format as rule `paths`)

`paths` is an **auto-activation trigger, not a scope boundary** — it gates *when* the skill loads, not what it operates on, and doesn't block `/`-invocation. **Rules vs. skills isn't decided by `paths` (both support it), but by content:** a rule loads resident knowledge that stays in context; a skill's body loads only when invoked.

**A CLAUDE.md routing entry does not scope a skill either.** Referencing a skill from a folder's CLAUDE.md aids discovery; it does not confine the skill to that folder or prevent it activating elsewhere. Activation is governed only by the three triggers above. To limit a skill to part of the tree, put `paths` on the skill — don't rely on which CLAUDE.md points at it. (This is why a feature doesn't need its own `.claude/` to "scope" its skills: keep the skill in the config home's (or root) `.claude/skills/` with `paths`, and give the feature a CLAUDE.md for context.)

#### Files in Skill Directories

A skill directory can contain more than SKILL.md.

| File type | Example | Belongs? | Why |
|-----------|---------|----------|-----|
| Templates | `component-template.ts` | Yes | Inert boilerplate the agent fills in |
| Reference examples | `example-component.ts` | Yes | Concrete model from the real codebase |
| Skill-internal references | `references/output-format.md`, `references/step-rubric.md` | Yes — in `references/` | Material only meaningful inside this skill (verdict template, sub-agent rubric). Real files, not symlinks. |
| Domain docs in disguise | Coding conventions, workflow guides | No — move to `docs/`, reference by path | If useful to humans outside the skill, it's a domain doc. Skill steps cite the `docs/` path directly. No symlinks from `references/` to `docs/`. |
| Config fragments | `owners.yml`, `tsdoc.json` | Yes | Data the agent applies verbatim |
| Scripts with logic | `validate-component.sh` | No — move to codebase | Needs tests, review, versioning. Must never rely on system dependencies (node, python, etc.) — use hermetic, project-managed toolchains only. |
| Scripts that duplicate agent tools | `commit-and-push.sh` | No — use SKILL.md instructions | Agent already knows how |
| Scripts with external deps | `query-db.py` (imports `requests`) | No | Breaks portability across environments |
| External service calls | `create-ticket.sh` | No — use MCP server | Auth, endpoints, and I/O belong in the Plugin layer |

**Decision test**: Does this file create a dependency that skill users don't control? If yes, it doesn't belong.

**Growth signal**: Script accumulates conditionals and error handling → promote to `bin/` or `scripts/` with a test target. Skill references by path.

**External services**: The skill says *when* and *what* (create a ticket with this info). The MCP server handles *how* (auth, endpoints, structured I/O). One integration serves all skills, and portability between local and SaaS is preserved.

#### Eval

A skill can be covered by an `eval/` directory that tests it against known inputs and verifies correct output. This is **opt-in**, not a universal mandate — apply it where silent regressions would be costly (root-level skills, skills that reference external docs). Integration wrappers that delegate to MCP servers typically don't need evals.

An eval has three parts:

- **Fixtures** — minimal input directories, each isolating one scenario (one "known good", the rest triggering specific failure modes). Think unit-test cases.
- **Graders** — scripts that inspect the skill's output and emit `{"score": 1.0, "details": "..."}` or `{"score": 0.0, "details": "..."}`. Most are deterministic shell scripts (pattern matching). For subjective quality checks, `llm_rubric` graders send the output to an LLM for scoring. Tasks can have multiple weighted graders.
- **eval.yaml** — ties fixtures to instructions and graders. The runner reads this file, feeds each fixture to an agent, then scores the output.

Run evals locally with `/run-skill-eval <skill-path>` inside Claude Code — it handles both deterministic and `llm_rubric` graders. In CI, `run_eval.sh` delegates to [skillgrade](https://www.npmjs.com/package/skillgrade) + `ANTHROPIC_API_KEY`.

### Domain Docs — The "ADDING A BUTTON.md" Pattern

Domain recipes are **project knowledge**, not tool knowledge. They live in tool-agnostic `docs/` directories relative to the area they describe — not inside `.claude/`. This keeps them discoverable by humans, usable by any AI tool, and owned by the team that owns the code.

```
packages/components/docs/
├── creating-a-component.md
├── service-integration.md
└── config-and-feature-flags.md

apps/example-app/docs/
├── adding-a-ui-component.md
├── adding-a-locale.md
└── worker-communication.md
```

**The location test**: If the doc would be useful to someone who has never heard of Claude Code, it doesn't belong in `.claude/`.

**How they get loaded**: A routing table in CLAUDE.md points to the doc. A skill step can also reference it directly. Either way, the doc enters context only when the task matches.

**Domain doc template**:

```markdown
# [Task Name]

## Owner
Team or person responsible for keeping this accurate.

## When to Use This
One sentence.

## Prerequisites
What must exist before starting.

## The Recipe
Numbered steps. Concrete. Copy-pasteable.

## Common Mistakes
What goes wrong and why. From real debugging sessions.

## Example
Minimal, complete, from the actual codebase.

## Last Updated
Date and what changed.
```

**Promotion path**:

```
Pattern recurs 3x → engineer adds doc → update routing table in CLAUDE.md
```

**Domain docs must be self-contained for essential steps.** When a domain doc references other docs, Claude decides at runtime whether to follow — there is no automatic recursive loading. Traversal depth is proportional to task complexity, not doc structure. A simple task may stop at the first doc; a complex one may follow 2–3 references. This means: put everything essential in the first doc the routing table points to. References to other docs are for edge cases and deeper understanding, not for required steps. If every component creation requires understanding the lifecycle, put the lifecycle in the component creation doc — don't make it a second hop that Claude might skip.

**Self-containment covers decision logic, not just steps.** When a task has conditional behavior — gating, eligibility, feature-flag predicates — the doc must state the activation condition as an explicit, testable predicate, not leave it to be re-derived from a ticket title or tribal knowledge. State it as `enable when A AND B AND C`, define each term, and define the default. Prose like "for first-time desktop users" gets re-interpreted differently on every run — agents will silently drop a condition nothing authoritative pinned down. (Observed: three independent runs of the same experiment ticket produced three different gating predicates because the predicate lived only in the ticket title.) A recipe that documents *how* to wire a flag but not *when* it should fire is not self-contained.

**Route by task, not topic.** Domain docs are organized around what a developer does (creating a component), not concepts (component registry, component types). Concept docs stay as reference; task docs inline the essential steps and link to them for depth. This keeps the routing table stable — a new reference doc becomes a link under a task doc, not a new CLAUDE.md row. A row per concept means the granularity is wrong.

### Hooks — Enforcement Layer

Hooks enforce constraints mechanically. Instructions can be ignored under context pressure. Hooks can't.

**Scope**: Hooks only run inside Claude Code. They don't replace git hooks or CI checks — a developer using another editor or no AI tool bypasses them entirely. Use hooks for fast local feedback to the Claude Code user. Use git hooks and CI for universal enforcement. They're complementary layers, not alternatives.

| Hook Type | Purpose | Example |
|-----------|---------|---------|
| **Pre-tool** | Validate before execution | Block writes outside target package |
| **Post-tool** | React after execution | Run lint after every file edit |
| **Session start** | Set up environment | Verify build config exists |
| **Pre-commit** | Validate before commit | Reject out-of-scope files |

**When to use a hook vs. an instruction**:

| Constraint type | Instruction | Hook |
|-----------------|-------------|------|
| Judgment call ("prefer small functions") | Yes | No |
| Hard constraint ("don't edit generated files") | Yes, for awareness | **Also a hook** |
| Automated action ("typecheck after edit") | Fragile | **Hook** — but consider cost. If the action is expensive (e.g., multi-minute lint transpile), defer to pre-commit or CI, not every edit. |

**Rule of thumb**: If violation has immediate concrete consequences (broken build, security exposure, scope breach), enforce with a hook. If it's a quality preference, leave as an instruction.

**Cost heuristic for post-tool hooks**: A hook that runs after every file edit must complete in under 5 seconds. If it takes longer — full project lint, transpilation, integration tests — move it to pre-commit or CI. Post-tool hooks should be scoped (single-file lint, type-check the changed file) not global.

#### Committing a hook (the pattern)

A committed hook in `.claude/settings.json` runs for **everyone, in every environment Claude Code runs** — not just the author's machine. A committed hook must therefore:

- **Be opt-in-gated as its first step** unless it's a true must-apply-to-all constraint. Gate on an env var set in personal `settings.local.json` (`[ "$MY_HOOK" = "1" ] || exit 0`). This is what makes a committed/root hook acceptable — people who didn't opt in pay ~nothing. A committed hook that *isn't* opt-in-gated must clear a genuine "near-everyone wants this, always" bar.
- **Gate on every external dependency it uses** (`command -v jq`, file-exists for a built artifact). Don't assume `jq`, `node`, a built artifact, or any non-base tool exists — a clean or remote checkout may not have it. Missing dependency → skip gracefully (a one-line hint to stderr), never error.
- **Be non-blocking and safe to run unattended** — `exit 0` on every path, never block the edit, no unbounded side effects.

**Governance split:** the hook *script* is committed and reviewed (`.claude/hooks/foo.sh`); the *activation* is personal (`settings.local.json`, gitignored). Ship the script via a `.gitignore` allow-list (un-ignore `.claude/settings.json` and the specific hook file) so the governed script ships while personal config stays out. Logic beyond a few gated steps belongs in a tested `bin/`/`scripts/` file the hook shim calls, not inline in the `.sh`.

*Reference implementation: an opt-in `prettier-on-edit` hook — opt-in gate first, gates on `jq`/`node`/built-output, `exit 0` throughout, gitignore allow-list.*

### Plugins (MCP Servers) — Capability Layer

Plugins provide structured access to external services. They don't contain knowledge — the *when* and *how* lives in agents and skills.

| Plugin | Provides | Used By |
|--------|----------|---------|
| GitHub MCP | PR creation, review comments | pr-submission, review agents |
| Slack MCP | Status updates, escalation | loop controller |
| Ticket-tracker MCP | Ticket updates, transitions | pr-submission agent |
| Custom MCP | Build-graph query, dependency graph | coder, tester agents |

**Plugins vs. Bash**: Both can run `gh pr create`. Plugins add structured I/O (no shell parsing), scoped permissions (restrict to specific operations), and credential isolation (token not visible to Bash). Use Bash for POC, plugins for production.

---

## Composition Flow

```
User request (or /skill as entry point)
  → Agent (role + workflow)
    → reads CLAUDE.md (project context + routing table, ancestors at launch)
    → Rules activate when matching files are touched (path-scoped)
    → checks routing table → loads Domain Doc if task matches
    → invokes Skill (reusable procedure)
      → Skill references Domain Doc (specific recipe)
      → Skill references another Skill (composition)
    → Hook fires on each tool call (enforcement)
    → Plugin called for external service (capability)
```

Each layer adds specificity. CLAUDE.md says "we use components" and where to find the docs. The agent says "I implement components." The skill says "here's how, step by step." The domain doc says "here's the exact pattern for a component that wraps a service API."

### Worked Example: `/new-component`

```
1. User types `/new-component camera-roll`
2. Skill (.claude/skills/new-component/SKILL.md) activates:
   "Create a new component named {name}."
3. Coder agent activates (role: implement)
4. Agent reads CLAUDE.md → sees routing table → loads docs/creating-a-component.md
5. Agent follows skill steps:
   Step 1: Copy component-template.ts from skill directory
   Step 2: Register in component-locator.ts
   Step 3: Add OWNERS file from config fragment
   Step 4: Run the build for the new package
6. Rule (.claude/rules/api-validation.md, paths: ["src/api/**/*.ts"]) activates
   when agent creates the service file
7. Hook (post-tool) runs single-file lint on each written file
8. Agent self-reviews against CLAUDE.md conventions
```

Four facilities contributed context. No single one had the full picture.

---

## Monorepo Scoping

In a monorepo, `.claude/` config lives at two levels: the monorepo root and a **config home** (an independently built/versioned/owned unit — see `.claude/` Directory Depth). Don't go deeper. (Docs and CLAUDE.md are a separate axis — they follow the code at any depth.)

### Scoping Rules

| Facility | Where it lives | Why |
|----------|---------------|-----|
| **Agents (canonical)** | Root `.claude/agents/` (the standard set) | Generic, project-agnostic. Every config home inherits them via discovery; domain framing comes from substrate, not a copy. |
| **Agents (config-home override)** | Config home `.claude/agents/` | Exception only — a domain-prefixed role (`example-coder`) when substrate can't carry the difference. Never a same-name shadow of a root role. |
| **Agents (governance)** | Root `.claude/agents/` | Cross-cutting governance roles that operate on `.claude/` configurations, not code. These are NOT code-role agents — they don't write code, review features, or submit PRs. Example: `config-reviewer` (evaluates `.claude/` configurations against the knowledge architecture). |
| **Skills (generic)** | Monorepo root `.claude/skills/` | Portable across config homes (security-review, TDD). Promote when generic + 3 teams need it. |
| **Skills (domain)** | Config home `.claude/skills/` | References app-specific patterns, files, conventions. |
| **Skills (team)** | Root `.claude/skills/teams/<team>/` | For teams whose code spans multiple config homes, when there's no single config home `.claude/` to host the skill. See "Team Scoping" below. |
| **Hooks** | Config home by default, root if universal enforcement | A monorepo-wide "never edit generated files" hook may qualify for root. |
| **Rules** | Config home `.claude/rules/` by default | Path-scoped instructions. Use `paths` frontmatter for file-type scoping. |
| **Rules (root)** | Root `.claude/rules/` — protected | Must have `paths` frontmatter. Requires platform-team review. Rules without `paths` at root load unconditionally for every developer in the monorepo. |
| **Rules (team)** | Root `.claude/rules/teams/<team>/` | For teams that own code spanning multiple projects (e.g., a team owns `apps/team-app/` + `platform/shared/module-*/`). Must have `paths` frontmatter. Each team owns their guardrails independently. See "Team Scoping" below. |
| **Domain docs** | `docs/` in the package that owns the API (tool-agnostic). For team-owned docs spanning multiple projects, `docs/teams/<team>/` follows the same shape. | Single source of truth. Consumer points, never copies. |
| **CLAUDE.md** | Both levels (hierarchical) | Root = shared conventions (loaded at launch). Subdirectory = loaded on demand. |
| **CLAUDE.md (root)** | Root `CLAUDE.md` — protected | Requires platform-team review. Changes affect every session in the monorepo. |

### `.claude/` Directory Depth

`.claude/` lives at exactly two kinds of place: the **monorepo root** and a **config home**. Nowhere else.

Two terms, defined on different criteria — don't conflate them:

- **Project** — what a team owns and works in as a unit (the everyday "the thing my team builds"). Defined by **ownership**, and it's a loose unit: the same team can own multiple projects, two teams can co-own one, and a project may be an app, a feature area shared across apps (`features/edu`), or a platform module (`platform/shared/module-*`). A project carries **no `.claude/` placement rule on its own** — its conventions are expressed through review-ownership + path-scoped rules/skills, not by a `.claude/` per project.
- **Config home** — an **independently built, versioned, and owned unit with its own dev loop** — the thing you'd launch Claude Code (or the orchestrator) at. This is broader than "deploys to prod": it includes apps and services **and published libraries** (e.g. `@example/shared-ui`). It is the **only** place (besides the monorepo root) a `.claude/` may live — **at most one**, and only if the unit needs one (being eligible doesn't mean it should have one — see opt-in below). Examples: `apps/example-app`, `services/example-service`, `packages/shared-ui`.

In the common case a single-team app, service, or library is **both** — same directory. They diverge when one config home is built by many teams (e.g. `apps/mega-app`): one config home, many projects. A subfolder that only compiles *into* its parent (never built/consumed independently) is not its own config home — its behavior goes into path-scoped rules within the parent's `.claude/`. A grouping folder that just contains other packages (e.g. `platform/grouping`, which holds ~20 separate libraries) is not itself a config home — each independently-published package under it can be.

**A `.claude/` is opt-in, not mandatory — eligibility is not a reason to add one.** Being a config home only makes a unit *allowed* to have a `.claude/`; most should not. Most config homes run fine on the monorepo-root `.claude/` (discovery walks up) plus their own `CLAUDE.md`, `docs/`, and path-scoped rules. Add a `.claude/` **only when the unit genuinely needs config the root/higher level doesn't already give it** (its own skills/rules/settings) — and when you do, it goes **at the config home, never deeper**. Default to *not* creating one.

**The boundary is the build/ship unit, not ownership.** A config home built by many teams is still one config home. A 20-team app like `apps/mega-app` is **one `.claude/`**; its `features/` are CLAUDE.md + `docs/`, and per-team conventions live in team guardrails at the monorepo root `.claude/rules/teams/<team>/` (path-scoped) — never nested `.claude/`. Ownership is resolved by review-ownership + team guardrails; it's often non-contiguous, which is exactly why it can't be the boundary.

Multiple build targets (`mobile/`, `web/`) share one `.claude/`. Platform variation lives in CLAUDE.md hierarchy + path-scoped rules, not deeper `.claude/` dirs.

**Anti-pattern — nested `.claude/` directories**: A nested `.claude/` is **not** a platform limit — `.claude/skills/` and CLAUDE.md *do* cascade on demand. The one-per-config-home rule is **governance discipline**: multiple `.claude/` below a config home create ungovernable composition (who owns what? which rules are active?), and skills that appear based on which file you touched is nondeterminism an orchestrator can't reason about. One `.claude/` per config home = one governance surface, one predictable config location the orchestrator detects. To scope a skill to part of the tree, use `paths` frontmatter — not a nested directory.

**cwd matters for agents:** Launch Claude Code from the config home to get the right agents (see Agent Discovery above).

### Root-Level Protection

The monorepo root is shared context. Anything placed there loads for every developer in every session. Treat it like a shared API — changes require review and must meet a high bar.

**What lives at root:**
- `CLAUDE.md` — shared conventions (build system, monorepo rules, domain routing table)
- `.claude/agents/` — the **canonical set** (generic, project-agnostic; every config home inherits them) **and** governance agents (e.g., `config-reviewer`, which operate on `.claude/` configurations, not code, and don't count toward the standard set)
- `.claude/skills/` — generic skills that meet both promotion criteria (portable + 3 teams need it)
- `.claude/rules/` — monorepo-wide rules that genuinely apply to all config homes

**Root-level rules MUST have `paths` frontmatter.** A rule without `paths` at root loads unconditionally for every developer — config-home-specific conventions loading into every unrelated developer's context window is pure waste. If a rule can't be scoped to file paths, it belongs in root CLAUDE.md (if truly universal) or in a config home's `.claude/rules/` (if specific to it).

**Enforcement:**
- Require platform-team review on `/CLAUDE.md`, `/.claude/rules/`, and `/.claude/skills/` (via your repo's path-based review-ownership mechanism)
- CI validation: reject rules under `/.claude/rules/` that lack `paths` frontmatter
- Promotion criteria for root: generic procedure that works on any codebase AND three or more teams need it. Both must be true.

**What does NOT belong at root:**
- Team-level agents and same-name overrides of the canonical roles — root `.claude/agents/` holds the canonical set and governance agents only. Team customization goes into rules/skills under `teams/<team>/`, not new agents; a config home's justified override stays in that config home (domain-prefixed).
- Config-home-specific rules (platform conventions, design tokens, feature flag patterns) — exception: team rules/skills/docs for teams spanning multiple config homes go under `teams/<team>/` (see "Team Scoping" below)
- Large data files (token dumps, icon manifests — these blow up context windows)

### Team Scoping — Cross-Project Rules, Skills, and Docs

Teams that own code spanning multiple config homes can't rely on config-home-level facilities — those only load from that config home's `.claude/`. The pattern for these teams:

- **Rules:** root `.claude/rules/teams/<team>/` with `paths` frontmatter covering all directories the team owns. Same root constraints apply (`paths` required, platform-team review).
- **Skills:** root `.claude/skills/teams/<team>/`. Use this only when the team's code spans multiple config homes; a team whose code lives inside one config home should keep its skills in that config home's `.claude/skills/`. Skills that are genuinely cross-cutting (3+ teams use it, generic) still go at root `.claude/skills/` directly, not under `teams/`.
- **Domain docs:** `docs/teams/<team>/` follows the same shape.
- **Agents:** no team-level tier. Root `.claude/agents/` holds the canonical set and governance agents only. Team customization happens through skills + rules that auto-compose around whichever agent runs — not by adding new agents.

### Cross-Dependency References

Dependencies own their docs. Consumers point to them via the routing table in CLAUDE.md.

```
packages/components/docs/creating-a-component.md   ← canonical, owned by the components team
apps/example-app/docs/app-component-patterns.md    ← app-specific usage, references canonical
```

```markdown
## Domain References (in CLAUDE.md)
| Task involves...        | Read first                                       |
|-------------------------|--------------------------------------------------|
| New component (general) | `packages/components/docs/creating-a-component.md` |
| App-specific component  | `apps/example-app/docs/app-component-patterns.md`  |
```

**Three rules**:
1. Whoever owns the API owns the doc. Consumer points, never copies.
2. When the API changes, one doc updates. All consumers benefit.
3. App-specific usage patterns go in a local doc that references the canonical.

### Monorepo Layout

```
repo/
├── CLAUDE.md                          ← shared conventions, domain routing table
├── .claude/
│   ├── agents/                        ← the canonical set (generic) + governance agents
│   │   ├── architect.md
│   │   ├── coder.md                   ← project-agnostic; domain comes from substrate
│   │   ├── test-writer.md
│   │   ├── tester.md
│   │   ├── reviewer.md
│   │   ├── pr-submission.md
│   │   ├── learner.md
│   │   └── config-reviewer.md         ← governance (operates on .claude/, not code)
│   └── skills/                        ← generic skills (security-review, tdd, etc.)
├── packages/components/
│   └── docs/                          ← canonical domain docs, owned by the components team
├── apps/example-app/                  ← config home (launch cwd here); inherits root's agents
│   ├── CLAUDE.md                      ← config-home conventions, routing table
│   ├── docs/                          ← config-home domain docs (tool-agnostic)
│   ├── .claude/
│   │   ├── agents/                    ← NO canonical copies; override only, domain-prefixed
│   │   │   └── product-manager.md     ← a genuinely unique role this config home adds
│   │   ├── skills/                    ← domain skills
│   │   └── rules/                     ← path-scoped instructions
│   ├── mobile/
│   │   └── CLAUDE.md                  ← mobile-specific context (on-demand)
│   └── web/
│       └── CLAUDE.md                  ← web-specific context (on-demand)
└── services/example-service/          ← different config home; also inherits root's agents
    ├── CLAUDE.md
    ├── docs/
    └── .claude/
        └── skills/                    ← no agents/ needed — root's set is enough
```

---

## Portability

All five facilities are declarative (markdown files, JSON config) and portable between local dev and SaaS environments:

```
Local Dev                    SaaS Container
──────────                   ──────────────
CLAUDE.md              ───→  Identical
.claude/rules/*.md     ───→  Identical (path-scoped instructions)
.claude/agents/*.md    ───→  Identical
.claude/skills/*/      ───→  Identical
docs/*.md              ───→  Identical (tool-agnostic domain docs)
.claude/settings.json  ───→  Identical (hooks config)
.mcp.json              ───→  Identical (plugin config)
```

Tool-specific config lives in `.claude/`. Project knowledge lives in `docs/`. Both are checked in, both are portable. Same files, both environments.

---

## Patterns from the Community

These patterns — drawn from open-source agent knowledge frameworks and community practice — informed this architecture:

| Pattern | Applied Here As |
|---------|-----------------|
| **Hierarchical context separation** — separate files by purpose | Four knowledge layers: CLAUDE.md → Agents → Skills → Domain Docs |
| **"Text > Brain"** — if you want to remember it, write it to a file | Three-occurrence rule as the capture discipline |
| **Living documentation** — docs evolve with the project, not written once | Placement test = disciplined evolution path |
| **"Skills are shared. Your setup is yours."** — separate shared from local | `.claude/` is checked in (shared). `settings.local.json` is gitignored (personal) |
| **Composable knowledge** — templates build on each other in reading order | Agent → invokes Skill → reads Domain Doc (layered indirection) |
| **Explicit decision frameworks** — document "when to use what," not just "what exists" | The placement test (seven questions) for knowledge routing |
| **Quality over quantity** — be selective about what to encode | Three-occurrence rule prevents knowledge bloat |

---

## Governance

The architecture itself needs maintenance. Without governance, knowledge drifts — stale docs, orphaned skills, agent definitions that no longer match reality.

**Ownership**: Each config home's `.claude/` is owned by the team that owns it. Root-level `.claude/` and root `CLAUDE.md` are owned by the platform team.

**Review**: Changes to a config home's `.claude/agents/`, `.claude/rules/`, and `docs/` require review from the owning team. Root-level changes require platform-team review — enforced via your repo's path-based review-ownership mechanism (require the platform team as reviewer on `/CLAUDE.md`, `/.claude/agents/`, `/.claude/rules/`, and `/.claude/skills/`).

**Hygiene cadence**: Quarterly review per config home. Check: Are domain docs still accurate? Do routing tables point to files that exist? Are skills still used? Remove what's dead.

**Submitting a KA-related PR**: Before requesting review, see [config-pr-checklist.md](config-pr-checklist.md) — a two-step self-validation (mechanical + judgment) expected before a turnaround review. Applies to PRs that touch CLAUDE.md, `.claude/` configs, or domain docs referenced by the KA.

**Drift detection**: A CI check validates structural conformance — the standard agents exist at root and match template structure, any config-home override is domain-prefixed (not a same-name shadow), routing table entries resolve to real files, `paths` in rules reference existing directories, and root-level rules have `paths` frontmatter (reject unscoped rules at root). Root governance agents are validated separately: must be read-only (no Write/Edit tools), must reference the knowledge architecture, and must be owned by the platform team via review gating.
