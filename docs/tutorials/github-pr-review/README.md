# Tutorial: Review your first PR with github-pr-review

This walkthrough takes you from a fresh install to posting a complete, approval-gated GitHub pull
request review — with inline code suggestions — using the
[`github-pr-review`](../../plugins/github-pr-review.md) plugin.

The plugin never posts anything to GitHub without showing you exactly what it will say and waiting
for your approval, so it's safe to follow along on a real PR.

**Time:** ~5 minutes · **Level:** beginner

## Prerequisites

| You need | Check it |
|----------|----------|
| Claude Code with the `boss-skills` marketplace added | `/plugin marketplace add bossjones/boss-skills` |
| The `gh` CLI installed and authenticated | `gh auth status` (run `gh auth login` if needed) |
| A GitHub repository with an open pull request | e.g. PR #123 in a repo you can review |

## Step 1 — Install the plugin

```bash
/plugin install github-pr-review@boss-skills
/plugin list                      # confirm github-pr-review is listed + enabled
```

> **If the install fails to resolve**, the plugin is external and its upstream subdirectory ships no
> manifest. Fall back to installing it straight from the upstream marketplace — see
> [marketplace chaining](../../plugins/github-pr-review.md#fallback-marketplace-chaining) in the
> reference page (a ready-to-copy block lives in
> [`.claude/settings.example.json`](../../../.claude/settings.example.json)).

## Step 2 — Ask Claude to review a PR

In the repo you want to review, just describe the task in natural language. The skill activates
automatically — there's no slash command to remember:

```text
Review PR #123 and suggest improvements
```

Claude reads the PR diff and **drafts** a review locally. Nothing is posted yet.

## Step 3 — Review what will be posted

Before touching GitHub, the skill shows you exactly what it intends to submit:

- each comment with its **file and line number**,
- the **code suggestions**, formatted as GitHub ` ```suggestion ` blocks,
- the **review event type** — `APPROVE`, `REQUEST_CHANGES`, or `COMMENT`,
- the **overall review message**.

Read it over. This is your approval gate.

## Step 4 — Approve (or ask for changes)

Tell Claude to go ahead, or refine first:

```text
Looks good — post it.
```

or

```text
Drop the comment on line 42 and change the event to REQUEST_CHANGES, then post.
```

Claude only posts after you approve. Under the hood it creates a **pending review** with all the
batched comments and then submits the event, using `gh api`:

```bash
# 1. Create a pending review with batched inline comments + suggestions.
#    Each comment body can embed a GitHub ```suggestion ... ``` block.
gh api repos/:owner/:repo/pulls/123/reviews -X POST \
  -f commit_id="<SHA>" \
  -f 'comments[][path]=src/file.ts' \
  -F 'comments[][line]=42' \
  -f 'comments[][body]=Consider extracting this into a helper.'

# 2. Submit the review with the chosen event
gh api repos/:owner/:repo/pulls/123/reviews/<REVIEW_ID>/events -X POST \
  -f event="APPROVE" \
  -f body="Overall review message"
```

You don't type these yourself — the skill builds and runs them for you (including the
` ```suggestion ` blocks inside each comment body). They're shown here so you know exactly what's
happening on your behalf.

## What you get

A single, coherent GitHub review on the PR: inline comments anchored to the right lines, one-click
applicable code suggestions, and the review state (approved / changes requested / commented) you
chose — all batched into one submission rather than a scatter of individual comments.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Skill doesn't activate | Name the PR explicitly ("review PR #123"); confirm it's enabled in `/plugin list` |
| `gh: not authenticated` | Run `gh auth login` and re-try `gh auth status` |
| `/plugin install` can't resolve the plugin | Use [marketplace chaining](../../plugins/github-pr-review.md#fallback-marketplace-chaining) |
| Comments land on the wrong lines | Make sure the PR is up to date; the skill anchors to the head commit SHA |

## Next steps

- Reference: [`docs/plugins/github-pr-review.md`](../../plugins/github-pr-review.md)
- Upstream source: [aidankinzett/claude-git-pr-skill](https://github.com/aidankinzett/claude-git-pr-skill)
- Back to all [tutorials](../README.md)
