# Code Review Focus: Bug Detection First

## Primary Objective
Focus exclusively on identifying real, actionable bugs. Prioritize in this order:
1. **Logic errors** — incorrect control flow, off-by-one errors, wrong conditions, mishandled edge cases
2. **Security vulnerabilities** — injection risks, unvalidated inputs, auth bypasses, secrets in code, unsafe file/path handling
3. **Data integrity issues** — race conditions, improper null handling, unhandled exceptions, lost writes
4. **Performance regressions** — N+1 queries, unbounded loops, blocking I/O in async paths, accidental O(n²) patterns

## What to SKIP
Do NOT comment on:
- Formatting or whitespace (handled by ruff format)
- Documentation or comment quality
- Variable naming preferences unless they cause ambiguity bugs
- Compiler/linter warnings or deprecations already flagged by CI (ruff, basedpyright, ty)
- Style/convention nits — local linting enforces these

## Comment Style
- Be direct and concise. State the bug, explain why it's a problem, suggest the fix.
- Every comment must include a concrete reproduction scenario or explain the exact failure condition.
- No suggestions that are purely aesthetic.
- If you are not confident a finding is a real bug, do not comment.

## Codebase-Specific Rules

### SKILL.md files (`.claude/skills/**/SKILL.md`, `plugins/**/skills/**/SKILL.md`)
- **GitHub #12781 parser bug**: SKILL.md files MUST NOT contain `!` immediately followed by a backtick pattern inside fenced code blocks — the skill parser executes them. Flag any `!`backtick combinations and recommend `$ command` notation instead.
- **Concrete triggers required**: The `description` field and any "when to use" guidance must contain concrete trigger patterns (specific keywords, file types, user phrases). Flag vague language like "when needed", "as appropriate", or "when relevant" — these produce skills that never auto-trigger.
- **Frontmatter**: Every SKILL.md must have YAML frontmatter with both `name` and `description`. Flag missing fields.

### PEP 723 scripts (any standalone script in `scripts/`, `devtools/`, `.claude/skills/**/scripts/`)
- Scripts intended to be run standalone must have the `#!/usr/bin/env -S uv run` shebang and a `# /// script` inline metadata block declaring `requires-python` and `dependencies`. Flag standalone scripts missing this block — they will fail to run via `uv run`.
