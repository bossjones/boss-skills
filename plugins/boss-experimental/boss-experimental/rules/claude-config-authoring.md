---
paths:
  - ".claude/**/*.md"
  - "**/CLAUDE.md"
  - "**/.claude/**/*.md"
---

# Claude Config Authoring Guidelines

When editing Claude Code configuration files, follow these rules.

## Placement Test

See the [Placement Test](../references/knowledge-architecture.md#placement-test) — use the "first yes wins" approach to determine which facility owns a piece of knowledge.

## Anti-Patterns to Avoid

- **Conventions in agent prompts**: File-type-scoped conventions (copyright headers, import style, naming) belong in `.claude/rules/` with `paths` frontmatter, not in agent definitions. Rules compose with all agents automatically.
- **Duplicating CLAUDE.md content in agents**: Agents already read CLAUDE.md. Don't copy project knowledge into agent prompts.
- **CLAUDE.md over 200 lines**: Extract to rules, docs, or skills. Leave one-line pointers.
- **Padding the always-loaded CLAUDE.md**: every line is a context tax paid by every session. Routing rows point to one entry doc per task. A doc tied to a narrow file pattern belongs in a path-scoped rule (loads on demand), not the routing table — and don't list a doc in both, that's redundant cost with no added discovery.
- **Non-writing agents with write permissions**: tester, reviewer, pr-submission should not have `Write`/`Edit` tools or `acceptEdits` permission. Architect gets `Write` for design docs only.
- **Referenced skills that don't exist**: If an agent says "use the X skill," that skill must exist.
- **Code blocks in skills**: Skills must be declarative (describe *what*, not *how*). Executable logic belongs in `bin/` or `scripts/`, not as fenced code blocks in SKILL.md. Output format templates are the only exception.
- **External dependencies in skills**: Skills must not require installing tools beyond the standard agent toolset. No `curl` to external APIs, no `npm install`, no `docker run`.
- **Platform-variant agents** (`coder-mobile`, `coder-web`): One agent per role. Variation via CLAUDE.md hierarchy + rules.
- **Flat skill files**: Skills must follow the `{skill-name}/SKILL.md` directory convention, not be flat files in a grouping directory (e.g., `.claude/skills/design/my-skill.md`). The subdirectory allows supporting files.
- **Missing skill frontmatter**: Skills should have YAML frontmatter with at least `description`. If the skill uses `Agent` or `Bash` tools, declare them in `allowed-tools`.
- **Cross-file duplication**: If the same procedure (e.g., token resolution steps, build commands) appears in multiple skills, extract it to a domain doc in `docs/` and have each skill reference it. Consumer points, never copies.
- **Oversized skills**: Skills over 150 lines likely mix procedure with domain knowledge. Extract checklists, templates, and API docs to `docs/`. Apply the location test: "If useful to someone who's never heard of Claude Code, it doesn't belong in `.claude/`."
- **Unreferenced skills**: Skills that need agent discovery should appear in the project's CLAUDE.md routing table. Skills not in the routing table rely solely on description frontmatter for agent discovery.
- **Using commands instead of skills**: Commands (`.claude/commands/`) are deprecated. Migrate existing commands to skills (`.claude/skills/{name}/SKILL.md`).
- **Skills without evals (when opted in)**: Eval coverage is opt-in, not universal. When your repo has opted into eval coverage, root-level skills and skills that reference external docs should have an `eval/` directory — silent regressions are the risk. Integration wrappers (ticket-tracker, chat) that delegate to MCP servers typically don't need evals. Run evals with `/run-skill-eval <skill-path>`.

## Standard Agent Set

See the [Standard Agent Set](../references/knowledge-architecture.md#standard-agent-set) for the recommended (config-driven) project roles and their tool permissions.

## Full Reference

See [knowledge-architecture.md](../references/knowledge-architecture.md) for the complete architecture.
