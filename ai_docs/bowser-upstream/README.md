# bowser — upstream snapshot

Unmodified snapshot of IndyDevDan's **bowser** repo, staged here as the implementation source for
[specs/bowser.md](../../specs/bowser.md) (vendoring bowser's 4-layer browser-automation stack into
the `agent-harness` plugin, with the `claude --chrome` layer ported to cmux).

## Provenance

- **Repository:** https://github.com/disler/bowser
- **Pinned commit:** `26541acddc0626e97e8f4398e47b288e97f97ebd` (2026-02-22)
- **Author:** IndyDevDan (disler)
- **Video:** https://www.youtube.com/watch?v=efctPj6bjCY — "My 4-Layer Claude Code Playwright CLI Skill (Agentic Browser Automation)" (transcript + summary live one directory up in `ai_docs/`)

Two local renames, no content changes (every file is byte-identical to the pinned commit):

1. Upstream's `README.md` → `UPSTREAM-README.md`, so this provenance file could take the `README.md` slot.
2. Upstream's `.claude/` → `dot-claude/`, so Claude Code does not auto-discover the snapshot's stale skills (the upstream `claude-bowser` skill would otherwise register and could mis-trigger in this repo).

## Contents

- `dot-claude/skills/` — `playwright-bowser/` (Playwright CLI wrapper skill + `docs/playwright-cli.md` reference), `claude-bowser/` (the `claude --chrome` skill being replaced by the cmux port), `just/` (generic just skill + 5 example templates)
- `dot-claude/agents/` — `bowser-qa-agent.md`, `playwright-bowser-agent.md`, `claude-bowser-agent.md`
- `dot-claude/commands/` — `ui-review.md`, `build.md`, `prime.md`, `list-tools.md`, and `bowser/{hop-automate,amazon-add-to-cart,blog-summarizer}.md`
- `ai_review/user_stories/` — sample QA user stories (`hackernews.yaml`, `example-app.yaml`)
- `justfile` — layer-4 recipes
- `UPSTREAM-README.md` — the 4-layer architecture doc; `TOOLS.md` — Claude Code tool dump (documents the `mcp__claude_in_chrome__*` surface); `specs/init-automation.md` — upstream spec for the hop-automate layer
