---
name: version-bump-reviewer
description: >
  Reviews uncommitted changes to decide whether a semver bump is required and applies the
  correct version artifact. Handles plugin skills and components, repo-internal skills,
  and new marketplace plugins; classifies major, minor, patch, or no-bump changes; uses
  plugin-eval evidence for skill edits; syncs plugin.json with marketplace.json; updates
  metadata.version for repo-internal skills; validates initial-publish parity; and creates
  a conventional commit. Use when feature-bearing files under plugins/ or .claude/skills/
  change, a marketplace plugin entry is added, versions may be out of sync, or the user
  asks to bump, release, introduce, or prepare a skill or plugin for merge. Run after
  plugin-dev:skill-reviewer.
allowed-tools: Bash(git diff *) Bash(git status *) Bash(git log *) Bash(git show *) Bash(git ls-tree *) Bash(git add *) Bash(git commit *) Bash(make *) Bash(uvx *) Bash(mkdir *) Bash(cp *) Read Edit
metadata:
  version: 0.1.2
---

# Version Bump Reviewer

Decides whether a plugin or skill change needs a semver bump and at what tier, then
propagates the new version through every file that has to stay in sync for this repo, and
writes a conventional-commit message a future CHANGELOG generator can grep. This skill is
the version-aware sibling to the `plugin-dev:skill-reviewer` agent: that agent flags policy and quality
issues; this skill reasons about versioning and commits the result.

The primary question this skill answers is **"does this change need a version bump, and
if so, what tier?"** — "no bump needed" is a first-class, expected outcome.

The skill is plugin-aware, not just SKILL.md-aware. Plugins can ship feature changes via
many surfaces (a new `.lsp.json`, a new `commands/foo.md`, a new agent, a new MCP server,
a new hook), and all of those should bump the owning plugin's `version` so installed users
actually receive the update. Marketplace docs are explicit: users only get plugin updates
when `plugin.json.version` (or the `plugins[].version` in `marketplace.json`) is bumped.

## When to invoke

- **Auto-triggered** by `.claude/hooks/version-bump-reviewer.py` whenever `Edit`, `Write`,
  or `MultiEdit` touches any of these paths:
  - `plugins/<category>/<plugin>/skills/<name>/SKILL.md` — plugin skill (existing).
  - `.claude/skills/<name>/SKILL.md` — repo-internal skill (existing).
  - `plugins/<category>/<plugin>/commands/*.md` — slash commands.
  - `plugins/<category>/<plugin>/agents/*.md` — subagents.
  - `plugins/<category>/<plugin>/hooks/hooks.json` — plugin hooks.
  - `plugins/<category>/<plugin>/.lsp.json` — LSP servers.
  - `plugins/<category>/<plugin>/.mcp.json` — MCP servers.
  - `plugins/<category>/<plugin>/monitors/monitors.json` — background monitors.
  - `plugins/<category>/<plugin>/settings.json` — default settings.
  - `plugins/<category>/<plugin>/bin/**` — shipped executables.
  - `plugins/<category>/<plugin>/.claude-plugin/plugin.json` — manifest (catches new
    plugin publishes and direct metadata edits).
  - `.claude-plugin/marketplace.json` — marketplace registry (catches new `plugins[]`
    entries and version drift).

  The hook runs alongside `skill-edit-review.py`; both fire independently. Address
  `plugin-dev:skill-reviewer` findings first, then run this skill.
- **Model-invoked** when the user asks to bump a version, cut a release, prepare a skill
  for merge, introduce/publish a new plugin, verify whether a change needs a bump, or
  sync a plugin's package version.
- Skip when no feature-bearing file is in the working tree (nothing drives a bump).
- Skip when the diff is an empty touch with no real content change.
- Skip when only non-behavior files changed (README.md, LICENSE, .gitignore, `tests/**`).

## Change classes and version artifacts

The changed path(s) determine the change class and which version artifact(s) get bumped.

| Path shape | Class | Version artifact(s) |
|------------|-------|---------------------|
| `plugins/<category>/<plugin>/skills/<name>/SKILL.md` | **Plugin skill** | `version` in `plugins/<category>/<plugin>/.claude-plugin/plugin.json` **and** the matching `plugins[]` entry in `.claude-plugin/marketplace.json`, located by `source == "./plugins/<category>/<plugin>"`. Bumped in lockstep, same tier. |
| `plugins/<category>/<plugin>/<component>` (commands, agents, hooks, `.lsp.json`, `.mcp.json`, monitors, settings, bin) | **Plugin component change** | Same artifacts as plugin skill — `plugin.json` + matching `marketplace.json` entry, in lockstep. SKILL.md is **not** touched. |
| `.claude-plugin/marketplace.json` adds a new `plugins[]` entry **and** the referenced `plugin.json` did not exist at `HEAD` | **New plugin publish** | Validate `plugin.json.version == marketplace.json[].version`; if mismatch, surface and pick the larger. **No bump** — this is initial publish. Emit `feat` commit. |
| `.claude/skills/<name>/SKILL.md` | **Repo-internal skill** | `metadata.version` in this SKILL.md's own frontmatter. Introduce the field at `0.1.0` if absent. No marketplace or plugin.json artifact applies. |

The repo's top-level `.claude-plugin/marketplace.json` `metadata.version` is **out of
scope** — it is informational only per Claude Code docs; per-plugin `version` is what
gates user updates. Do not touch the top-level `metadata.version`.

## Inputs the skill gathers

1. The list of changed feature-bearing files in the working tree:

   ```
   $ git diff --name-only HEAD -- \
       'plugins/**/SKILL.md' \
       '.claude/skills/**/SKILL.md' \
       'plugins/**/commands/*.md' \
       'plugins/**/agents/*.md' \
       'plugins/**/hooks/hooks.json' \
       'plugins/**/.lsp.json' \
       'plugins/**/.mcp.json' \
       'plugins/**/monitors/monitors.json' \
       'plugins/**/settings.json' \
       'plugins/**/bin/**' \
       'plugins/**/.claude-plugin/plugin.json' \
       '.claude-plugin/marketplace.json'
   ```

   Plus `git status --short` to catch untracked new files.
2. The full uncommitted diff for the chosen target path(s), via `git diff HEAD -- <path>`
   (or `git diff --no-index /dev/null <path>` for an untracked new file).
3. The change class and, for plugin-skill or plugin-component changes, the owning plugin
   directory, its `plugin.json` `version`, and the matching `marketplace.json`
   `plugins[].version`.
4. For a repo-internal skill, the current `metadata.version` in the SKILL.md frontmatter
   (or the fact that it is absent).
5. The `marketplace.json` diff (only when that file changed), to detect new `plugins[]`
   entries that signal a new-plugin publish.
6. A `plugin-eval` score for the SKILL.md before and after the change (see Phase 4) —
   **only for SKILL.md targets**, skipped for component-only and new-publish events.

## Workflow

### Phase 1 — Pick exactly one target

Run the changed-files query above. If empty, also check `git status --short` for
untracked feature-bearing files.

Group the changed paths by **owning plugin** (or by SKILL.md for repo-internal skills,
or by marketplace.json for the new-publish case):

- A plugin-skill SKILL.md edit + a sibling component edit in the same plugin → one
  group, one bump, one commit. Rubric tier is the highest across both.
- Two different plugins changed → two groups, handle alphabetically first by plugin
  path; list the rest for re-run.
- A repo-internal skill change → its own group.
- A `marketplace.json` change with a new `plugins[]` entry → its own group (new
  publish).

Outcomes:

- **Zero changed targets** → tell the user there is nothing to review and stop.
- **One group** → that is the target.
- **More than one group** → pick the first one alphabetically by group key, do the full
  workflow for it, and at the end tell the user to re-run the skill for each remaining
  group (list them). Each group gets its own independent commit so the future CHANGELOG
  generator can attribute changes correctly.

### Phase 2 — Resolve change class and version artifacts

Classify the target group:

- **Plugin skill** — a `SKILL.md` matching `plugins/<category>/<plugin>/skills/<name>/`
  is in the group. Owning plugin manifest:
  `plugins/<category>/<plugin>/.claude-plugin/plugin.json`. Marketplace entry: the
  element of `.claude-plugin/marketplace.json` `plugins[]` whose `source` is
  `./plugins/<category>/<plugin>`.
  - **Edge — unregistered plugin:** if the plugin has a `plugin.json` but no matching
    `marketplace.json` entry, bump `plugin.json` only and surface a finding telling the
    user the plugin is not yet registered.

- **Plugin component change** — the group has only feature-bearing component files
  (no SKILL.md), all under one plugin directory. Same artifacts as plugin skill
  (`plugin.json` + `marketplace.json` entry). SKILL.md is **not** edited.

- **New plugin publish** — `marketplace.json` has a new `plugins[]` entry AND the
  referenced plugin directory's `plugin.json` did not exist at `HEAD`. Detect via:

  ```
  $ git show HEAD:plugins/<category>/<plugin>/.claude-plugin/plugin.json 2>/dev/null
  ```

  If the command fails (no such path at HEAD), this is a new publish. Artifacts: confirm
  parity between `plugin.json.version` and the new `marketplace.json[].version`. **No
  bump**. See Phase 2.5.

- **Repo-internal skill** — `.claude/skills/<name>/SKILL.md` is in the group. The only
  artifact is `metadata.version` in the SKILL.md frontmatter.

### Phase 2.5 — New-plugin publish short-circuit

If the change class is **new plugin publish**:

1. Read `plugin.json.version` (call it `MANIFEST_V`) and the new
   `marketplace.json[].version` for the same `source` (call it `MARKET_V`).
2. If `MANIFEST_V != MARKET_V`, surface this as a parity finding and take the larger
   as the published version. Edit the smaller artifact to match.
3. If both match, no edits are needed for this phase.
4. Skip Phases 3–6 entirely (no rubric, no bump computation).
5. Continue to Phase 7 (no-op for parity-already-aligned), Phase 8 (validate), Phase 9
   (commit as `feat(<plugin>): introduce <plugin> at v<MANIFEST_V>`).

### Phase 3 — Read current versions and detect author intent

(Skip for new-plugin publish — already handled in Phase 2.5.)

- **Plugin skill or plugin component change:** read `plugin.json` `version`
  (`CURRENT_PLUGIN_VERSION`) and the matching `marketplace.json` `plugins[].version`
  (`CURRENT_MARKETPLACE_VERSION`). They should match; if they don't, that's a finding
  to surface — proceed and bring both to the same new version.
- **Repo-internal skill:** read `metadata.version` from the SKILL.md frontmatter
  (`CURRENT_INTERNAL_VERSION`). If the field is absent, this is a field-introduction
  case: treat the baseline as unset and default to `0.1.0` (see Phase 6).
- **Author intent / baseline.** From `git diff HEAD --` against the relevant manifest /
  frontmatter files, find any removed line (prefixed `-`) that set a `version` /
  `metadata.version`. If found, parse it as `ORIGINAL_VERSION` (the pre-edit baseline).
  If no version line was removed, set `ORIGINAL_VERSION = CURRENT_*_VERSION`. This
  anchors the author-bump floor in Phase 6.

### Phase 4 — plugin-eval before/after signal (SKILL.md targets only)

This is a corroborating signal that feeds the tier decision **for SKILL.md changes**. It
can **escalate** the rubric tier but must never silently lower it. The content-diff
rubric (Phase 5) remains the primary classifier.

**Skip entirely** for plugin-component-only changes and for new-plugin publish. There
is no SKILL.md diff to score; report `plugin-eval: n/a (component change, no SKILL.md
edit)` in the commit body.

`plugin-eval` is built on demand via `uvx` from the vendored, locally-patched copy at
`scripts/plugin_eval/`. Use the same invocation contract as `scripts/eval-skills.py`
(`PLUGIN_EVAL_SOURCE` still overrides the default):

```
$ SRC="${PLUGIN_EVAL_SOURCE:-./scripts/plugin_eval}"
$ uvx --from "$SRC" plugin-eval score <dir> --depth quick --output json
```

`--depth quick` is the static layer only: deterministic, free, no API key — safe as a
gate. `standard`/`certify` (LLM judge / Monte Carlo) are optional manual deep-dives;
never require them for the bump decision.

- **BEFORE** (skip if the SKILL.md is untracked / brand-new): create a temp dir, copy
  the skill directory into it, overwrite the copy's `SKILL.md` with the committed
  version, and score it:

  ```
  $ TMP=$(mktemp -d)
  $ cp -R <skill-dir>/. "$TMP"/
  $ git show HEAD:<path-to-SKILL.md> > "$TMP"/SKILL.md
  $ uvx --from "$SRC" plugin-eval score "$TMP" --depth quick --output json
  ```

- **AFTER**: score the working-tree skill directory. Prefer `scripts/eval-skills.py
  --skill <skill-dir>` for parity with CI, or run the same `uvx ... --output json`
  command against `<skill-dir>` for an apples-to-apples JSON delta.

Capture `composite.score` and the summed `anti_patterns` count from each run. Compute
`Δscore` and `Δanti_patterns`. Interpretation:

- `Δanti_patterns > 0` → a regression was introduced; the change is at least a semantic
  patch (`fix`) and the regression must be called out in the commit body.
- `Δscore` materially negative → flag a quality regression to the user; do not silently
  proceed with a cosmetic classification.
- Structural additions with `Δscore ≥ 0` → corroborates a Minor classification.
- Brand-new / untracked skill → no BEFORE; report the AFTER score as a sanity gate only
  and treat the change as an initial publish.

### Phase 5 — Classify the diff

Apply the rubric below. Highest tier wins — if the diff touches Major and Minor
categories, the result is Major. For SKILL.md targets, fold in the Phase 4 signal: the
eval delta may push the result to a higher tier, never a lower one.

**SKILL.md rubric (plugin skill or repo-internal skill)**

| Tier | Triggers |
|------|----------|
| **Major** | A workflow step was removed; a tool was removed from `allowed-tools` or from the body's tool reference; the skill was renamed (frontmatter `name` changed); the skill's directory was relocated; required inputs/outputs changed in a way that breaks existing callers; a user-facing trigger was narrowed (e.g. `description` lost a context that previously activated the skill). |
| **Minor** | A new workflow step was added; a tool was added; the description was broadened to cover new triggers; new optional functionality that doesn't break existing flows; new edge-case handling. |
| **Patch (semantic)** | A small behavioral fix that changes how a step works without changing its inputs or outputs; correcting a wrong tool argument; tightening a regex or condition; any change where `Δanti_patterns > 0`. |
| **Patch (cosmetic)** | Typos, prose clarifications, reordering paragraphs without semantic change, link fixes, formatting-only changes. |

**Plugin component rubric (commands, agents, hooks, `.lsp.json`, `.mcp.json`, monitors,
settings, bin)**

| Tier | Triggers |
|------|----------|
| **Major** | An existing command/agent file was deleted or renamed; a hook event matcher was removed; an `.lsp.json` language entry was removed; `.lsp.json` `extensionToLanguage` lost an extension; an `.mcp.json` server's `command` changed in a way that breaks callers; a monitor was removed; a settings key callers depended on was removed; a shipped binary was removed or its calling interface changed. |
| **Minor** | A new command/agent/hook/lsp/mcp/monitor was added; `extensionToLanguage` gained a new extension; a new env var was introduced; a new args entry was added to an LSP server without changing existing behavior; a new shipped binary appeared. |
| **Patch (semantic)** | Small behavioral fix — corrected a hook command's arguments, tightened a regex in a matcher, fixed a wrong `transport`, fixed a typo'd MCP server URL that nobody could have been depending on. |
| **Patch (cosmetic)** | Prose-only edits inside a command/agent markdown body (the human-readable description text, not the frontmatter or instructions); whitespace-only JSON reformatting. |

When the rubric is genuinely ambiguous, prefer the higher tier. A wrong Major bump is
recoverable in the next release; a wrong Patch bump that should have been Major
silently breaks downstream installs.

### Phase 6 — Decide bump-or-not and compute the new version

(Skip for new-plugin publish — handled in Phase 2.5.)

**No-bump outcome.** A bump is **not** needed only when the change is a genuine no-op:
an empty touch, a whitespace-only change, or a reordering that produces zero rendered
difference — i.e. `git diff HEAD -- <path>` shows no semantic or visible content
change. In that case report "no version bump is needed", explain why, and stop without
editing or committing. This is the core "verify whether a bump is needed" answer and is
a successful outcome.

A cosmetic **content** change (typo, prose clarification, link fix, formatting that
changes rendered output) is **not** a no-op — it is a Patch (cosmetic) change and
**does** bump (see Phase 5 and the conventional-commit table). Every committed
behavior-bearing content change is attributable in the CHANGELOG; "no bump" never
applies just because a change is small.

Otherwise compute the new version. Parse `ORIGINAL_VERSION` into
`MAJOR.MINOR.PATCH[-PRERELEASE]` and apply the rubric (or escalated) tier:

- Major → `(MAJOR+1).0.0[-PRERELEASE]`
- Minor → `MAJOR.(MINOR+1).0[-PRERELEASE]`
- Patch → `MAJOR.MINOR.(PATCH+1)[-PRERELEASE]`

The pre-release suffix (e.g. `-alpha`) is preserved verbatim. A pre-release stays
pre-release until an author explicitly drops the suffix; this skill never makes that
call.

**Author-bump floor.** If the diff changed a version (`ORIGINAL_VERSION ≠ CURRENT_*`),
take the larger of (`CURRENT_*`, the rubric-computed version). Both are anchored to
the same pre-edit baseline, so the comparison is meaningful: the author's intent is a
floor, never a ceiling. If the rubric demands a higher tier, raise to it and explain
why in the commit body. If no version change was in the diff, use the rubric-computed
version directly.

**Field-introduction (repo-internal, no `metadata.version`).** If the SKILL.md had no
`metadata.version`, introduce it at `0.1.0` (or `0.1.0-alpha` if the author clearly
intends pre-release). The conventional commit type is `feat` (initial versioning).

**Brand-new SKILL.md.** If the file is untracked, do not bump — accept whatever version
the author wrote (default `0.1.0`); the conventional commit type is `feat`.

### Phase 7 — Apply the version edit(s)

- **Plugin skill or plugin component change:** use `Edit` to change `version` in
  `plugins/<category>/<plugin>/.claude-plugin/plugin.json`, and the matching
  `plugins[].version` in `.claude-plugin/marketplace.json`, both to the new version.
  Match enough surrounding context (the plugin's `name`/`source`) to be unambiguous. If
  the plugin is unregistered in `marketplace.json`, edit only `plugin.json` and keep
  the unregistered-plugin finding for the report. For component-only changes, **do not
  edit the SKILL.md** — it didn't change.
- **Repo-internal skill:** use `Edit` to change (or introduce) `metadata.version` in
  the SKILL.md frontmatter. If introducing, add a `metadata:` block with `version:`
  under the frontmatter, matching the existing YAML style.
- **New plugin publish:** if parity was already aligned in Phase 2.5, no edits in this
  phase. If parity was off, the edit was already made in Phase 2.5.

### Phase 8 — Validate

- If `plugin.json` and/or `marketplace.json` were edited (plugin skill, plugin
  component change, or new publish with parity fix), run:

  ```
  $ make verify-structure
  ```

  This validates the marketplace structure and plugin manifests before the commit
  lands.

- The Phase 4 AFTER score (when run) already exercised `plugin-eval`. Require that
  `Δanti_patterns <= 0` relative to BEFORE (no new anti-patterns introduced by the
  version edits). For a repo-internal skill with no manifests touched,
  `make verify-structure` is not required. For component-only and new-publish changes,
  `plugin-eval` is `n/a` and there is no anti-pattern check.

If validation fails, **abort before committing** — leave the file edits on disk,
surface the tool output to the user, and tell them to fix the underlying issue and
re-run. Don't roll back the version edits; the user may want to see them.

### Phase 9 — Stage and commit

Stage exactly the files this skill touched:

- Plugin skill: `git add <path-to-SKILL.md> <plugin.json> .claude-plugin/marketplace.json`
  (omit `marketplace.json` if the plugin is unregistered).
- Plugin component change: `git add <component-paths...> <plugin.json> .claude-plugin/marketplace.json`.
  The component files are the user's already-staged or unstaged work; pull them in
  alongside the version bump so the commit is self-contained.
- New plugin publish: `git add <plugin-root>/ .claude-plugin/marketplace.json` — the
  whole new plugin directory plus the marketplace entry.
- Repo-internal skill: `git add <path-to-SKILL.md>`.

Then commit using the format below. Pass the message via heredoc so multi-line bodies
work:

```
$ git commit -m "$(cat <<'EOF'
<type>(<scope>): <subject> (v<NEW_VERSION>)

- <bullet 1: what changed>
- <bullet 2: plugin/marketplace version bumped to <NEW_VERSION>, or "initial publish">
- <bullet 3: plugin-eval delta — Δscore / Δanti_patterns, or "n/a (component change)">
- <bullet 4: only if author already bumped — note we raised it to match the rubric>

[BREAKING CHANGE: <description>]   # only present when type is feat!
EOF
)"
```

Confirm the commit landed with `git status` and `git log -1 --oneline`. Don't push.

## Conventional commit format

The skill produces commits in this exact shape so a future CHANGELOG generator can
`git log --grep '(v[0-9]'` and parse them deterministically.

| Bump tier              | Commit type             | Scope            | Notes                          |
|------------------------|-------------------------|------------------|--------------------------------|
| Major (SKILL.md)       | `feat(<skill-name>)!:`  | skill directory  | Add `BREAKING CHANGE:` footer  |
| Minor (SKILL.md)       | `feat(<skill-name>):`   | skill directory  |                                |
| Patch (semantic, SKILL.md) | `fix(<skill-name>):` | skill directory  |                                |
| Patch (cosmetic, SKILL.md) | `chore(<skill-name>):` | skill directory | Typos, prose, link fixes      |
| Major (plugin component)   | `feat(<plugin-name>)!:` | plugin name    | Add `BREAKING CHANGE:` footer  |
| Minor (plugin component)   | `feat(<plugin-name>):` | plugin name    | e.g. "add `.lsp.json`"         |
| Patch (semantic, component) | `fix(<plugin-name>):` | plugin name   |                                |
| Patch (cosmetic, component) | `chore(<plugin-name>):` | plugin name |                                |
| New plugin publish     | `feat(<plugin-name>):`  | plugin name      | "introduce <plugin> at v<X.Y.Z>" |
| New skill / first version | `feat(<skill-name>):` | skill directory | "introduce <skill> at v<X.Y.Z>" |

**Scope rule:** when the change is driven by a SKILL.md edit, scope is the skill
directory name (`twitter-to-reel`, `doc-generator`). When the change is a plugin
component change or a new plugin publish (no SKILL.md driving it), scope is the
**plugin** name (`basedpyright-lsp`, `agent-harness`). For a mixed group where both
a SKILL.md and a component changed in the same plugin, use the **skill** name as the
scope and mention the component changes in the body.

The subject line **must** end with `(v<NEW_VERSION>)` — that trailing tag is the grep
anchor for the CHANGELOG generator. For a plugin skill or plugin component change the
anchor is the new plugin version; for a repo-internal skill it is the new
`metadata.version`; for a new publish it is the initial version.

**Examples**

Minor — added a tool to a plugin skill (`twitter-tools` plugin at v0.1.0):

```
feat(twitter-to-reel): add caption-overlay step (v0.2.0)

- Insert Step 4.5 to burn a caption overlay before export
- twitter-tools plugin bumped to v0.2.0 (plugin.json + marketplace.json)
- plugin-eval: Δscore +0.02, Δanti_patterns 0
```

Patch (cosmetic) — prose/typo fix in a plugin skill (`twitter-tools` plugin at v0.1.0):

```
chore(twitter-to-reel): clarify --debug troubleshooting wording (v0.1.1)

- Reword the Debug mode bullet for clarity (no behavior change)
- twitter-tools plugin bumped to v0.1.1 (plugin.json + marketplace.json)
- plugin-eval: Δscore 0, Δanti_patterns 0
```

Field-introduction — repo-internal skill with no prior `metadata.version`
(`doc-generator`); always `feat` at `v0.1.0` regardless of the diff's tier:

```
feat(doc-generator): introduce versioning at v0.1.0 (v0.1.0)

- Add metadata.version: 0.1.0 to frontmatter (field did not exist)
- plugin-eval: Δscore 0, Δanti_patterns 0
```

Major — removed a step and changed required inputs (plugin skill at v1.0.1):

```
feat(twitter-media-downloader)!: drop legacy single-url path (v2.0.0)

- Remove Step 0a (single-url fallback) — batch input is now required
- twitter-tools plugin bumped to v2.0.0 (plugin.json + marketplace.json)
- plugin-eval: Δscore -0.01, Δanti_patterns 0

BREAKING CHANGE: callers passing one URL via the legacy path must now pass an
array under `urls`. The single-url path was deprecated in v1.0.0.
```

Author-bumped floor — author wrote `0.1.1` for a typo, but the diff also adds a step:

```
feat(doc-generator): add type-stub extraction step (v0.2.0)

- Add Step 3.5 to extract type stubs before rendering
- plugin-eval: Δscore +0.03, Δanti_patterns 0
- Author bumped metadata.version to 0.1.1; raised to 0.2.0 because a new
  workflow step is a minor change
```

New plugin publish — a new `plugins[]` entry for `basedpyright-lsp` (no prior history):

```
feat(basedpyright-lsp): introduce basedpyright-lsp at v0.1.0 (v0.1.0)

- Register basedpyright-lsp plugin in .claude-plugin/marketplace.json
- Initial publish at v0.1.0 (plugin.json + marketplace.json parity verified)
- plugin-eval: n/a (no SKILL.md in this plugin)
```

Plugin component minor — added a new slash command to an existing plugin
(`agent-harness` plugin at v0.2.0, no SKILL.md change):

```
feat(agent-harness): add /status command (v0.3.0)

- Add commands/status.md exposing /agent-harness:status to inspect agent state
- agent-harness plugin bumped to v0.3.0 (plugin.json + marketplace.json)
- plugin-eval: n/a (component change, no SKILL.md edit)
```

Plugin component patch (semantic) — fixed a wrong matcher in a plugin hook
(`agent-harness` plugin at v0.3.0):

```
fix(agent-harness): tighten PreToolUse matcher to avoid false positives (v0.3.1)

- Replace `Edit|Write` matcher with `Edit|Write|MultiEdit` in hooks/hooks.json
- agent-harness plugin bumped to v0.3.1 (plugin.json + marketplace.json)
- plugin-eval: n/a (component change, no SKILL.md edit)
```

Plugin component major — removed an LSP language entry (plugin at v1.0.0):

```
feat(basedpyright-lsp)!: drop .pyw support from extensionToLanguage (v2.0.0)

- Remove ".pyw" from .lsp.json extensionToLanguage
- basedpyright-lsp plugin bumped to v2.0.0 (plugin.json + marketplace.json)
- plugin-eval: n/a (component change, no SKILL.md edit)

BREAKING CHANGE: .pyw files are no longer routed to basedpyright-langserver
via this plugin. Users who depended on .pyw routing must add their own
extension mapping or install a separate plugin.
```

## Edge cases

- **No version artifact found for a plugin skill / component change.** If neither
  `plugin.json` nor a `marketplace.json` entry exists for the owning plugin, surface
  this as a structural problem and stop — don't fabricate a manifest.
- **`plugin.json` and `marketplace.json` versions disagree.** Treat the larger as the
  floor; bring both to the same new version and note the prior drift in the commit
  body.
- **Repo-internal skill without `metadata.version`.** Introduce it at `0.1.0`; commit
  type `feat`; subject "introduce versioning at v0.1.0".
- **Author manually edited `plugin.json`/`marketplace.json` already.** Their bump is
  the floor; use the larger of (author's version, rubric-computed version).
- **Multiple change groups in one working tree.** Handle the alphabetically first one,
  tell the user to re-run for the rest, and list the remaining group keys.
- **The diff is an empty touch.** Report "no bump needed" and stop.
- **Component change with no version artifact.** If a component file changed inside
  `plugins/<category>/<plugin>/` but the plugin has no `plugin.json` (structural bug),
  surface and stop.
- **Mixed SKILL.md + component change in the same plugin.** Treat as a single plugin
  bump — highest tier wins across both diffs. Commit scope is the **skill** name; the
  body lists both the SKILL.md change and the component change.
- **Marketplace.json diff adds an entry but the plugin directory doesn't exist on
  disk.** Bad merge or stale registration. Surface and stop — do not commit a
  marketplace entry pointing at nothing.
- **New plugin publish with mismatched `plugin.json` and `marketplace.json` versions.**
  Pick the larger as the published version, edit the smaller to match, and note the
  parity fix in the commit body.
- **`plugin-dev:skill-reviewer` reported Critical or Major findings.** Don't commit. Tell the user
  to resolve the findings first; this skill is the last step before commit, not the
  first.
- **Pre-release with no numeric component to bump (e.g. `1.0.0-rc.5`).** Bump the
  numeric part as usual (`1.0.1-rc.5`); don't increment the rc counter — that's an
  author call.
- **`plugin-eval` invocation fails (network/upstream churn).** Report the failure,
  fall back to the content-diff rubric alone for the tier decision, and note in the
  commit body that the eval signal was unavailable. Pin a known-good revision via
  `PLUGIN_EVAL_SOURCE` if upstream is flaky. (Only applies to SKILL.md targets;
  component-only changes already skip eval.)

## What this skill is NOT

- Not a code or policy reviewer. The `plugin-dev:skill-reviewer` agent does that, dispatched by its own hook.
- Not a structural validator. `make verify-structure` does that; this skill calls it
  but doesn't reimplement it.
- Not a quality scorer. `plugin-eval` does that; this skill consumes its score as a
  signal but does not reimplement scoring.
- Not a CHANGELOG generator. That's a separate, future skill that consumes the
  commits this skill produces.
- Not a release publisher. Doesn't push, doesn't tag, doesn't open PRs.
- Not an owner of the top-level `marketplace.json` `metadata.version`. That umbrella
  package version is informational only and is not driven by individual plugin or
  skill changes.
