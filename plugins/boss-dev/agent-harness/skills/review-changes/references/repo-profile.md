# Repo profile — rule discovery and the optional per-repo escape hatch

`review-changes` ships with no assumptions about any particular repo's layout, language, or
conventions. It learns them two ways: by generic **discovery** (always runs, works everywhere),
and by an optional **profile file** the target repo can author to sharpen that discovery with
knowledge no generic scan can infer. Neither is required for the skill to produce a useful
review; both make it sharper the more a repo invests in them.

## Discovery — what runs with zero configuration

At Step 2, read whatever exists at the merge-base SHA:

- **Root rule files** — `CLAUDE.md`, `AGENTS.md`, `AGENT.md`, `CONTRIBUTING.md`,
  `.github/copilot-instructions.md`. Different agent harnesses converge on slightly different
  filenames for the same idea; read all that exist rather than assuming one.
- **Rule directories** — `.cursor/rules/`, `.claude/rules/` (`git ls-tree` the directory so
  nothing is missed).
- **Nested conventions** — for each top-level directory the diff touches, also check that
  directory's own `CLAUDE.md`, `AGENTS.md`, or `README.md`. Conventions frequently live next to
  the content they govern rather than only at the repo root.
- **Declared entrypoints** — `pyproject.toml` `[project.scripts]`, `package.json`
  `bin`/`scripts`, `Cargo.toml` `[[bin]]`, `Makefile`/`justfile` targets. This is what the
  `code` lens and challenge criterion 7 (`fp_not_actionable`) check a suggested command against.
- **Already-enforced tooling** — `.pre-commit-config.yaml`, `lefthook.yml`,
  `.github/workflows/*` (or the repo's CI config), and language-specific tool config
  (`eslint.config.*`, `.rubocop.yml`, `rustfmt.toml`, `.editorconfig`, a markdown-lint config).
  This is what quality gate 8 and challenge criterion 15 (`fp_tool_enforced`) resolve against.

**Dedupe symlinked rule files by blob id.** Some repos symlink one rule file to another (a
common pattern: an `AGENT.md` symlink pointing at `CLAUDE.md`). Compare
`git rev-parse "$BASE_SHA:<fileA>"` against `git rev-parse "$BASE_SHA:<fileB>"` — matching blob
ids mean one file, read once. Two files with *different* blob ids that restate the same
conventions and now disagree is a real `consistency` finding, not noise to filter.

Rule precedence: **the repo's own discovered rules override everything and must be cited by
path; industry standards only where the repo is silent; the reviewing model's own judgement is
lowest.**

## The profile file — `.claude/review-changes.md`

An optional file the target repo can author, read at the base SHA
(`git show "$BASE_SHA:.claude/review-changes.md"`). Every section is optional; a repo can supply
one, several, or none. Its absence is not an error — the review is simply quieter, which is the
correct default when nothing is known about the repo's conventions. **State in the report
whether a profile was found.**

| Section | Purpose | Consumed by |
|---|---|---|
| `## Skip paths` | Additional glob patterns to exclude, beyond the generic binary/generated/vendored classification | Step 1 scoping |
| `## Rule files` | Extra rule paths to load at the base SHA that discovery would not find on its own | Step 2 |
| `## Already enforced` | Tools or CI gates whose findings are explicitly out of scope, beyond what quality gate 8 detects automatically | `quality-gates.md` gate 8, `challenge-criteria.md` criterion 15 |
| `## Issue tracker` | The key pattern (e.g. a regex like `PROJ-\d+`) and a read-only lookup command or MCP tool name | `claims` lens, `challenge-criteria.md` criterion 13 |
| `## Index files` | Which index, nav, or README a new file under a given path must appear in | `cross-refs` lens |
| `## Claim conventions` | A repo's own source/confidence tagging contract, if it has one (what the tags mean, where the legend lives) | `claims` lens |
| `## Downstream renders` | Published copies (a wiki page, a generated site, an exported doc) that go stale when the canonical file changes | `cross-refs` lens |
| `## Repo traps` | Free-form notes on repo-specific footguns — appended verbatim to every lens's brief | every lens |

### Worked example

```markdown
# review-changes profile

## Skip paths
- fixtures/**
- *.snap

## Already enforced
- eslint (`.eslintrc.json`) covers unused imports and prefer-const — do not re-flag.
- CI's `typecheck` job is the source of truth for TypeScript errors.

## Issue tracker
- Pattern: `PROJ-\d+`
- Lookup: `jira issue view <key> --output json` (read-only; never write)

## Index files
- New files under `docs/guides/**` must appear in `docs/guides/README.md`.

## Claim conventions
- Claims tagged `[verified]` / `[assumed]` / `[todo]` in prose; legend at the top of each doc.

## Downstream renders
- `docs/**` is mirrored to the public docs site on merge to `main`; a substantive edit with no
  note that the site will regenerate is a MEDIUM finding, not a HIGH — the site catches up on
  the next deploy.

## Repo traps
- This repo pins dependency versions with `npm ci`, never `npm install`, in every script and
  CI step. A suggestion or doc naming `npm install` in a CI context is a finding.
```

A profile only needs the sections that matter for that repo. A one-line `## Already enforced`
list is a legitimate, complete profile.
