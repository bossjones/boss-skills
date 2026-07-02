---
paths: plugins/**/SKILL.md, plugins/**/skills/**
---

# Skill Development Standards

## SKILL.md Structure

Every skill requires a `SKILL.md` file with:

1. **Title** - Clear, descriptive name
2. **Description** - What the skill provides
3. **Triggers** - Concrete activation conditions
4. **Instructions** - Step-by-step guidance
5. **References** - Links to supporting files

## Skill Directory Layout

```text
skills/<skill-name>/
├── SKILL.md              # Main skill definition (required)
├── references/           # Reference documentation
├── examples/             # Example code/configs
├── patterns/             # Reusable patterns
├── anti-patterns/        # Common mistakes to avoid
├── tools/                # Helper scripts
└── workflows/            # Multi-step procedures
```

## Workspace Directories

`skill-creator`'s Description Optimization loop (and similar eval tooling) generates scratch
output in a sibling `<skill-name>-workspace/` directory (eval fixtures, `trigger-eval.json`,
benchmark results — see `docs/evals/README.md` for the parallel convention for eval *reports*).
`scripts/verify-structure.py`'s skills-directory check recognizes any directory whose name ends
in `-workspace` (like the existing `logs` exclusion for gitignored hook output) as a non-skill
directory, so it's fine to place it either alongside the skill under `skills/` or at the plugin
root — both pass `make verify-structure`.

## Trigger Patterns

Triggers should be **concrete and actionable**, not vague:

**Good triggers:**
- "When creating a new Ansible role"
- "When configuring Proxmox cloud-init templates"
- "When writing PEP 723 inline script metadata"

**Bad triggers:**
- "When working with infrastructure"
- "When needed"
- "For Python tasks"

## Reference Organization

- Keep references focused and specific
- Use markdown files for documentation
- Include working code examples
- Document anti-patterns explicitly

## CRITICAL: Dynamic Bash Pattern Bug (GitHub #12781)

The skill parser executes `!` backtick patterns **even inside fenced code blocks**.

**NEVER use these patterns in SKILL.md code examples:**

```text
# BAD - Will execute during skill load:
!`git status`
!`bash ${CLAUDE_PLUGIN_ROOT}/scripts/script.sh`

# The \! escape does NOT work
\!`command`  # Still executes!
```

**Use `$` shell notation instead:**

```text
# GOOD - Safe in code blocks:
$ git status
$ bash ${CLAUDE_PLUGIN_ROOT}/scripts/script.sh
```

**Workarounds:**

1. Use `$ command` notation in examples
2. Describe syntax in prose: "Use exclamation mark prefix with backticks"
3. Move examples to reference files (not parsed as skill content)

This also applies to `@` file reference patterns in code blocks.
