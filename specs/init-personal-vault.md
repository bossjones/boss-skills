# Plan: Initialize `personal.vault` as an LLM-Wiki Second Brain (+ vault CLAUDE.md)

## Task Description

Turn the fresh Obsidian vault at `/Users/bossjones/Documents/obsidian/personal.vault` into a
working "second brain" driven by two already-installed toolsets, and give it a vault-level
`CLAUDE.md` that tells any agent how to author pages. Concretely: scaffold the vault with
obsidian-wiki's `wiki-setup`, then write a `CLAUDE.md` (with an `AGENTS.md` symlink) that makes
obsidian-wiki's page schema canonical while folding in the good *authoring principles* from
eugeniughelbur/obsidian-second-brain's `ai-first-rules.md`.

## Objective

When complete: the vault is scaffolded (categories, `index.md`, `log.md`, `hot.md`,
`.manifest.json`, `_meta/taxonomy.md`, `_raw/`), and `$VAULT/CLAUDE.md` exists (with
`AGENTS.md -> CLAUDE.md`) declaring one canonical schema, layering ai-first discipline expressed
in obsidian-wiki's fields, and routing intent to both obsidian-wiki and kepano `obsidian:*` skills.

## Problem Statement

Two gaps and one design trap:

1. **No scaffold.** The vault has only `Welcome.md`, `.obsidian/`, a Claude Code `.claude/`
   workspace, and `logs/`. obsidian-wiki's `wiki-setup` has never run, so there is no `index.md`,
   `_meta/taxonomy.md`, or category folders for the wiki skills to point at.
2. **No vault operating manual.** There is no `CLAUDE.md`/`AGENTS.md` in the vault. Any agent
   authoring a note *outside* a skill invocation has no guardrails, and obsidian-wiki's
   owner-override hook (it reads `$VAULT/AGENTS.md`) stays empty.
3. **The `ai-first-rules.md` trap.** eugeniughelbur/obsidian-second-brain's
   `references/ai-first-rules.md` is a *different, competing* schema. Copying it verbatim would
   collide with obsidian-wiki's schema (`type` vs `category`, `ai-first: true` vs `lifecycle`,
   `confidence: high` vs `base_confidence: 0.65`), producing inconsistent notes.

### Sources

> <quote>obsidian-wiki `CLAUDE.md:134`: "Frontmatter is required. Every wiki page needs:
> `title`, `category`, `tags`, `sources`, `created`, `updated`."</quote>
>
> <quote>obsidian-wiki `.skills/llm-wiki/SKILL.md`: optional `summary` (<=200 chars),
> `relationships` (typed edges), `provenance{extracted/inferred/ambiguous}`, `base_confidence`,
> `lifecycle`; inline provenance markers `^[inferred]` / `^[ambiguous]`; index spacing `( #tag)`.</quote>
>
> <quote>obsidian-wiki `CLAUDE.md:23`: "After reading config, always read
> `$OBSIDIAN_VAULT_PATH/AGENTS.md` if it exists. It contains owner-specific conventions ... that
> override framework defaults for all skills."</quote>
>
> <quote>eugeniughelbur/obsidian-second-brain `references/ai-first-rules.md`: requires
> `date`/`type`/`tags`/`ai-first: true`, a `## For future Claude` preamble, inline recency
> markers with source URLs, `confidence: stated|high|medium|speculation`, mandatory `[[wikilinks]]`,
> anti-fabrication ("never assert absence without exhaustive search"), and unicode hygiene
> (ASCII dashes, straight quotes, ASCII operators).</quote>
>
> <quote>kepano/obsidian-skills README: five skills - `obsidian-markdown` (wikilinks, embeds,
> callouts, properties), `obsidian-bases` (views/filters/formulas), `json-canvas`,
> `obsidian-cli`, `defuddle` (clean-markdown web extraction). Installed as the `obsidian:*` plugin.</quote>

**Answer to the driving question ("does the vault need an ai-first-rules.md, or is formatting
already handled?"):** Formatting is *mostly* handled - obsidian-wiki's skills enforce their schema
whenever invoked. A vault `CLAUDE.md` is still worth having for ad-hoc authoring, folder-map/identity,
and schema-neutral discipline (anti-fabrication, unicode). But we do **not** copy `ai-first-rules.md`;
we distill its *principles* into obsidian-wiki's canonical fields.

## Solution Approach

One authoritative vault doc - `CLAUDE.md`, with `AGENTS.md` symlinked to it - that:

1. **Declares obsidian-wiki's frontmatter schema canonical** (single source of truth).
2. **Re-expresses ai-first principles in obsidian-wiki's fields** (no competing schema):
   - "For future Claude" preamble -> obsidian-wiki's `summary:` field (<=200 chars) + optional
     `> [!tldr]` callout body.
   - `confidence: stated|high|medium|speculation` -> `base_confidence` + `provenance{}` + inline
     `^[inferred]` / `^[ambiguous]` markers.
   - Recency markers + verbatim source URLs -> `sources:` + inline `(as of YYYY-MM, url)`.
   - Mandatory `[[wikilinks]]` + stubs, anti-fabrication / false-absence hard rule, unicode
     hygiene, compile-don't-retrieve - kept as-is (schema-neutral).
3. **Routes intent** to obsidian-wiki skills (ingest/query/maintain/export) and kepano `obsidian:*`
   skills (native Obsidian syntax: callouts, properties, Bases, Canvas, web clip).

Scaffold first (so the doc's folder map is real), then write the doc.

## Relevant Files

- `/Users/bossjones/dev/obsidian-wiki/CLAUDE.md` - canonical schema, Config Resolution Protocol,
  `$VAULT/AGENTS.md` override hook, skill routing table, visibility tags, Core Principles.
- `/Users/bossjones/dev/obsidian-wiki/.skills/wiki-setup/SKILL.md` - exact scaffold steps
  (category dirs, `index.md`/`log.md`/`hot.md`/`.manifest.json`/`_meta/taxonomy.md`).
- `/Users/bossjones/dev/obsidian-wiki/.skills/llm-wiki/SKILL.md` - full page templates,
  provenance markers, index `( #tag)` spacing rule.
- `/Users/bossjones/dev/obsidian-second-brain/references/ai-first-rules.md` - the *principles*
  distilled (preamble, recency, verbatim sources, confidence, anti-fabrication, unicode).
- `~/.obsidian-wiki/config` - authoritative vault path + QMD settings (already correct).
- `/Users/bossjones/dev/bossjones/boss-skills/cliff.toml` + boss-skills `Makefile` (`changelog`,
  `changelog-preview` targets) - the in-repo git-cliff reference this Phase B mirrors.

### New Files

- `specs/init-personal-vault.md` (this file) - the spec.
- `/Users/bossjones/Documents/obsidian/personal.vault/CLAUDE.md` - vault operating manual.
- `/Users/bossjones/Documents/obsidian/personal.vault/AGENTS.md` - **symlink** -> `CLAUDE.md`.
- Vault scaffold (created by `wiki-setup`): `index.md`, `log.md`, `hot.md`, `.manifest.json`,
  `_meta/taxonomy.md`, folders `concepts/ entities/ skills/ references/ synthesis/ journal/
  projects/ _raw/ _archives/`.

Phase B (changelog + release tooling) adds: `cliff.toml` (git-cliff config), `Makefile`
(git-cliff utility commands), and a git-cliff-generated `CHANGELOG.md`. git-cliff itself is a
global CLI (already installed via Homebrew) - not a project dependency. Migrating an
already-built vault also REMOVES the prior Python tooling (`scripts/changelog.py`, `scripts/tests/`,
`pyproject.toml`, `uv.lock`).

## Step by Step Tasks

IMPORTANT: Execute every step in order, top to bottom.

### 1. Confirm prerequisites (read-only)

- `obsidian-wiki info` and `cat ~/.obsidian-wiki/config` - confirm vault path + QMD.
- Confirm the vault has no existing `index.md` / `CLAUDE.md` (avoid clobbering). Leave `Welcome.md`.

### 2. Scaffold the vault (obsidian-wiki `wiki-setup`)

- Invoke the `wiki-setup` skill against `$OBSIDIAN_VAULT_PATH`. Skip the `.env` prompts - global
  `~/.obsidian-wiki/config` already resolves (Config Resolution Protocol falls back to it).
- Result: category folders + `_raw/ _archives/`, `index.md`, `log.md`, `hot.md`,
  `.manifest.json`, `_meta/taxonomy.md`. Do not enable `WIKI_STAGED_WRITES` unless requested.

### 3. Write the vault `CLAUDE.md`

Author `$VAULT/CLAUDE.md` with the following content (obsidian-wiki schema canonical, ai-first
principles folded in):

```markdown
# personal.vault - Second Brain (Agent Operating Manual)

This vault is an **LLM-Wiki second brain** (Karpathy's "compile, don't retrieve").
The engine is **obsidian-wiki** (globally installed, config at `~/.obsidian-wiki/config`).
Resolve config via obsidian-wiki's Config Resolution Protocol before any vault op.

## Schema is canonical (obsidian-wiki)
Every page REQUIRES frontmatter: `title`, `category`, `tags`, `sources`, `created`, `updated`.
Recommended: `summary` (<=200 chars), `aliases`, `relationships` (typed edges),
`provenance{extracted,inferred,ambiguous}`, `base_confidence` (0.0-1.0), `lifecycle`.
Categories: concepts / entities / skills / references / synthesis / journal / projects.
Do NOT introduce a competing schema (no `type:`, no `ai-first: true`, no
`confidence: stated|high|...`). Use the fields above.

## Authoring discipline (ai-first principles, in obsidian-wiki's fields)
1. Self-contained - each note explains what/why/when without relying on backlinks.
2. Scannable preamble - put the "for future Claude" summary in the `summary:` field
   (<=200 chars); optional `> [!tldr]` callout at top of body.
3. Recency + verbatim sources - inline `(as of YYYY-MM, url)`; keep URLs in `sources:`
   unmodified for re-verification.
4. Confidence - use `base_confidence` + `provenance{}` in frontmatter and inline
   `^[inferred]` / `^[ambiguous]` markers. (NOT `confidence: high`.)
5. Cross-links mandatory - every person/project/concept as `[[wikilinks]]`; create a stub
   if the target is missing.
6. Anti-fabrication (HARD) - never invent facts/dates/relationships; mark unknowns `TBD`.
   Never claim a note/person/file is absent without exhaustive search (false-absence is the
   top failure mode).
7. Unicode hygiene - ASCII ` - ` dashes, straight `"` quotes, ASCII operators (`>=`, `!=`).
8. Compile, don't retrieve - update the existing page; never append a duplicate.
9. Tags - max 5 domain tags, consult `_meta/taxonomy.md` first; `visibility/*` tags are
   separate and don't count toward the limit. Index lines use `( #tag)` spacing.

## Skill routing
- Ingest / capture / query / maintain / export -> obsidian-wiki skills (`wiki-ingest`,
  `wiki-capture`, `wiki-query`, `wiki-lint`, `cross-linker`, `tag-taxonomy`, `wiki-export`, ...).
- Native Obsidian syntax -> kepano `obsidian:*` skills: `obsidian:obsidian-markdown`
  (callouts, properties, embeds, wikilinks), `obsidian:obsidian-bases` (Bases views),
  `obsidian:json-canvas` (Canvas), `obsidian:obsidian-cli`, `obsidian:defuddle` (web clip).

## Maintained files (keep current on every write)
`index.md`, `log.md`, `hot.md`, `.manifest.json` - per obsidian-wiki Core Principles.

## Conventional Commits (drive the changelog)
Commit messages follow Conventional Commits - git-cliff parses them to build `CHANGELOG.md` and
infer the next version. Format: `type(scope)!: description` + optional body + `BREAKING CHANGE:`
footer.

| Prefix | Bump | Keep a Changelog section |
| --- | --- | --- |
| `feat:` | minor | Added |
| `fix:` | patch | Fixed |
| `perf:` / `refactor:` / `revert:` | none | Changed |
| `deprecate:` | none | Deprecated |
| `docs:` | none | Documentation |
| `type!:` or `BREAKING CHANGE:` footer | major | (breaking) |
| security-related (matched in body) | - | Security |
| `chore:` / `ci:` / `test:` / `style:` / `build:` | none | (skipped) |

- Scope split: note-content commits use `content:` or `chore(notes):` - git-cliff SKIPS them, so
  they stay in `log.md`. Vault-level changes (structure, CLAUDE.md rules/schema, scripts, Make
  tasks, skills, reorganizations) use the mapped prefixes above so they land in `CHANGELOG.md`.
- Breaking changes: append `!` (`feat!:`) or add a `BREAKING CHANGE:` footer - either bumps major.
- Same unicode hygiene as notes (ASCII dashes/quotes/operators).

## Changelog and releases
`CHANGELOG.md` (Keep a Changelog + SemVer) is FULLY GENERATED by **git-cliff** from Conventional
Commits - never hand-edit it. It records VAULT-LEVEL changes only; day-to-day note writes live in
`log.md` (see the scope split above).

- Regenerate: `make changelog`. Preview the Unreleased section: `make changelog-preview`.
- Next version (computed from unreleased commits): `make next-version`.
- Cut a release (author-driven, local-only): `make release` bumps the version, regenerates
  `CHANGELOG.md`, commits, and creates an annotated tag; then `make release-push` pushes and runs
  `gh release create`. Releases are local-only until you run release-push.
- `GITHUB_TOKEN` (from `gh auth token`) enriches entries with PR links, `@usernames`, and
  first-time contributors. The compare-link footer is auto-maintained by git-cliff.
```

### 4. Create the `AGENTS.md` symlink

- From the vault root: `ln -s CLAUDE.md AGENTS.md` (relative symlink) so obsidian-wiki's
  `$VAULT/AGENTS.md` lookup and non-Claude agents resolve to the same manual. Verify with
  `readlink`.

### 5. Validate end-to-end

- Run the Validation Commands below. Smoke test: ask a wiki skill (`wiki-capture` or `wiki-ingest`
  on a tiny source) to author one stub note; confirm the frontmatter matches the canonical schema
  and the note appears in `index.md`.

## Testing Strategy

- **Structural**: scaffold files/folders exist; `_meta/taxonomy.md` present.
- **Symlink**: `readlink "$VAULT/AGENTS.md"` -> `CLAUDE.md`; both open identical content.
- **Schema conformance**: a skill-authored page has required keys (`title`, `category`, `tags`,
  `sources`, `created`, `updated`) and no forbidden keys (`type:`, `ai-first:`, `confidence:`).
- **Query path**: `wiki-query` returns an answer with `[[wikilink]]` citations from the new page.
- **Lint**: `wiki-lint` reports zero broken links / no orphan after cross-linking.

## Acceptance Criteria

- Vault scaffold present: category folders + `_raw/`, `index.md`, `log.md`, `hot.md`,
  `.manifest.json`, `_meta/taxonomy.md`.
- `$VAULT/CLAUDE.md` exists, makes obsidian-wiki's schema canonical, folds in ai-first principles
  using obsidian-wiki fields (no competing schema), and routes to obsidian-wiki + kepano skills.
- `$VAULT/AGENTS.md` is a symlink to `CLAUDE.md` and resolves.
- A skill-authored smoke-test note conforms to the canonical schema and appears in `index.md`.

## Validation Commands

Execute these to validate the task is complete (`$VAULT` = the vault path):

- `obsidian-wiki info` - confirms vault path + config resolve.
- `ls -la "$VAULT"` and `ls "$VAULT"/_meta` - scaffold + taxonomy present.
- `test -f "$VAULT/index.md" && test -f "$VAULT/log.md" && test -f "$VAULT/hot.md"` - special files.
- `readlink "$VAULT/AGENTS.md"` - prints `CLAUDE.md`.
- `grep -nE '^(title|category|tags|sources|created|updated):' "$VAULT"/<new-note>.md` - required
  keys present.
- `! grep -nE '^(type|ai-first|confidence):' "$VAULT"/<new-note>.md` - no competing-schema keys.
- (in boss-skills) `make markdown-lint` and `make link-check` - this spec lints clean.

## Phase B: Changelog & Release Tooling (git-cliff)

Phase A (above) scaffolds the vault and its operating manual. Phase B wires **git-cliff** - a
Conventional-Commit-driven changelog generator - to produce a GitHub + Keep a Changelog
`CHANGELOG.md` and a `gh`-backed release flow for vault-level changes. git-cliff is already
installed (Homebrew, v2.11.0) and is a global CLI, NOT a project dependency.

### B0. Decisions & scope

- **Engine**: git-cliff (`brew install git-cliff`); config in `$VAULT/cliff.toml`. Mirror the
  in-repo template `boss-skills/cliff.toml` (a tailored `github-keepachangelog.toml`).
- **Format**: GitHub + Keep a Changelog + SemVer; `[Unreleased]` on top; auto-maintained
  compare-link footer; PR links / `@usernames` / first-time contributors via `[remote.github]` +
  `GITHUB_TOKEN`.
- **Scope (what earns an entry)**: vault-level changes only, enforced by COMMIT CONVENTION.
  Vault-level commits use `feat/fix/docs/perf/refactor/...` (mapped to KaC groups); note-content
  commits use `content:` or `chore(notes):`, which git-cliff SKIPS - they stay in `log.md`.
- **Versioning**: git-cliff infers the next version from unreleased commits (`--bumped-version`):
  `feat` -> minor, `fix` -> patch, `!` / `BREAKING CHANGE:` -> major (via `[bump]`).
- **Release reach**: `make release` is **local-only** (bump + regenerate + commit + annotated tag).
  Pushing + the GitHub release is the separate, explicit `make release-push`.
- **Migration**: if the vault still carries the earlier Python tooling, REMOVE it -
  `scripts/changelog.py`, `scripts/tests/` (+ `__pycache__`), `pyproject.toml`, `uv.lock`, and the
  hand-authored `CHANGELOG.md` (git-cliff regenerates it).

### B1. Add `$VAULT/cliff.toml`

Mirror `boss-skills/cliff.toml` (the `[changelog]` `body`/`footer` templates are reproduced
verbatim - they read `remote.github.owner`/`repo` dynamically). Adapt: set `[remote.github]` to this
vault, reword the header, map `docs` -> Documentation (CLAUDE.md/rule changes are real entries), and
add skip parsers for the note-content prefixes.

```toml
# git-cliff ~ configuration file  -  https://git-cliff.org/docs/configuration
# Tailored from the upstream GitHub + Keep a Changelog example:
# https://github.com/orhun/git-cliff/blob/main/examples/github-keepachangelog.toml
# Parsers key off this vault's conventional-commit prefixes (feat/fix/docs/...).
# Scope: VAULT-LEVEL only. Note-content commits use content:/chore(notes): and are skipped.

[remote.github]
owner = "bossjones"
repo = "personal.vault"

[changelog]
header = """
# Changelog\n
All notable changes to this vault's structure, rules, and tooling are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this vault adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).\n
"""
body = """
{%- macro remote_url() -%}
  https://github.com/{{ remote.github.owner }}/{{ remote.github.repo }}
{%- endmacro -%}

{% if version -%}
    ## [{{ version | trim_start_matches(pat="v") }}] - {{ timestamp | date(format="%Y-%m-%d") }}
{% else -%}
    ## [Unreleased]
{% endif -%}

{% for group, commits in commits | group_by(attribute="group") %}
    ### {{ group | upper_first }}
    {%- for commit in commits %}
        - {{ commit.message | split(pat="\n") | first | upper_first | trim }}\
            {% if commit.remote.username %} by @{{ commit.remote.username }}{%- endif -%}
            {% if commit.remote.pr_number %} in \
            [#{{ commit.remote.pr_number }}]({{ self::remote_url() }}/pull/{{ commit.remote.pr_number }}) \
            {%- endif -%}
    {% endfor %}
{% endfor %}

{%- if github.contributors | filter(attribute="is_first_time", value=true) | length != 0 %}
    ### New Contributors
{%- endif -%}

{% for contributor in github.contributors | filter(attribute="is_first_time", value=true) %}
  * @{{ contributor.username }} made their first contribution
    {%- if contributor.pr_number %} in \
      [#{{ contributor.pr_number }}]({{ self::remote_url() }}/pull/{{ contributor.pr_number }}) \
    {%- endif %}
{%- endfor %}\n

{%- if github.contributors | filter(attribute="is_first_time", value=true) | length != 0 %}{% raw %}\n{% endraw -%}{% endif %}

"""
footer = """
{%- macro remote_url() -%}
  https://github.com/{{ remote.github.owner }}/{{ remote.github.repo }}
{%- endmacro -%}

{% for release in releases -%}
    {% if release.version -%}
        {% if release.previous and release.previous.version -%}
            [{{ release.version | trim_start_matches(pat="v") }}]: \
                {{ self::remote_url() }}/compare/{{ release.previous.version }}...{{ release.version }}
        {% endif -%}
    {% else -%}
        {% if release.previous and release.previous.version -%}
            [unreleased]: {{ self::remote_url() }}/compare/{{ release.previous.version }}...HEAD
        {% else -%}
            [unreleased]: {{ self::remote_url() }}/commits/HEAD
        {% endif -%}
    {% endif -%}
{% endfor %}
<!-- generated by git-cliff -->
"""
trim = true

[git]
conventional_commits = true
filter_unconventional = true
commit_preprocessors = [
    # Strip inline issue refs like "(#123)"; PR links come from remote data.
    { pattern = '\((\w+\s)?#([0-9]+)\)', replace = "" },
]
# Order matters: skips/specifics before broad type matches.
commit_parsers = [
    { message = "^chore\\(deps", skip = true },
    { message = "^chore\\(notes", skip = true },   # note-write commits -> stay in log.md
    { message = "^content", skip = true },          # note-write commits -> stay in log.md
    { message = "^feat", group = "Added" },
    { message = "^fix", group = "Fixed" },
    { message = "^perf", group = "Changed" },
    { message = "^refactor", group = "Changed" },
    { message = "^revert", group = "Changed" },
    { message = "^deprecate", group = "Deprecated" },
    { message = "^docs?", group = "Documentation" },
    { body = ".*security", group = "Security" },
    { message = "^chore", skip = true },
    { message = "^ci", skip = true },
    { message = "^test", skip = true },
    { message = "^style", skip = true },
    { message = "^build", skip = true },
]
filter_commits = true
topo_order = false
sort_commits = "newest"

[bump]
features_always_bump_minor = true
breaking_always_bump_major = true
initial_tag = "v0.1.0"
```

### B2. Add `$VAULT/Makefile` (git-cliff utility commands)

Pure git-cliff wrappers - no `uv`/Python. `GITHUB_TOKEN` falls back to `gh auth token` so remote
enrichment (PR links, contributors) works without exporting a token. Because `[remote.github]`
makes git-cliff call the GitHub API on EVERY run (a private repo 404s unauthenticated), ALL
invocations - including `--bumped-version` - go through the `$(GC)` token wrapper. `## help` targets
are auto-listed by a grep+awk generator.

```makefile
.DEFAULT_GOAL := help
GC = GITHUB_TOKEN="$${GITHUB_TOKEN:-$$(gh auth token 2>/dev/null)}" git-cliff

.PHONY: help changelog changelog-preview changelog-latest changelog-context next-version release release-push install-git-cliff

help: ## Show this help message
	@grep -hE '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
changelog: ## Regenerate CHANGELOG.md from conventional commits
	@command -v git-cliff >/dev/null 2>&1 || { echo "install: brew install git-cliff"; exit 1; }
	@$(GC) --output CHANGELOG.md
changelog-preview: ## Preview the Unreleased section (stdout, no write)
	@$(GC) --unreleased
changelog-latest: ## Show the latest released section
	@$(GC) --latest
changelog-context: ## Dump the Unreleased context as JSON (debug)
	@$(GC) --unreleased --context
next-version: ## Print the next version git-cliff would bump to
	@$(GC) --bumped-version
release: ## Cut a local release: bump + regenerate + commit + tag (no push)
	@git diff --quiet || { echo "working tree dirty - commit/stash first"; exit 1; }
	@V=$$($(GC) --bumped-version) && \
	 $(GC) --bump --output CHANGELOG.md && \
	 git add CHANGELOG.md && git commit -m "chore(release): $$V" && \
	 git tag -a "$$V" -m "Release $$V" && \
	 echo "Tagged $$V locally. Run 'make release-push' to publish."
release-push: ## Push the latest tag + create the GitHub release
	@V=$$(git describe --tags --abbrev=0) && \
	 git push --follow-tags && \
	 $(GC) --latest --strip all | gh release create "$$V" --title "$$V" --notes-file -
install-git-cliff: ## Install git-cliff via Homebrew
	@brew install git-cliff
```

### B3. Wire the vault `CLAUDE.md`

- Add the `## Conventional Commits` section and the git-cliff `## Changelog and releases` section
  (both shown in the Phase A template above) after `## Maintained files`.
- Together they document the commit-prefix -> KaC-group mapping and the `log.md`-vs-`CHANGELOG.md`
  scope split.

### B4. Generate + validate

- First run: `make changelog` regenerates `CHANGELOG.md` from git history. Early commits may predate
  the convention; review the output and optionally cut a `v0.1.0` baseline. Validate the release flow
  on a scratch branch before running it on `feature-init-brain`/`main`.
- If migrating: delete the prior Python tooling first (`scripts/changelog.py`, `scripts/tests/`,
  `pyproject.toml`, `uv.lock`) so `make changelog` output is the single source of truth.

### Phase B validation commands (in `$VAULT`)

Run through the `make` wrappers - they inject `GITHUB_TOKEN` from `gh auth token`, which git-cliff
needs to resolve `[remote.github]` for a private repo (a bare `git-cliff` call omits the token and
404s on the GitHub API).

- `git-cliff --version` - engine present (else `brew install git-cliff`).
- `make changelog-preview` - config parses; Unreleased renders with the right groups
  (Added/Changed/Fixed/Documentation/...); note-content commits (`content:`/`chore(notes):`) are absent.
- `make next-version` - prints the next semver from unreleased commits (`v0.1.0` on a fresh vault).
- `make changelog && head -20 CHANGELOG.md` - Keep a Changelog output: header + `[Unreleased]` +
  auto-maintained compare-link footer pointing at `bossjones/personal.vault`.

### Phase B acceptance criteria

- `$VAULT/cliff.toml` mirrors boss-skills' git-cliff config, sets `[remote.github]` to
  `bossjones/personal.vault`, maps conventional prefixes to KaC groups, and SKIPS note-content
  prefixes (`content:` / `chore(notes):`).
- `make changelog` produces a valid GitHub + Keep a Changelog `CHANGELOG.md` with an auto-maintained
  compare-link footer; `make changelog-preview` / `make changelog-latest` / `make next-version` work.
- `make release` bumps via git-cliff, regenerates `CHANGELOG.md`, commits, and creates a LOCAL
  annotated tag without pushing; `make release-push` pushes + `gh release create`.
- Vault `CLAUDE.md` has a `## Conventional Commits` section and a git-cliff `## Changelog and
  releases` section documenting the scope split.
- Any prior Python changelog tooling (`scripts/changelog.py`, `scripts/tests/`, `pyproject.toml`,
  `uv.lock`) is removed.

## Notes

- `$VAULT` = `/Users/bossjones/Documents/obsidian/personal.vault` (authoritative path lives in
  `~/.obsidian-wiki/config`, not an env var).
- No new libraries needed - obsidian-wiki (v2026.6.9) and kepano `obsidian:*` skills are already
  installed; obsidian-wiki's 36 skills are symlinked into `~/.claude/skills`.
- QMD (`cli`, quality mode) is already configured; wiki skills use it and fall back to Grep if
  unavailable. Optional follow-up once the vault has content:
  `qmd collection add "$VAULT" --name wiki && qmd embed`.
- Leave `Welcome.md` in place; `wiki-setup` does not remove it.
- This spec is the vault-level complement to the machine-level setup already documented in
  `specs/second-brain.md`, the `setup-second-brain` skill, and
  `docs/tutorials/agent-harness/second-brain.md` - not a duplicate.
- Phase B needs no project dependencies - git-cliff is a global CLI (`brew install git-cliff`;
  installed v2.11.0, upstream latest 2.13.1). `GITHUB_TOKEN` for remote enrichment falls back to
  `gh auth token`. `.gitignore` already anticipates a `Makefile`.
- The vault and boss-skills now share ONE changelog engine (git-cliff); `$VAULT/cliff.toml` mirrors
  `boss-skills/cliff.toml`. An earlier revision of this spec used a stdlib Python `changelog.py`;
  git-cliff replaces it (see the Phase B migration note). Because git-cliff generates from commits,
  Conventional Commit discipline (Phase A `CLAUDE.md` template) is what keeps `CHANGELOG.md`
  vault-level and note writes in `log.md`.
