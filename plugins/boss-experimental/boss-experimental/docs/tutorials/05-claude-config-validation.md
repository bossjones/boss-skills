# Tutorial 5 — Validate a project's Claude config

`/claude-config-validation` is a **read-only** skill (`allowed-tools: Read, Glob, Grep`). It
runs a catalog of checks over a project's `.claude/` configuration and reports each as
**PASS / WARN / FAIL**. Use it before merging Claude-config changes, or to audit an unfamiliar
project's setup.

No API key, no Docker, no network — it just reads files.

## 1. Point it at a project

Invoke the skill with a project path:

```text
/claude-config-validation apps/example-app
```

If you run it with **no argument from a monorepo root**, the skill deliberately does *not*
auto-validate the root. It detects the root using a configurable marker set (default: `.git`,
`pnpm-workspace.yaml`, a `package.json` with a `workspaces` field, `lerna.json`, `nx.json`),
lists the projects that have a `.claude/` directory, and asks which one to validate. Pass the
path explicitly to skip that prompt.

## 2. A sample project to validate

Create the small project the tutorials share (or point the skill at one of your own):

```text
apps/example-app/
├── CLAUDE.md
└── .claude/
    ├── agents/
    │   └── coder.md
    └── skills/
        └── my-skill/
            └── SKILL.md
```

A minimal `apps/example-app/.claude/skills/my-skill/SKILL.md`:

```markdown
---
name: my-skill
description: Formats changelog entries. Use when asked to "format a changelog" or "tidy CHANGELOG.md".
allowed-tools:
  - Read
  - Edit
---

# My Skill

1. Read CHANGELOG.md.
2. Normalize each entry to `- <type>: <subject>`.
3. Write the result back.
```

## 3. Read the results table

The skill prints one row per check across six categories (Project Structure, Knowledge
Placement, Skill Quality, Discoverability & References, Compliance Placement, Loading &
Registration):

```text
## Claude Config Validation: apps/example-app

| # | Check | Status | Details |
|---|-------|--------|---------|
| 1 | Config exists | PASS | |
| 2 | Canonical agents | PASS | |
| 3 | Agent frontmatter | PASS | |
| 6 | CLAUDE.md size | PASS | 84 lines |
| 10 | Skill content quality | FAIL | my-skill/SKILL.md:7 fenced code block has a language id |
| 11 | Skill frontmatter | PASS | |
| 14 | Skill size & separation | PASS | 12 lines |
| 22 | Skill eval present | N/A | repo has not opted into eval coverage |
| ... | ... | ... | ... |

## Issues

### FAIL
- apps/example-app/.claude/skills/my-skill/SKILL.md: Check 10 — language-tagged fenced code block (parser bug #12781)

### WARN
- (none)

## Recommendations
- Replace the ```markdown fence in my-skill/SKILL.md with a bare fence or `$ command` notation.
```

**How to read it:**

- **PASS** — the check is satisfied.
- **WARN** — worth a look but not blocking (e.g. CLAUDE.md between 200–300 lines, a
  project-prefixed custom agent with no pipeline declaration).
- **FAIL** — a real problem (e.g. a canonical agent shadowed in a project, a broken routing
  reference, a language-tagged code block in a SKILL.md).
- **N/A** — the check doesn't apply here. Check 22 (every skill has an `eval/`) is **opt-in**;
  it reports N/A unless the repo has opted into eval coverage.

## 4. Two knobs you can tune per repo

The skill is deliberately **not** hardcoded to one project's conventions:

- **Canonical agent roles (Check 2).** The default root-owned set is `architect`, `coder`,
  `test-writer`, `tester`, `reviewer`, `pr-submission`, `learner` — but this is a *recommended*
  default, not a mandate. If your repo declares its own role set, the check validates against
  that instead. A project that redefines a canonical role (same name) FAILs, because a
  same-named project agent is shadowed by the root one and never runs.
- **Monorepo-root markers (Step 0).** The default detection set is listed in step 1 above;
  adjust it to match your tooling (e.g. a Cargo workspace, a Go module root).

Both are documented in the skill's **Configuration** section and in
[`references/config-validation-checks.md`](../../references/config-validation-checks.md).

## 5. Fix, re-run, repeat

Fix the reported FAILs (here: remove the language-tagged fence), then re-run:

```text
/claude-config-validation apps/example-app
```

Iterate until FAILs are gone and WARNs are either fixed or consciously accepted. For the full
definition of every check and its PASS/WARN/FAIL criteria, see
[`references/config-validation-checks.md`](../../references/config-validation-checks.md); for the
doctrine behind the checks, see
[`references/knowledge-architecture.md`](../../references/knowledge-architecture.md).

## Next steps

Config validation pairs naturally with the read-only `config-reviewer` agent, which runs this
skill as its "mechanical floor" and then layers architectural judgment on top. Meet it and the
rest of the set in [Tutorial 6](06-dev-workflow-agents.md).
