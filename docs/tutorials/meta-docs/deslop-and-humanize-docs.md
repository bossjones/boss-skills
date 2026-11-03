# Tutorial: De-slop and humanize documentation with `meta-docs`

Use `unslop`, `humanize-skills`, and the `docs-anti-slop-reviewer` subagent when you have finished
drafting a README, tutorial, specification, or pull request description and want to remove AI
writing tells in a dedicated second pass while keeping every command, file path, and fact intact.

## Prerequisites

- Claude Code, GitHub Copilot CLI, or Codex with the `meta-docs` plugin installed from `boss-skills` (see the
  [Meta Docs plugin README](../../../plugins/meta/meta-docs/README.md#install-the-plugin)).
- A drafted markdown document, pull request description, or passage to review.
- *(Optional, for Step 5 only)*: The external `documentation-generation` or `code-documentation`
  plugins from [`wshobson/agents`](https://github.com/wshobson/agents) (for the `tutorial-engineer`
  subagents).

## Step 1: Finish the draft first

Slash examples use the plugin namespace that Claude Code and Copilot CLI apply to installed
plugin skills (`/meta-docs:<skill>`). In Codex, name the skill in your prompt instead, for example
`Use the unslop skill on README.md`.

Do not mix "don't sound like AI" instructions into your initial drafting prompt. Let the agent focus
on gathering accurate commands, paths, and architecture details first.

## Step 2: Run `unslop` on short technical docs or PR descriptions

For READMEs, release notes, and pull request bodies, invoke `unslop` to scan against its 28 numbered
rules (such as removing "serves as", "Not just X, but Y", em dashes, inline-header bold lists, and
sentences that could appear unchanged in any other project's docs):

```text
/meta-docs:unslop Review README.md. Keep all commands, flags, and file paths unchanged, fix only the patterns
covered by the skill, and show the diff.
```

## Step 3: Run `humanize-skills` for mode-aware or long-document passes

When reviewing a longer document (`1,500+` words), non-English documentation, or text that requires
domain-specific preservation rules (`--technical`, `--academic`, `--legal`, `--business`, `--ux`),
start with an audit pass:

```text
Use humanize-skills on docs/plugins/meta-docs.md with --technical --audit
```

`humanize-skills` runs a 0-100 pre-flight score first:

- If the text scores `0-20` with no formulaic opener/closer and fewer than 5 banned words, the
  **no-edit gate** stops the pass so clean human writing is not tampered with.
- On long files, when you ask to apply fixes, `humanize-skills` freezes structure (headings, code
  blocks, tables, citations) and writes the result to `<name>.humanized.<ext>` beside the original.

## Step 4: Delegate to the `docs-anti-slop-reviewer` subagent

To keep anti-slop rule tables and review diffs out of your main coding context window, delegate the
entire second pass to the `docs-anti-slop-reviewer` subagent (Claude Code and Copilot CLI; Codex
loads the plugin's skills but not its subagent):

```text
Use the docs-anti-slop-reviewer agent to review docs/tutorials/meta-docs/deslop-and-humanize-docs.md
and report any AI prose tells or broken documentation links.
```

## Step 5: Generate or refresh tutorials with `tutorial-engineer`

If you also have the external `documentation-generation` or `code-documentation` plugin installed,
you can generate new tutorials or refresh existing ones by delegating to either fully-qualified
`tutorial-engineer` subagent with any model:

```text
Use the documentation-generation:tutorial-engineer subagent to expand
docs/tutorials/meta-docs/deslop-and-humanize-docs.md with a voice-calibration (--calibrate)
walkthrough based on plugins/meta/meta-docs/skills/humanize-skills/references/voice-calibration.md.
```

## Review the outcome

Inspect the proposed diff to ensure intentional phrasing and all technical commands survived, then
continue with [Stress-test docs and plans with `interrogate`](interrogate-docs-and-plans.md) to
verify every command and path against the repository.

See the [Meta Docs plugin reference](../../plugins/meta-docs.md) for the full component contract.
