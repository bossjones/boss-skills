# github-pr-review

> `boss-dev` · v1.1.1 · **external** · MIT · by [Aidan Kinzett](https://github.com/aidankinzett) · [upstream repo](https://github.com/aidankinzett/claude-git-pr-skill)

Professional GitHub PR reviews with pending reviews, code suggestions, and a user-approval
workflow via the `gh` CLI. This is the marketplace's first **external** plugin: it is not vendored
into this repo — `boss-skills` references it remotely and pins it to a specific upstream release.

The skill is **skill-only** (no slash commands or subagents). Claude loads it automatically when you
ask it to review a pull request.

## Installation

The plugin installs like any other entry in the marketplace:

```bash
/plugin marketplace add bossjones/boss-skills   # once
/plugin install github-pr-review@boss-skills
```

### Fallback: marketplace chaining

`github-pr-review` lives in a subdirectory of an upstream repo that is itself a marketplace, and that
subdirectory ships no `plugin.json`. If `/plugin install github-pr-review@boss-skills` ever fails to
resolve, install it directly from the upstream marketplace instead by adding it to
`.claude/settings.json` (this repo ships a working example in
[`.claude/settings.example.json`](../../.claude/settings.example.json)):

```json
{
  "extraKnownMarketplaces": [
    {
      "name": "github-pr-skills",
      "source": { "source": "github", "repo": "aidankinzett/claude-git-pr-skill" }
    }
  ],
  "enabledPlugins": { "github-pr-review@github-pr-skills": true }
}
```

## How it's pinned

The marketplace entry is a `git-subdir` source locked to a specific upstream tag **and** commit:

```json
"source": {
  "source": "git-subdir",
  "url": "https://github.com/aidankinzett/claude-git-pr-skill.git",
  "path": "github-pr-review",
  "ref": "v1.1.1",
  "sha": "3660dca92424b91f1eb716b5815b476c3913450e"
}
```

Pinning both `ref` and `sha` means the plugin never updates silently — taking a newer upstream
release is a deliberate, reviewable bump of those two fields in
[`.claude-plugin/marketplace.json`](../../.claude-plugin/marketplace.json). See the
[spec](../../specs/claude-git-pr-skill.md) for the update procedure.

## Requirements

| Requirement | Why |
|-------------|-----|
| `gh` CLI installed and authenticated | The skill posts reviews via `gh api`; run `gh auth login` first |
| A GitHub repo with an open PR | The target of the review |

## Usage

Trigger the skill with a natural-language request naming the PR:

```text
Review PR #123 and suggest improvements
```

The skill follows a three-phase, approval-gated workflow so nothing is posted to GitHub without your
sign-off:

1. **Draft review** — Claude analyzes the PR and prepares inline comments with `gh`-formatted
   ` ```suggestion ` code blocks.
2. **Show & get approval** — Claude shows you exactly what will be posted: every comment with its
   file and line, the formatted suggestions, the review event type (`APPROVE` /
   `REQUEST_CHANGES` / `COMMENT`), and the overall message. You approve or ask for changes.
3. **Post review** — only after approval, Claude creates a pending review with the batched comments
   and submits the chosen event via `gh api`.

For a step-by-step walkthrough, see the
[github-pr-review tutorial](../tutorials/github-pr-review/README.md).

## See also

- Hands-on tutorial: [`docs/tutorials/github-pr-review/`](../tutorials/github-pr-review/README.md)
- Upstream repo & README: [aidankinzett/claude-git-pr-skill](https://github.com/aidankinzett/claude-git-pr-skill)
- Integration spec: [`specs/claude-git-pr-skill.md`](../../specs/claude-git-pr-skill.md)
- Marketplace entry: [`.claude-plugin/marketplace.json`](../../.claude-plugin/marketplace.json)
