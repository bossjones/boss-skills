# Tutorial 1: Install & enable `boss-experimental`

**Time:** ~3 minutes
**You'll learn:** how to add the `boss-skills` marketplace, install `boss-experimental`, and
confirm its skills and agents are actually loaded.

## What you'll build

Nothing yet — this is the one-time setup every other tutorial in this series depends on.

## Prerequisites

- Claude Code installed and runnable (`claude` on your `PATH`, or the desktop app).
- A terminal, or any Claude Code session where you can type slash commands.

## Step 1: Add the `boss-skills` marketplace

In any Claude Code session, run:

```text
/plugin marketplace add bossjones/boss-skills
```

Expected output: Claude Code fetches `.claude-plugin/marketplace.json` from
`github.com/bossjones/boss-skills` and confirms the marketplace was added. You only need to do
this once per machine.

## Step 2: Install `boss-experimental`

```text
/plugin install boss-experimental@boss-skills
```

The `@boss-skills` suffix disambiguates which marketplace to install from — you'll use this same
`<plugin>@<marketplace>` shape for every plugin in this repo.

> **Info box — interactive alternative.** Typing `/plugin` with no arguments opens Claude Code's
> plugin browser, where you can search for `boss-experimental` and install it from a menu instead
> of typing the command above. Both paths write to the same config.

## Step 3 (alternative): non-interactive install via `settings.json`

If you're bootstrapping a project non-interactively (e.g. from a setup script or a shared repo
config), skip the slash commands and declare the plugin directly in `.claude/settings.json`:

```json
{
  "enabledPlugins": {
    "boss-experimental@boss-skills": true
  }
}
```

Claude Code picks this up on next launch — no `/plugin marketplace add` step needed as long as
`bossjones/boss-skills` is resolvable (it's a public GitHub repo, so no extra
`extraKnownMarketplaces` entry is required, unlike third-party marketplaces).

## Step 4: Confirm the skills appear

Type `/` in a fresh session and look for these three entries (they may show under an
`boss-experimental:` prefix depending on your Claude Code version):

```text
/run-skill-eval
/scaffold-skill-eval
/claude-config-validation
```

If you don't see them, run `/plugin` again and check the plugin's status shows **enabled** — a
plugin can be installed but not enabled.

**Checkpoint:** run the config-validation skill against the plugin's own repo to sanity-check
that skills are wired up (this also previews Tutorial 5):

```text
/claude-config-validation plugins/boss-experimental/boss-experimental/skills/claude-config-validation/eval/test-fixtures/valid-project
```

Expected: a markdown table titled `## Claude Config Validation: ...` with 23 rows, all `PASS`
(this fixture is the plugin's own positive control).

## Step 5: Confirm the agents appear

The eight dev-workflow agents (`architect`, `coder`, `test-writer`, `tester`, `reviewer`,
`pr-submission`, `learner`, `config-reviewer`) are subagents, not slash commands — Claude Code
routes to them automatically based on their `description` frontmatter, or you can invoke them
explicitly by name if your Claude Code version supports `@agent-name` mentions or the `Task` tool.
To confirm they're registered, ask Claude directly:

```text
What subagents do you have access to from the boss-experimental plugin?
```

Expected: a list naming all eight, each with a one-line description matching
`plugins/boss-experimental/boss-experimental/agents/*.md` (e.g. `pr-submission` — "Use when
creating branches, committing changes, pushing, or opening pull requests").

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `/plugin marketplace add` fails to resolve | No network access, or GitHub rate-limited | Retry, or check `gh auth status` if you have `gh` configured |
| Skills don't show under `/` | Plugin installed but not enabled | Run `/plugin`, find `boss-experimental`, toggle it on |
| `/claude-config-validation` runs but says "no Claude Code configuration" | Wrong path — the skill needs a `project_path` that contains a `.claude/` directory | Point it at a project root, not a subdirectory |

## Next steps

Continue to [Tutorial 2: Evaluate an existing skill locally](02-run-skill-eval-locally.md) to run
your first eval with zero setup (no API key, no Docker).
