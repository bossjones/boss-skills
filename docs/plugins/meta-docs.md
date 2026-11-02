# Meta Docs plugin reference

> `meta` · v0.1.0 · [plugin source](../../plugins/meta/meta-docs/)

[Meta Docs](../../plugins/meta/meta-docs/README.md) provides three skills and an autonomous review
subagent for cleaning up AI writing habits, humanizing documentation across 20 languages and 10
purpose modes, and adversarially verifying documentation contracts and plans.

| Component | Kind | Input | Output | Boundary |
|---|---|---|---|---|
| [`unslop`](../../plugins/meta/meta-docs/skills/unslop/SKILL.md) | Skill | Drafted prose, READMEs, PR descriptions, commit bodies, or release notes | Rewritten text or diff with 28 numbered AI writing tells removed | Preserves facts, commands, code blocks, and intended tone; does not invent facts. |
| [`humanize-skills`](../../plugins/meta/meta-docs/skills/humanize-skills/SKILL.md) | Skill | A passage or document plus optional mode/language/tone flags (`--technical`, `--audit`, `--lang=xx`, `--calibrate`) | Severity-grouped audit or rewritten text (or `<name>.humanized.<ext>` for long files) | Enforces a pre-flight 0-100 **no-edit gate** and a strict **fact-lock** intake ledger; never overwrites long files in place. |
| [`interrogate`](../../plugins/meta/meta-docs/skills/interrogate/SKILL.md) | Skill | A documentation page, specification, design plan, or git diff | Restatement of intent, verified findings backed by command output, and dropped-claim counts | Report-only unless asked to fix; drops any finding not proven by an executed command or check. |
| [`docs-anti-slop-reviewer`](../../plugins/meta/meta-docs/agents/docs-anti-slop-reviewer.md) | Subagent | Target documentation files or branch diff | Structured second-pass review report combining `interrogate` contract checks and `unslop` / `humanize-skills` prose proposals | Runs in an isolated context window; model-agnostic; does not mutate files unless explicitly asked. |

## Installation

`meta-docs` ships manifests for Claude Code, GitHub Copilot CLI, and Codex.

```bash
claude plugin marketplace add bossjones/boss-skills    # once
claude plugin install meta-docs@boss-skills

copilot plugin marketplace add bossjones/boss-skills   # once
copilot plugin install meta-docs@boss-skills

codex plugin marketplace add bossjones/boss-skills     # once
codex plugin add meta-docs@boss-skills
```

Claude Code and Copilot CLI read `.claude-plugin/marketplace.json` and the plugin's
`.claude-plugin/plugin.json`, and load the skills plus the subagent. Codex reads
`.agents/plugins/marketplace.json` and `.codex-plugin/plugin.json`, and loads the skills only.

## Separate-pass review contract

Following [Flavio Copes' anti-slop methodology](../../plugins/meta/meta-docs/skills/unslop/references/anti-slop-playbook.md),
drafting and anti-slop editing are kept separate:

1. Complete the draft with all technical facts, commands, and sources first.
2. Run `unslop` (for concise English technical prose) or `humanize-skills` (for long documents,
   multi-language content, domain modes, or voice calibration) as a dedicated review pass.
3. Run `interrogate` (or delegate both steps to `docs-anti-slop-reviewer`) to verify that every
   documented CLI flag, file path, relative link, and workflow step actually works against the
   repository.

## Authoring tutorials with `tutorial-engineer`

Contributors extending `meta-docs` can generate or update task-first tutorials under
[`../tutorials/meta-docs/`](../tutorials/meta-docs/README.md) with the external
`tutorial-engineer` subagents (`documentation-generation:tutorial-engineer` for documentation
workflows or `code-documentation:tutorial-engineer` for code-grounded walkthroughs) with any model.
Installing `meta-docs` alone does not install the external `documentation-generation` /
`code-documentation` plugins.
See [Documenting Usage with `tutorial-engineer`](../../plugins/meta/meta-docs/README.md#documenting-usage-with-tutorial-engineer)
for prerequisites and ready-to-run prompts.

## Learn by task

- [De-slop and humanize documentation](../tutorials/meta-docs/deslop-and-humanize-docs.md)
- [Stress-test docs and plans with `interrogate`](../tutorials/meta-docs/interrogate-docs-and-plans.md)
- [Anti-slop playbook and before/after walkthrough](../../plugins/meta/meta-docs/skills/unslop/references/anti-slop-playbook.md)
- [Implementation blueprint](../../specs/meta-docs.md)
