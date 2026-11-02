# Meta Docs

`meta-docs` packages three documentation skills and an autonomous review subagent for the
`boss-skills` marketplace. It ships manifests for Claude Code, GitHub Copilot CLI, and Codex. Use it to run a separate anti-slop review pass on drafted prose, humanize
documents across 20 languages and 10 purpose modes without losing technical facts, and stress-test
documentation contracts and plans with execution-backed adversarial verification.

Read the [Meta Docs plugin reference](../../../docs/plugins/meta-docs.md) for the contract summary and
the [Meta Docs tutorials](../../../docs/tutorials/meta-docs/README.md) for step-by-step walkthroughs.

## Included Components

| Component | Type | What it does | When to use it |
|---|---|---|---|
| [`unslop`](skills/unslop/SKILL.md) | Skill | Cuts 28 numbered AI writing tells (vocabulary, em dashes, "Not just X, but Y", inline-header lists, abstract metaphor nouns) while keeping commands and facts intact. | Fast second-pass cleanup on READMEs, PR descriptions, commit bodies, and short technical docs. |
| [`humanize-skills`](skills/humanize-skills/SKILL.md) | Skill | Runs a pre-flight no-edit gate, a strict fact-lock intake ledger, and surface + structural passes across 20 languages, 10 modes (`--technical`, `--academic`, `--legal`, etc.), and 7 tones. | Long documents (`1,500+` words), non-English docs, voice calibration (`--calibrate`), or severity-grouped audits (`--audit`). |
| [`interrogate`](skills/interrogate/SKILL.md) | Skill | Restates intent, fans out parallel adversary subagents to break a document, specification, or code diff, and retains only findings proven by an executable command. | Verifying that documented CLI flags, paths, links, schemas, and architectural plans hold up against the real repository. |
| [`docs-anti-slop-reviewer`](agents/docs-anti-slop-reviewer.md) | Subagent | Runs in an isolated context window with `unslop`, `humanize-skills`, and `interrogate` preloaded to perform a combined prose + contract review pass. | Delegating a separate review pass after drafting a README, tutorial, spec, or pull request so review logs stay out of your main session. |

## Install the Plugin

The `meta-docs` plugin is available from the `boss-skills` marketplace
(`bossjones/boss-skills`). Marketplace registration is a one-time step; skip the
marketplace-add command if `boss-skills` is already registered.

| Runtime | Manifest read | Marketplace read | Components loaded |
|---|---|---|---|
| Claude Code | `.claude-plugin/plugin.json` | `.claude-plugin/marketplace.json` | Skills and the subagent |
| GitHub Copilot CLI | `.claude-plugin/plugin.json` | `.claude-plugin/marketplace.json` | Skills and the subagent |
| Codex | `.codex-plugin/plugin.json` | `.agents/plugins/marketplace.json` | Skills |

Keep the `version` field in both plugin manifests and the Claude marketplace entry in lockstep.

### Claude Code interactive

Launch Claude Code, then enter:

```text
/plugin marketplace add bossjones/boss-skills
/plugin install meta-docs@boss-skills
```

### Claude Code shell

Run these commands from your shell:

```shell
claude plugin marketplace add bossjones/boss-skills
claude plugin install meta-docs@boss-skills
```

### GitHub Copilot CLI interactive

Start Copilot CLI with `copilot`, then enter:

```text
/plugin marketplace add bossjones/boss-skills
/plugin install meta-docs@boss-skills
```

### GitHub Copilot CLI shell

Run these commands from your shell:

```shell
copilot plugin marketplace add bossjones/boss-skills
copilot plugin install meta-docs@boss-skills
```

### Codex shell

Run these commands from your shell:

```shell
codex plugin marketplace add bossjones/boss-skills
codex plugin add meta-docs@boss-skills
```

Codex plugins load skills only. Ask Codex to use `unslop`, `humanize-skills`, or `interrogate`
directly instead of the `docs-anti-slop-reviewer` subagent.

## Relationship to `stop-slop`

The `agent-harness` plugin's `stop-slop` skill is a lightweight prose cleanup for drafting. Use
`meta-docs` when you need numbered rule coverage (`unslop`), non-English or long-document
humanization (`humanize-skills`), execution-backed verification (`interrogate`), or an isolated
review subagent.

## Best Practice: Run Anti-Slop as a Separate Pass

Following [Flavio Copes' anti-slop workflow](skills/unslop/references/anti-slop-playbook.md), finish
your first draft with all facts, sources, and commands before running an anti-slop pass:

1. **Draft the content first** so the agent focuses on accuracy and completeness.
2. **Run a dedicated review pass** with `unslop`, `humanize-skills`, or the
   `docs-anti-slop-reviewer` subagent:

   ```text
   Review README.md using the unslop skill.
   Keep all commands, flags, file paths, and intended structure.
   Fix only the patterns covered by the skill and show the resulting diff.
   ```

3. **Verify contracts with `interrogate`**: An anti-slop pass removes repetitive writing habits, but
   it cannot verify whether a command works. Run `interrogate` to prove every documented command and
   path against the codebase:

   ```text
   Use the interrogate skill on docs/plugins/meta-docs.md to verify every link, path, and command.
   ```

## Quick Usage Examples

### 1. Fast README or PR cleanup (`unslop`)

```text
/unslop Tighten the introduction of README.md and keep every command block unchanged.
```

### 2. Technical audit or rewrite with no-edit gate (`humanize-skills`)

```text
Humanize docs/architecture.md with --technical --audit
```

To apply changes to a long file without overwriting the original, `humanize-skills` writes beside
the source file (for example, `docs/architecture.humanized.md`) while freezing headings, code
blocks, tables, and citations.

### 3. Execution-backed adversarial check (`interrogate`)

```text
/interrogate Challenge specs/meta-docs.md and prove any broken paths or missing validation steps.
```

### 4. Isolated second-pass subagent (`docs-anti-slop-reviewer`)

```text
Use the docs-anti-slop-reviewer agent to audit plugins/meta/meta-docs/README.md for AI prose tells and
broken documentation contracts.
```

## Documenting Usage with `tutorial-engineer`

When adding new skills to `meta-docs` or updating its workflows, generate or refresh task-first
tutorials under [`docs/tutorials/meta-docs/`](../../../docs/tutorials/meta-docs/README.md) by
delegating to a `tutorial-engineer` subagent. These workflows are model-agnostic and work with
whatever model your session or `/subagents` configuration selects.

> **Additional prerequisites for tutorial generation**: These optional authoring workflows require
> the external `documentation-generation` or `code-documentation` plugins from
> [`wshobson/agents`](https://github.com/wshobson/agents), which provide the `tutorial-engineer`
> subagents. Installing `meta-docs` alone does not bundle those tutorial generators.

### Option A: Direct delegation (`documentation-generation:tutorial-engineer`)

```text
Use the documentation-generation:tutorial-engineer subagent to write a
progressive tutorial at docs/tutorials/meta-docs/interrogate-docs-and-plans.md from
plugins/meta/meta-docs/skills/interrogate/SKILL.md and
plugins/meta/meta-docs/agents/docs-anti-slop-reviewer.md. Show how to stress-test a specification
and verify every documented CLI command before implementation.
```

### Option B: Direct delegation (`code-documentation:tutorial-engineer`)

```text
Use the code-documentation:tutorial-engineer subagent to document a pull-request
review example in docs/tutorials/meta-docs/deslop-and-humanize-docs.md showing how
docs-anti-slop-reviewer cleans up PR descriptions and docstrings while preserving runtime behavior.
```

After generating or updating a tutorial, run `docs-anti-slop-reviewer` as a final separate pass on
the tutorial itself, followed by `make markdown-lint` and `make link-check`.

## License

See [LICENSE.md](LICENSE.md) for MIT and CC BY 4.0 attribution details.
