# Spec: Include `aidankinzett/claude-git-pr-skill` in the boss-skills marketplace

## Context / Goal

Make the `boss-skills` marketplace **automatically offer** a third-party plugin —
`github-pr-review` from [`aidankinzett/claude-git-pr-skill`](https://github.com/aidankinzett/claude-git-pr-skill) —
the same way [`anthropics/claude-plugins-official`](https://github.com/anthropics/claude-plugins-official/blob/main/.claude-plugin/marketplace.json)
lists external plugins (e.g. its Adobe and Airtable entries).

Today every entry in `.claude-plugin/marketplace.json` is a **local** `./plugins/...` path; none
reference a remote repo. This spec introduces the first **remote reference**.

> **Scope:** this document is a spec. Following it means editing `.claude-plugin/marketplace.json`
> and validating. It does not change behavior on its own.

### Decisions (locked in)

- **Approach:** remote reference via a single `git-subdir` entry (NOT vendoring/copying upstream code).
- **Pinning:** pin `ref: v1.1.1` + `sha: 3660dca…` (reproducible, supply-chain-safe).
- **Category:** `boss-dev`.

### Upstream facts (verified via `gh` on 2025-12-02)

- `aidankinzett/claude-git-pr-skill` is itself a marketplace (`github-pr-skills`, v1.1.1).
- It contains **one** plugin, `github-pr-review`, living in the subdirectory `github-pr-review/`.
- That plugin is **skill-only**: `github-pr-review/skills/github-pr-review/SKILL.md`, and it has
  **no `.claude-plugin/plugin.json`** — the upstream marketplace.json supplies its metadata.
- Latest release: tag `v1.1.1`, commit `3660dca92424b91f1eb716b5815b476c3913450e`.
- License: MIT.

## 1. The marketplace entry to add

Append this object to the `plugins[]` array in `.claude-plugin/marketplace.json` (keep it grouped
with the other `boss-dev` entries):

```json
{
  "name": "github-pr-review",
  "source": {
    "source": "git-subdir",
    "url": "https://github.com/aidankinzett/claude-git-pr-skill.git",
    "path": "github-pr-review",
    "ref": "v1.1.1",
    "sha": "3660dca92424b91f1eb716b5815b476c3913450e"
  },
  "description": "Professional GitHub PR reviews with pending reviews, code suggestions, and a user-approval workflow via the gh CLI.",
  "version": "1.1.1",
  "category": "boss-dev",
  "keywords": ["github", "pr", "review", "code-suggestions", "gh-cli"],
  "author": { "name": "Aidan Kinzett" },
  "homepage": "https://github.com/aidankinzett/claude-git-pr-skill"
}
```

### Why `git-subdir` (and not `{ "repo": "..." }`)

The plugin lives in a **subdirectory** (`github-pr-review/`), not at the repo root. The repo root
is itself a *marketplace*, so a bare `repo`/`url`-only reference would point at the wrong thing.
The `git-subdir` source — `url` + `path` + `ref` + `sha` — is exactly the shape the official
marketplace uses for subdirectory-hosted third-party plugins (Adobe, Airtable, 42Crunch, …).

### Why this passes local validation

`scripts/verify-structure.py` handles object-form sources as follows:

- **Schema (lines ~233–246):** the inner `source` object only `required`s the `source` key and
  permits extra keys, so `url`/`path`/`ref`/`sha` are accepted.
- **Runtime (line ~1154):** any object source containing a `repo` **or** `url` key is recorded as
  `"External source; not validated locally"` and skips filesystem checks.

So the entry validates without any change to the validator.

## 2. Best-practice notes

- **Pin, don't float.** Every external entry in the official marketplace pins a `sha`. Taking an
  upstream update is then a deliberate, reviewable bump of `ref` + `sha` — never a silent change
  at install time.
- **Preserve attribution.** Keep `author.name` (Aidan Kinzett) and `homepage`. Do not relabel
  someone else's plugin as your own.
- **Unique `name`.** `github-pr-review` must not collide with any existing `plugins[]` entry.
- **`version` is display-only here.** It mirrors upstream (`1.1.1`) so `/plugin list` shows a
  sensible number; there is no local manifest to keep it in sync with.

## 3. Validate

```bash
uv run scripts/verify-structure.py      # or: ./scripts/verify-structure.py
```

**Expected result:** the `github-pr-review` entry reports

```
External source; not validated locally
```

That message is **success** — it is `info_only`, not a warning or error. The run should otherwise
pass exactly as before.

## 4. Versioning / parity

- The `version-bump-reviewer` skill enforces `plugin.json.version == marketplace.json[].version`
  for **local** plugins. An external `git-subdir` entry has **no local `plugin.json`**, so that
  parity check **does not apply** — do not expect (or try to satisfy) it for this entry.
- **Optional but recommended:** bump the marketplace `metadata.version`
  (`0.1.0` → `0.2.0`, a minor bump) since adding a plugin to the directory is an additive change.
- Suggested conventional commit:

  ```text
  feat(marketplace): add external github-pr-review plugin (git-subdir, pinned v1.1.1)
  ```

## 5. Verify it installs (end-to-end)

```bash
# From a consumer (or this repo, for local testing):
/plugin marketplace add bossjones/boss-skills      # or: /plugin marketplace add file://$(pwd)
/plugin install github-pr-review
/plugin list                                        # confirm github-pr-review is listed + enabled
```

Then confirm the skill triggers: ask Claude something like *"Review PR #123 and suggest
improvements"* and verify it follows the github-pr-review pending-review / approval workflow.

## 6. Contingency — the one real risk

**Risk:** the upstream `github-pr-review/` subdir has **no `plugin.json`** (only the upstream
marketplace.json declares the plugin). If Claude Code's `git-subdir` resolver requires a manifest
at the plugin root, `/plugin install github-pr-review` (step 5) may fail.

Apply a fallback **only if step 5 fails**:

1. **Marketplace chaining (preferred fallback).** Instead of re-listing the plugin in your
   marketplace, add the upstream repo as a known marketplace and install from it. This is what the
   upstream README recommends for teams. In the consumer's `.claude/settings.json`:

   ```json
   {
     "extraKnownMarketplaces": [
       {
         "name": "github-pr-skills",
         "source": { "source": "github", "repo": "aidankinzett/claude-git-pr-skill" }
       }
     ],
     "plugins": { "github-pr-review": { "enabled": true } }
   }
   ```

2. **Vendor (last resort).** Copy `github-pr-review/skills/github-pr-review/` into a
   boss-skills-owned plugin under `plugins/boss-dev/`, preserving the MIT license and attribution.
   This gives full control and offline use but **loses automatic upstream updates** — you must
   re-sync manually. If vendored, it becomes a normal local plugin and the `version-bump-reviewer`
   parity rules **do** apply.

## 7. Updating the pin (future upstream releases)

To take a newer upstream release:

1. Find the new tag/commit:
   `gh api repos/aidankinzett/claude-git-pr-skill/commits/<tag-or-main> --jq '.sha'`
2. Update `ref` and `sha` in the entry (and `version` to match the new tag).
3. Re-run `uv run scripts/verify-structure.py`.
4. Re-test install per §5.

## Acceptance criteria

- `.claude-plugin/marketplace.json` contains the `git-subdir` entry above (pinned `v1.1.1` /
  `3660dca…`, `category: "boss-dev"`).
- `uv run scripts/verify-structure.py` passes, reporting the entry as an external source.
- `/plugin install github-pr-review` succeeds (or a documented fallback from §6 is in place).
