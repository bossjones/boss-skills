# How skills work (reference)

Canonical doc: <https://github.com/wshobson/agents/blob/main/docs/agent-skills.md#how-skills-work>

Skills are modular packages that extend Claude with specialized knowledge, following
Anthropic's [Agent Skills Specification](https://github.com/anthropics/skills/blob/main/spec/agent-skills-spec.md).
Use this when deciding *how* to improve a skill (the `--fix` path), so changes reflect what
genuinely makes a skill better rather than just nudging a metric.

## Activation

Skills are consulted when Claude detects matching patterns in the request via the skill's
`name` + `description`. Claude only reaches for a skill on tasks it can't trivially handle
itself, so descriptions must clearly signal the multi-step or specialized contexts where
the skill earns its keep. Claude tends to **under-trigger**, so descriptions should be
explicit and slightly "pushy" about when to use the skill.

## Progressive disclosure (three tiers)

1. **Metadata** (frontmatter `name` + `description`) — always loaded (~100 words). The
   primary triggering mechanism.
2. **Instructions** (SKILL.md body) — loaded when the skill activates. Keep under ~500
   lines; if longer, add hierarchy and point into `references/`.
3. **Resources** (`references/`, `scripts/`, `assets/`) — loaded on demand. Scripts can
   execute without being read into context.

This is exactly the lever for a low `progressive_disclosure` score: move detail out of the
body into focused `references/` files and link to them.

## Spec compliance checklist

- `name` is required and hyphen-case.
- `description` is required, includes a "Use when …" clause, and stays under 1024 characters.
- Descriptions are complete (not truncated) and the YAML frontmatter is valid.

## Writing guidance for `--fix`

- Prefer imperative instructions and explain the *why* — modern models follow reasoned
  guidance better than rigid `ALWAYS`/`NEVER` walls.
- Generalize from the eval feedback; don't overfit edits to a single score.
- Bundle repeated logic into `scripts/` and define output formats explicitly when relevant.
