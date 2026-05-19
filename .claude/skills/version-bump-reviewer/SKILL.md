---
name: version-bump-reviewer
description: >
  Verifies whether an uncommitted SKILL.md change in this repo needs a version bump, and at
  what semver tier. Classifies the diff as major/minor/patch (or no-bump) using a rubric,
  corroborates the decision with a plugin-eval score/anti-pattern delta, bumps the correct
  per-repo version artifact, then commits with a conventional message a CHANGELOG generator
  can parse. There are two skill classes: a plugin skill under
  plugins/<category>/<plugin>/skills/<name>/SKILL.md bumps the owning plugin's version in
  plugins/<category>/<plugin>/.claude-plugin/plugin.json AND the matching entry in
  .claude-plugin/marketplace.json; a repo-internal skill under .claude/skills/<name>/SKILL.md
  bumps a per-skill metadata.version in its own frontmatter. Use this skill whenever a
  SKILL.md under plugins/ or .claude/skills/ has been edited, written, or newly created and
  not yet committed; whenever the user says "bump the version", "cut a release", "release
  this skill", "prepare this skill for merge", or "does this need a version bump"; or
  whenever a plugin's package version may be out of sync with a recently changed skill. Run
  this AFTER skill-review so any policy or quality issues are addressed first.
allowed-tools: Bash(git diff *) Bash(git status *) Bash(git log *) Bash(git show *) Bash(git add *) Bash(git commit *) Bash(make *) Bash(uvx *) Bash(mkdir *) Bash(cp *) Read Edit
---

# Version Bump Reviewer

Decides whether a SKILL.md change needs a semver bump and at what tier, then propagates the
new version through every file that has to stay in sync for this repo, and writes a
conventional-commit message a future CHANGELOG generator can grep. This skill is the
version-aware sibling to `skill-review`: `skill-review` flags policy and quality issues;
this skill reasons about versioning and commits the result.

The primary question this skill answers is **"does this change need a version bump, and if
so, what tier?"** — "no bump needed" is a first-class, expected outcome.

## When to invoke

- **Auto-triggered** by `.claude/hooks/version-bump-reviewer.py` whenever `Edit`, `Write`,
  or `MultiEdit` touches a `SKILL.md` under `plugins/<category>/<plugin>/skills/<name>/` or
  under `.claude/skills/<name>/`. The hook runs alongside `skill-edit-review.py`; both
  fire independently. Address `skill-review` findings first, then run this skill.
- **Model-invoked** when the user asks to bump a version, cut a release, prepare a skill
  for merge, verify whether a change needs a bump, or sync a plugin's package version.
- Skip when no `SKILL.md` is in the working tree (nothing drives a version bump).
- Skip when the diff is an empty touch with no real content change.

## Skill classes and version artifacts

The changed `SKILL.md` path determines the skill class and which version artifact(s) get
bumped.

| Path shape | Class | Version artifact(s) |
|------------|-------|---------------------|
| `plugins/<category>/<plugin>/skills/<name>/SKILL.md` | **Plugin skill** | `version` in `plugins/<category>/<plugin>/.claude-plugin/plugin.json` **and** the matching `plugins[]` entry in `.claude-plugin/marketplace.json`, located by `source == "./plugins/<category>/<plugin>"`. Bumped in lockstep, same tier. |
| `.claude/skills/<name>/SKILL.md` | **Repo-internal skill** | `metadata.version` in this SKILL.md's own frontmatter. Introduce the field at `0.1.0` if it does not exist (e.g. `doc-generator` has no version field today). No marketplace or plugin.json artifact applies. |

The repo's top-level `.claude-plugin/marketplace.json` `metadata.version` is **out of
scope** — it is the umbrella package version and is not driven by individual skill changes.
Do not touch it.

## Inputs the skill gathers

1. The list of changed `SKILL.md` files in the working tree, via
   `git diff --name-only HEAD -- 'plugins/**/SKILL.md' '.claude/skills/**/SKILL.md'`,
   plus `git status --short` to catch untracked new files.
2. The full uncommitted diff for the chosen SKILL.md, via `git diff HEAD -- <path>`
   (or `git diff --no-index /dev/null <path>` for an untracked new file).
3. The skill class and, for a plugin skill, the owning plugin directory, its
   `plugin.json` `version`, and the matching `marketplace.json` `plugins[].version`.
4. For a repo-internal skill, the current `metadata.version` in the SKILL.md
   frontmatter (or the fact that it is absent).
5. A `plugin-eval` score for the SKILL.md before and after the change (see Phase 4).

## Workflow

### Phase 1 — Pick exactly one skill

Run `git diff --name-only HEAD -- 'plugins/**/SKILL.md' '.claude/skills/**/SKILL.md'`. If
the result is empty, also check `git status --short` for untracked new `SKILL.md` files.

- **Zero changed SKILL.md files** → tell the user there is nothing to review and stop.
- **One changed SKILL.md** → that is the target.
- **More than one** → pick the first one alphabetically by path, do the full workflow for
  it, and at the end tell the user to re-run the skill for each remaining SKILL.md (list
  them). Each skill gets its own independent commit so the future CHANGELOG generator can
  attribute changes correctly.

### Phase 2 — Resolve skill class and version artifacts

Classify the target path:

- Matches `plugins/<category>/<plugin>/skills/<name>/SKILL.md` → **plugin skill**.
  - Owning plugin manifest: `plugins/<category>/<plugin>/.claude-plugin/plugin.json`.
  - Marketplace entry: the element of `.claude-plugin/marketplace.json` `plugins[]` whose
    `source` is `./plugins/<category>/<plugin>`.
  - **Edge — unregistered plugin:** if the plugin has a `plugin.json` but no matching
    `marketplace.json` entry (true for `proxmox-infra` at time of writing), bump
    `plugin.json` only and surface a finding telling the user the plugin is not yet
    registered in `marketplace.json`.
- Matches `.claude/skills/<name>/SKILL.md` → **repo-internal skill**. The only artifact is
  `metadata.version` in this SKILL.md's frontmatter.

### Phase 3 — Read current versions and detect author intent

- **Plugin skill:** read `plugin.json` `version` (`CURRENT_PLUGIN_VERSION`) and the
  matching `marketplace.json` `plugins[].version` (`CURRENT_MARKETPLACE_VERSION`). They
  should match; if they don't, that's a finding to surface — proceed and bring both to the
  same new version.
- **Repo-internal skill:** read `metadata.version` from the SKILL.md frontmatter
  (`CURRENT_INTERNAL_VERSION`). If the field is absent, this is a field-introduction
  case: treat the baseline as unset and default to `0.1.0` (see Phase 6).
- **Author intent / baseline.** From `git diff HEAD -- <path>` (and, for a plugin skill,
  `git diff HEAD -- <plugin.json> <marketplace.json>`), find any removed line (prefixed
  `-`) that set a `version` / `metadata.version`. If found, parse it as
  `ORIGINAL_VERSION` (the pre-edit baseline). If no version line was removed, set
  `ORIGINAL_VERSION = CURRENT_*_VERSION`. This anchors the author-bump floor in Phase 6.

### Phase 4 — plugin-eval before/after signal

This is a corroborating signal that feeds the tier decision. It can **escalate** the
rubric tier but must never silently lower it. The content-diff rubric (Phase 5) remains
the primary classifier.

`plugin-eval` is pulled on demand via `uvx` — nothing is vendored. Use the same invocation
contract as `scripts/eval-skills.py`:

```
$ SRC="${PLUGIN_EVAL_SOURCE:-git+https://github.com/wshobson/agents.git#subdirectory=plugins/plugin-eval}"
$ uvx --from "$SRC" plugin-eval score <dir> --depth quick --output json
```

`--depth quick` is the static layer only: deterministic, free, no API key — safe as a
gate. `standard`/`certify` (LLM judge / Monte Carlo) are optional manual deep-dives; never
require them for the bump decision.

- **BEFORE** (skip if the SKILL.md is untracked / brand-new): create a temp dir, copy the
  skill directory into it, overwrite the copy's `SKILL.md` with the committed version, and
  score it:

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

Apply this rubric to the SKILL.md diff. Highest tier wins — if the diff touches Major and
Minor categories, the result is Major. Then fold in the Phase 4 signal: the eval delta may
push the result to a higher tier, never a lower one.

| Tier | Triggers |
|------|----------|
| **Major** | A workflow step was removed; a tool was removed from `allowed-tools` or from the body's tool reference; the skill was renamed (frontmatter `name` changed); the skill's directory was relocated; required inputs/outputs changed in a way that breaks existing callers; a user-facing trigger was narrowed (e.g. `description` lost a context that previously activated the skill). |
| **Minor** | A new workflow step was added; a tool was added; the description was broadened to cover new triggers; new optional functionality that doesn't break existing flows; new edge-case handling. |
| **Patch (semantic)** | A small behavioral fix that changes how a step works without changing its inputs or outputs; correcting a wrong tool argument; tightening a regex or condition; any change where `Δanti_patterns > 0`. |
| **Patch (cosmetic)** | Typos, prose clarifications, reordering paragraphs without semantic change, link fixes, formatting-only changes. |

When the rubric is genuinely ambiguous, prefer the higher tier. A wrong Major bump is
recoverable in the next release; a wrong Patch bump that should have been Major silently
breaks downstream installs.

### Phase 6 — Decide bump-or-not and compute the new version

**No-bump outcome.** A bump is **not** needed only when the change is a genuine no-op:
an empty touch, a whitespace-only change, or a reordering that produces zero rendered
difference — i.e. `git diff HEAD -- <path>` shows no semantic or visible content change.
In that case report "no version bump is needed", explain why, and stop without editing
or committing. This is the core "verify whether a bump is needed" answer and is a
successful outcome.

A cosmetic **content** change (typo, prose clarification, link fix, formatting that
changes rendered output) is **not** a no-op — it is a Patch (cosmetic) change and **does**
bump (see Phase 5 and the conventional-commit table). Every committed SKILL.md content
change is attributable in the CHANGELOG; "no bump" never applies just because a change is
small.

Otherwise compute the new version. Parse `ORIGINAL_VERSION` into
`MAJOR.MINOR.PATCH[-PRERELEASE]` and apply the rubric (or escalated) tier:

- Major → `(MAJOR+1).0.0[-PRERELEASE]`
- Minor → `MAJOR.(MINOR+1).0[-PRERELEASE]`
- Patch → `MAJOR.MINOR.(PATCH+1)[-PRERELEASE]`

The pre-release suffix (e.g. `-alpha`) is preserved verbatim. A pre-release skill stays
pre-release until an author explicitly drops the suffix; this skill never makes that call.

**Author-bump floor.** If the diff changed a version (`ORIGINAL_VERSION ≠ CURRENT_*`),
take the larger of (`CURRENT_*`, the rubric-computed version). Both are anchored to the
same pre-edit baseline, so the comparison is meaningful: the author's intent is a floor,
never a ceiling. If the rubric demands a higher tier, raise to it and explain why in the
commit body. If no version change was in the diff, use the rubric-computed version
directly.

**Field-introduction (repo-internal, no `metadata.version`).** If the SKILL.md had no
`metadata.version`, introduce it at `0.1.0` (or `0.1.0-alpha` if the author clearly
intends pre-release). The conventional commit type is `feat` (initial versioning).

**Brand-new SKILL.md.** If the file is untracked, do not bump — accept whatever version
the author wrote (default `0.1.0`); the conventional commit type is `feat`.

### Phase 7 — Apply the version edit(s)

- **Plugin skill:** use `Edit` to change `version` in
  `plugins/<category>/<plugin>/.claude-plugin/plugin.json`, and the matching
  `plugins[].version` in `.claude-plugin/marketplace.json`, both to the new version. Match
  enough surrounding context (the plugin's `name`/`source`) to be unambiguous. If the
  plugin is unregistered in `marketplace.json`, edit only `plugin.json` and keep the
  unregistered-plugin finding for the report.
- **Repo-internal skill:** use `Edit` to change (or introduce) `metadata.version` in the
  SKILL.md frontmatter. If introducing, add a `metadata:` block with `version:` under the
  frontmatter, matching the existing YAML style.

### Phase 8 — Validate

- If `plugin.json` and/or `marketplace.json` were edited (plugin skill), run:

  ```
  $ make verify-structure
  ```

  This validates the marketplace structure and plugin manifests before the commit lands.

- The Phase 4 AFTER score already exercised `plugin-eval`. Require that
  `Δanti_patterns <= 0` relative to BEFORE (no new anti-patterns introduced by the
  version edits). For a repo-internal skill with no manifests touched,
  `make verify-structure` is not required.

If validation fails, **abort before committing** — leave the file edits on disk, surface
the tool output to the user, and tell them to fix the underlying issue and re-run. Don't
roll back the version edits; the user may want to see them.

### Phase 9 — Stage and commit

Stage exactly the files this skill touched:

- Plugin skill: `git add <path-to-SKILL.md> <plugin.json> .claude-plugin/marketplace.json`
  (omit `marketplace.json` if the plugin is unregistered).
- Repo-internal skill: `git add <path-to-SKILL.md>`.

Then commit using the format below. Pass the message via heredoc so multi-line bodies
work:

```
$ git commit -m "$(cat <<'EOF'
<type>(<skill-name>): <subject> (v<NEW_VERSION>)

- <bullet 1: what changed in the SKILL.md>
- <bullet 2: plugin/marketplace version bumped to <NEW_VERSION> (plugin skill only)>
- <bullet 3: plugin-eval delta — Δscore / Δanti_patterns>
- <bullet 4: only if author already bumped — note we raised it to match the rubric>

[BREAKING CHANGE: <description>]   # only present when type is feat!
EOF
)"
```

Confirm the commit landed with `git status` and `git log -1 --oneline`. Don't push.

## Conventional commit format

The skill produces commits in this exact shape so a future CHANGELOG generator can
`git log --grep '(v[0-9]'` and parse them deterministically.

| Bump tier        | Commit type             | Notes                          |
|------------------|-------------------------|--------------------------------|
| Major            | `feat(<skill-name>)!:`  | Add `BREAKING CHANGE:` footer  |
| Minor            | `feat(<skill-name>):`   |                                |
| Patch (semantic) | `fix(<skill-name>):`    |                                |
| Patch (cosmetic) | `chore(<skill-name>):`  | Typos, prose, link fixes       |
| New skill / first version | `feat(<skill-name>):` | "introduce <skill> at v<X.Y.Z>" |

`<skill-name>` is the skill directory name (e.g. `twitter-to-reel`, `doc-generator`), not
the plugin name and not the path. The subject line **must** end with `(v<NEW_VERSION>)` —
that trailing tag is the grep anchor for the CHANGELOG generator. For a plugin skill the
anchor is the new plugin version; for a repo-internal skill it is the new
`metadata.version`.

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

## Edge cases

- **No version artifact found for a plugin skill.** If neither `plugin.json` nor a
  `marketplace.json` entry exists for the owning plugin, surface this as a structural
  problem and stop — don't fabricate a manifest.
- **`plugin.json` and `marketplace.json` versions disagree.** Treat the larger as the
  floor; bring both to the same new version and note the prior drift in the commit body.
- **Repo-internal skill without `metadata.version`.** Introduce it at `0.1.0`; commit
  type `feat`; subject "introduce versioning at v0.1.0".
- **Author manually edited `plugin.json`/`marketplace.json` already.** Their bump is the
  floor; use the larger of (author's version, rubric-computed version).
- **Multiple SKILL.md changes in one working tree.** Handle the alphabetically first one,
  tell the user to re-run for the rest, and list the remaining paths.
- **The diff is an empty touch.** Report "no bump needed" and stop.
- **`skill-review` reported critical or high findings.** Don't commit. Tell the user to
  resolve the findings first; this skill is the last step before commit, not the first.
- **Pre-release with no numeric component to bump (e.g. `1.0.0-rc.5`).** Bump the numeric
  part as usual (`1.0.1-rc.5`); don't increment the rc counter — that's an author call.
- **`plugin-eval` invocation fails (network/upstream churn).** Report the failure, fall
  back to the content-diff rubric alone for the tier decision, and note in the commit
  body that the eval signal was unavailable. Pin a known-good revision via
  `PLUGIN_EVAL_SOURCE` if upstream is flaky.

## What this skill is NOT

- Not a code or policy reviewer. `skill-review` does that and runs in its own hook.
- Not a structural validator. `make verify-structure` does that; this skill calls it but
  doesn't reimplement it.
- Not a quality scorer. `plugin-eval` does that; this skill consumes its score as a
  signal but does not reimplement scoring.
- Not a CHANGELOG generator. That's a separate, future skill that consumes the commits
  this skill produces.
- Not a release publisher. Doesn't push, doesn't tag, doesn't open PRs.
- Not an owner of the top-level `marketplace.json` `metadata.version`. That umbrella
  package version is managed separately and is not driven by individual skill changes.
