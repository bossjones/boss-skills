# Plan: Migrate the `planf3` skill into `agent-harness`

## Task Description

Bring the `disler/planf3` Claude Code skill into this repo as a new skill under
`plugins/boss-dev/agent-harness/skills/planf3/`. `planf3` is a small, self-contained skill
(`SKILL.md` + `workflows/` + `scripts/`) that authors implementation plans as single self-contained
**HTML** files — synced CSS visual identity, optional AI-generated diagrams (OpenAI `gpt-image-2`),
phase/task checkboxes, append-only metadata, and four lifecycle workflows (create / update /
update-references / build). This plugin already has a plain-markdown `/agent-harness:plan` command
that does a simpler version of "create a plan and save it to specs/" — it stays completely
unmodified; `planf3` ships alongside it as a richer, opt-in alternative.

## Objective

`plugins/boss-dev/agent-harness/skills/planf3/` exists with a working, portable copy of the skill,
adapted to this plugin's conventions (`${CLAUDE_SKILL_DIR}`-qualified script paths,
`disable-model-invocation: true`, a differentiated `description`, scoped `allowed-tools`). The
plugin's documentation (`docs/skills.md`, `README.md`, `docs/tutorials/README.md`) reflects the new
skill, a new tutorial walks through all four workflows plus image generation, and the plugin's
version is bumped as a component addition.

## Problem Statement

The source skill is battle-tested in `disler/planf3` but lives outside this repo's marketplace, so it
isn't installable via `/plugin install agent-harness@boss-skills` and doesn't follow this repo's
skill-authoring conventions (skill-relative script paths, explicit-invocation flags, documentation
indexes). Without migrating it, users of this plugin only have the lighter markdown `/plan` command
and no path to richer, diagram-carrying, multi-session plans.

## Solution Approach

Copy the skill directory verbatim (it has zero hardcoded absolute paths or sibling-skill
dependencies — confirmed by inspection), then apply four small, targeted adaptations rather than a
rewrite: (1) frontmatter additions/changes for description, invocation mode, and tool scoping, (2) a
path-qualification fix in the one workflow file that invokes the bundled scripts, (3) doc updates in
the three places this plugin indexes its skills, and (4) a new tutorial. This keeps the skill's
proven internals (the HTML plan template, the four workflows, the two PEP 723 image scripts)
completely untouched while making it a first-class citizen of this plugin.

## Relevant Files

Use these files to complete the task:

- `/Users/malcolm/dev/disler/planf3/.claude/skills/planf3/` — the source skill to copy (`SKILL.md`,
  `workflows/*.md`, `scripts/*.py`).
- `plugins/boss-dev/agent-harness/skills/fetch-diff/SKILL.md` and
  `plugins/boss-dev/agent-harness/skills/setup-second-brain/SKILL.md` — reference examples of this
  plugin's `${CLAUDE_SKILL_DIR}`-qualified script invocation and explicit-invocation frontmatter
  conventions to match.
- `plugins/boss-dev/agent-harness/docs/skills.md` — the plugin's skill index; add a `planf3` entry.
- `plugins/boss-dev/agent-harness/README.md` — the plugin's top-level README; add a `planf3` row and
  fix the stale skill count.
- `docs/tutorials/README.md` — repo-wide tutorial index; add a `planf3` row.
- `docs/tutorials/agent-harness/second-brain.md` — structural template for the new tutorial.
- `plugins/boss-dev/agent-harness/.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` —
  version bump for the new component.
- `.env.sample` — already has `OPENAI_API_KEY`; verify only, no edit needed.

### New Files

- `plugins/boss-dev/agent-harness/skills/planf3/SKILL.md`
- `plugins/boss-dev/agent-harness/skills/planf3/workflows/create-plan.md`
- `plugins/boss-dev/agent-harness/skills/planf3/workflows/update-plan.md`
- `plugins/boss-dev/agent-harness/skills/planf3/workflows/update-references.md`
- `plugins/boss-dev/agent-harness/skills/planf3/workflows/build-plan.md`
- `plugins/boss-dev/agent-harness/skills/planf3/workflows/image-generation.md`
- `plugins/boss-dev/agent-harness/skills/planf3/scripts/generate_gpt_image.py`
- `plugins/boss-dev/agent-harness/skills/planf3/scripts/edit_gpt_image.py`
- `docs/tutorials/agent-harness/planf3.md`

## Implementation Phases

### Phase 1: Copy and adapt the skill

Copy the skill directory as-is, then apply the frontmatter and path adaptations decided for this
migration (see Step by Step Tasks below for exact diffs).

### Phase 2: Documentation and indexing

Update the three places this plugin/repo index skills and tutorials so `planf3` is discoverable, and
bump the plugin's version as a component addition.

### Phase 3: Tutorial

Add a full worked-example tutorial covering all four workflows plus image generation, following the
`second-brain.md` structural pattern.

## Step by Step Tasks

IMPORTANT: Execute every step in order, top to bottom.

### 1. Copy the skill directory

- Run:

  ```bash
  cp -r /Users/malcolm/dev/disler/planf3/.claude/skills/planf3 \
        /Users/malcolm/dev/bossjones/boss-skills/plugins/boss-dev/agent-harness/skills/planf3
  ```

- Verify the two scripts retain their executable bit and `#!/usr/bin/env -S uv run` shebang
  (`ls -l scripts/*.py` should show `755`).
- No other files exist in the source skill (no `references/`, no config, no assets) — confirm nothing
  else needs copying.

### 2. Adapt `SKILL.md` frontmatter

In the copied `plugins/boss-dev/agent-harness/skills/planf3/SKILL.md`:

- Keep `name: planf3` and `argument-hint: "[user-prompt] [questionable]"` unchanged.
- Replace the `description` field (currently a verbatim duplicate of the existing `/agent-harness:plan`
  command's description) with:

  ```yaml
  description: >
    Writes and maintains implementation plans as self-contained HTML files with synced visual
    identity, optional AI-generated diagrams, and a full create/update/build lifecycle with phase
    checkboxes and append-only metadata — saved to specs/. Use as a richer alternative to
    /agent-harness:plan when the plan benefits from diagrams or needs to be revised and executed
    over multiple sessions.
  ```

- Add `disable-model-invocation: true` so it only runs via explicit `/agent-harness:planf3` or being
  asked for by name — matching this plugin's convention for other multi-workflow, explicit-intent
  skills (`git-worktree*`, `pr-review`, `pyrefly-typing`, `setup-*`).
- Add a scoped `allowed-tools` line: `Read, Write, Edit, Grep, Glob, Bash(uv run:*), Bash(open -a:*)`.
- Leave the `IDE: code` / `BROWSER: chrome` variables in the body as soft defaults; do not hardcode
  anything else.

### 3. Fix the one skill-relative path reference

In `workflows/image-generation.md`, change both script invocations from the bare relative form to the
`${CLAUDE_SKILL_DIR}`-qualified form this plugin uses everywhere else (see `fetch-diff/SKILL.md`,
`git-worktree/SKILL.md`, `setup-second-brain/SKILL.md`):

```text
uv run "${CLAUDE_SKILL_DIR}/scripts/generate_gpt_image.py" "<prompt>" <output.png> --size 1536x1024 --quality high
uv run "${CLAUDE_SKILL_DIR}/scripts/edit_gpt_image.py" "<instruction>" <output.png> <input.png> --size 1536x1024 --quality high
```

Confirm no other file (`SKILL.md`, the other three workflow files) references `scripts/` — grep the
copied directory for `scripts/` to be sure only `image-generation.md` needed the change.

### 4. Update `plugins/boss-dev/agent-harness/docs/skills.md`

- Add `[`planf3`](#planf3)` to the Table of Contents under a new `## Planning` family heading (none
  of the existing seven families — PR review, git-worktree, release notes, content hygiene, machine
  setup, type checking, security review, cmux — fit this skill).
- Add a row to the "At a glance" table: `| [`planf3`](#planf3) | explicit | Write/maintain HTML plans
  with diagrams and a create/update/build lifecycle | `uv`, `OPENAI_API_KEY` optional |`.
- Add a `## Planning` section with a `### planf3` subsection, following the `setup-second-brain`
  subsection's shape: **Invocation** (explicit, argument-hint `[user-prompt] [questionable]`),
  **When to use**, **What it does** (summarize the four workflows + image subworkflow), **Example**
  (`/agent-harness:planf3 "add rate limiting to the API client"`), **Source**
  (`../skills/planf3/SKILL.md`), **Tutorial**
  (`../../../../docs/tutorials/agent-harness/planf3.md`).
- In the closing "Dependencies" section, add `planf3` to the `uv` bullet's skill list, and add a note
  that `OPENAI_API_KEY` is optional and only used for `planf3`'s image-generation subworkflow.

### 5. Update `plugins/boss-dev/agent-harness/README.md`

- In "Components at a glance", correct the "Skills" row count. It currently reads `17`, which was
  already stale (19 skills exist on disk before this change); set it to `20` (19 existing + `planf3`).
- Under `## Skills`, add a new "**Planning:**" family table with one row:
  `| `planf3` | Write implementation plans as self-contained HTML files with synced styling, optional
  AI-generated diagrams, and a create/update/build lifecycle. |`.

### 6. Update `docs/tutorials/README.md`

Add a row to the "Available tutorials" table, following the existing `agent-harness` rows' format:

```text
| [agent-harness](agent-harness/README.md) | [Write and build plans with planf3](agent-harness/planf3.md) | Author an HTML plan with diagrams, then revise and build it out end to end |
```

### 7. Write the tutorial

Create `docs/tutorials/agent-harness/planf3.md` with the following content:

<!-- The full tutorial body is included verbatim below; write it exactly as-is except for
     ensuring relative links resolve from this file's real path. -->

```markdown
# Tutorial: Write and build plans with planf3

`planf3` is the HTML-first sibling of the plugin's simpler `/agent-harness:plan` command. Instead of a
markdown spec, it authors a single self-contained `.html` file in `specs/` — synced CSS visual identity,
optional AI-generated diagrams, phase/task checkboxes, and an append-only metadata + amendments trail that
survives the plan's whole lifecycle (create → question → revise → link → build). This walkthrough runs
every workflow once, end to end, against one running example: adding rate limiting to an API client.

**Time:** ~25 minutes · **Level:** intermediate · **Reference:**
[`planf3` skill](../../../plugins/boss-dev/agent-harness/skills/planf3/SKILL.md)

## Prerequisites

| You need | Check it |
|----------|----------|
| The plugin installed | `/plugin install agent-harness@boss-skills` |
| `uv` on PATH | `uv --version` |
| (Optional, for embedded images) `OPENAI_API_KEY` | `echo $OPENAI_API_KEY` (or an `.env` file in `cwd`) |
| A repo with (or room for) a `specs/` directory | plan files land at `specs/<name>.html` |

Images are entirely optional: without a key, the plan is still a complete, valid, self-contained HTML
file — the image slots just stay as HTML comments instead of `<img>` tags.

## Step 1 — Create a plan

```text
/agent-harness:planf3 "add rate limiting to the API client"
```

`QUESTIONABLE` is omitted, so it defaults to `false`. The skill reads `SKILL.md`, matches this against the
workflow table — new work, no existing plan referenced — and routes to **Create Plan**, reading
`workflows/create-plan.md`.

That workflow: analyzes the prompt, explores the codebase (and `AI_DOCS/`, `APP_DOCS/` if present) for
prior patterns, designs the approach, then fills every `{{PLACEHOLDER}}` in the `## Plan Template`,
generates a descriptive filename, and saves it — here, `specs/add-api-client-rate-limiting.html`. It
finishes by opening the file in Chrome (`open -a "Google Chrome" specs/add-api-client-rate-limiting.html`).

Opened in a browser, the resulting file has:

- **Header + metadata** — collapsible `<details class="meta">` with `created` (a single ISO timestamp),
  and empty-but-present `modified` / `commits` / `agent name` / `session id` / `back refs` / `forward
  refs` lists, ready to be appended to later.
- **Hero image** figure at the top (filled in Step 6 below).
- **Purpose / Problem / Solution** sections — e.g. Problem: "repeated bursts from a single client can
  exhaust the upstream API's quota"; Solution: "a token-bucket rate limiter wrapping every outbound
  request" — each with its own optional figure.
- **Relevant Files** — Existing: `src/api_client.py`, `src/config.py`; New: `src/rate_limiter.py`,
  `tests/test_rate_limiter.py`.
- **Implementation Phases**, each starting at `[]`:
  - Phase 1: Token Bucket Rate Limiter
  - Phase 2: Wire Rate Limiter into `APIClient`
  - Phase 3: Configuration, Backoff & Retry Headers

  Every phase ends with a **Testing Strategy** sub-task and validation commands like
  `uv run pytest tests/test_rate_limiter.py -v`, plus the standing 🔁 loop notice: don't leave the phase
  until every box is checked.
- **Validation Commands** (global) — e.g. `make test`, `make lint`.
- **Notes** — free-form: why token bucket over sliding window, the new `uv add` dependency if any,
  rejected alternatives.
- **Amendments** — present but empty; nothing has happened to the plan yet.

## Step 2 — Surface open questions instead of guessing

```text
/agent-harness:planf3 "add rate limiting to the API client" true
```

Same routing (Create Plan), but with `QUESTIONABLE=true` the Instructions tell the agent to actively
surface assumptions in the **Questionables** section rather than silently deciding. The section is
*only* included when this flag is true. Expect entries like:

```html
<details>
  <summary>Should the limit be per-API-key or per-source-IP?</summary>
  <p class="qa-answer">Assumed per-API-key since the client already authenticates with a key; revisit if
  anonymous traffic needs coverage.</p>
</details>
<details>
  <summary>Fixed backoff or exponential with jitter?</summary>
  <p class="qa-answer">Assumed exponential with jitter to avoid thundering-herd retries; flagged for
  reviewer sign-off before Phase 3.</p>
</details>
```

Each `<details>` toggles open/closed in the browser — a reviewer skims summaries and expands only the
ones they care about.

## Step 3 — Revise a section (Update Plan)

Suppose a reviewer wants Phase 2 to use a sliding window instead of a token bucket:

```text
/agent-harness:planf3 "In specs/add-api-client-rate-limiting.html, change Phase 2 to use a sliding
window algorithm instead of token bucket"
```

This asks to change content of an *existing* plan, so it routes to **Update Plan**
(`workflows/update-plan.md`): locate the file, scope the edit to just Phase 2, apply it in place
(structure and `{{...}}` conventions preserved elsewhere), then:

1. Append (never overwrite) the current ISO timestamp to `modified`, and the agent name / session id to
   their lists.
2. Append a new, newest-at-the-bottom entry to **Amendments**:

```html
<details>
  <summary>2026-07-09T14:05:00Z — Switched Phase 2 to sliding-window algorithm</summary>
  <p>Reviewer requested sliding window over token bucket for tighter burst control; Phase 2 tasks and
  its Testing Strategy were rewritten accordingly.</p>
</details>
```

## Step 4 — Record a commit and agent name (Update References)

After manually implementing and committing Phase 1's token-bucket primitive, tell `planf3` to fold that
fact into the plan's metadata:

```text
/agent-harness:planf3 "In specs/add-api-client-rate-limiting.html, record commit a1b2c3d for the
Phase 1 rate limiter work, agent claude-sonnet-5"
```

The prompt is refreshing plan metadata (`commits`, `agent`), so it routes to **Update References**
(`workflows/update-references.md`). Here there's no other plan to link, so the workflow's back/forward
reference steps are a no-op; it still appends `a1b2c3d` to `{{COMMIT_SHA_LIST}}`, `claude-sonnet-5` to
`{{AGENT_NAME_LIST}}`, the current timestamp to `{{MODIFIED_ISO_LIST}}`, and records an Amendments entry
noting what was appended.

If instead the prompt names a related plan — `"...also link this to specs/api-client-refactor.html as a
back reference"` — the same workflow adds `{{BACK_REFERENCES}}` here **and** the reciprocal
`{{FORWARD_REFERENCES}}` entry on `api-client-refactor.html`, touching and stamping `modified` on both
files.

## Step 5 — Implement the plan (Build Plan)

```text
/agent-harness:planf3 "implement specs/add-api-client-rate-limiting.html"
```

This asks to carry out the plan's work, so it routes to **Build Plan** (`workflows/build-plan.md`). It
first absorbs context — the whole plan, its images, metadata, and any back references one level deep —
then executes phases top to bottom:

- Starting Phase 1, the phase heading and its current task flip from `[]` to `[wip]`:
  `<h3><code class="status">[wip]</code> Phase 1: Token Bucket Rate Limiter</h3>`.
- Tasks are implemented, then the phase's Testing Strategy command runs:
  `uv run pytest tests/test_rate_limiter.py -v`. On failure it loops — fix, re-run — until it passes,
  then the task and phase both flip to `[x]`.
- Phase 2 starts only after Phase 1's tasks and tests all resolve. Say its integration test genuinely
  can't be made to pass (e.g. a sandboxed dependency isn't reachable in this environment):

  ```html
  <li><code class="status">[f]</code> <code>uv run pytest tests/test_api_client_integration.py -v</code>
      — proves the limiter throttles real outbound calls</li>
  ```

  `[f]` means failed-and-moved-on, not skipped — the workflow still advances to Phase 3 rather than
  blocking forever, but flags it for attention in the final report.
- After all phases, **Final Validation** runs the global Validation Commands (`make test`, `make lint`)
  and confirms every box passes.
- **Update Metadata**: append the build's ISO timestamp to `modified`, the agent name / session id, and
  the real commit SHA(s) made during the build to their lists.
- **Report**: what was built per phase, final status of every task, and a callout that Phase 2's
  integration test is still marked `[f]` and needs human follow-up.

## Step 6 — Image generation, with and without `OPENAI_API_KEY`

Image Generation is a **subworkflow** (`workflows/image-generation.md`) — never selected directly from a
`USER_PROMPT`; Create Plan calls its *Create* mode, Update Plan/Build Plan can call its *Update* mode if a
diagram needs refreshing. Two PEP 723 scripts do the actual work:

- `scripts/generate_gpt_image.py "<prompt>" <output.png> --size 1536x1024 --quality high` — new image.
- `scripts/edit_gpt_image.py "<instruction>" <output.png> <input.png> --size 1536x1024 --quality high` —
  edits an existing PNG in place (backing up the original first).

**With `OPENAI_API_KEY` set:** Create Plan's step 5 greps the plan for every `{{...IMAGE}}` slot (hero,
problem, solution, each phase), writes a short prompt obeying the shared rules (wide, high quality,
professional/minimal, under 10 words of on-image text, matching the plan's CSS identity), and generates
each into `IMAGES_OUTPUT_DIR` — here `specs/add-api-client-rate-limiting/hero.png`,
`.../phase-1.png`, etc. — then swaps the placeholder comment for
`<img src="add-api-client-rate-limiting/hero.png" alt="...">` inside the existing `<figure>`.

**Without it:** both scripts call `OpenAI()` and raise immediately — there's no key to authenticate with,
and no silent fallback. The image step fails, so the plan is saved with its `<!-- {{HERO_IMAGE: ...}} -->`
comments left untouched. The HTML is still fully valid and usable (all text sections, checkboxes, and
metadata work identically); it just renders without pictures. Adding a `.env` file with
`OPENAI_API_KEY=sk-...` in the repo root works too — both scripts call `load_dotenv(Path.cwd() / ".env")`.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Image slots stay as HTML comments, no `<img>` tags | No `OPENAI_API_KEY` (env or `.env`) | Export the key or add a `.env`, then re-run Create (or an Update-Plan prompt asking to fill images) |
| "Which plan?" / wrong file picked | `USER_PROMPT` didn't name a path and multiple `specs/*.html` files exist | Be explicit: include the relative path, e.g. `specs/add-api-client-rate-limiting.html` |
| A task stays `[f]` after Build Plan | Its Testing Strategy or global validation command genuinely couldn't be made to pass in this run | Fix the root cause (env, missing dep, flaky service) then re-invoke Build Plan on the same file — it re-reads current statuses, so already-`[x]` phases aren't redone |
| Metadata list looks shorter than expected / entries missing | Manual edits accidentally overwrote a list instead of appending | Every metadata field except `created` must only ever be appended to — restore prior entries and append going forward |
| Plan doesn't open in the browser automatically | `open -a "Google Chrome"` fails (Chrome not installed) | Open the `.html` file manually, or point `BROWSER`/`IDE` at whatever you have installed |

## Where to go next

- Compare with the lighter `/agent-harness:plan` command — same "save to `specs/`" idea, plain markdown,
  no images/lifecycle, for when a full HTML plan is overkill for a quick spec.
- Chain workflows on a real feature: Create → (optionally) Update Plan as scope shifts → Update References
  once you land related commits → Build Plan to execute and watch the checkboxes move.
- Read `workflows/build-plan.md` directly if you want the exact phase-by-phase loop the agent follows —
  it's short and worth knowing before you rely on `[f]` markers in a long-running build.
```

### 8. Bump the plugin version

- Run (or manually apply) the `version-bump-reviewer` skill's rubric for this "plugin component
  change" (a new skill added under `plugins/boss-dev/agent-harness/skills/`): bump the `version`
  field in both `plugins/boss-dev/agent-harness/.claude-plugin/plugin.json` and the matching
  `agent-harness` entry in `.claude-plugin/marketplace.json` together, one minor version (new
  feature, no breaking change).
- Do not touch `docs/plugins/agent-harness.md` (it explicitly defers to `docs/skills.md` for the
  current skill list), `.env.sample` (`OPENAI_API_KEY` already present), or
  `plugins/boss-dev/agent-harness/commands/plan.md` (kept intentionally unmodified per explicit
  decision to preserve the existing, working `/agent-harness:plan` command).

## Testing Strategy

This is a documentation/skill-authoring migration with no application test suite of its own.
Validation is manual: confirm the copied skill's frontmatter parses, confirm the one path fix landed,
confirm the doc/tutorial edits render correctly and link targets resolve, and exercise the skill's
four workflows plus image generation against a real throwaway prompt to confirm behavior (see
Validation Commands).

## Acceptance Criteria

- `plugins/boss-dev/agent-harness/skills/planf3/` exists with `SKILL.md`, all five `workflows/*.md`
  files, and both `scripts/*.py` files (executable, PEP 723 headers intact).
- `SKILL.md` has the differentiated `description`, `disable-model-invocation: true`, and the scoped
  `allowed-tools` line; `name` and `argument-hint` are unchanged from the source.
- `workflows/image-generation.md` invokes both scripts via `"${CLAUDE_SKILL_DIR}/scripts/...`, not a
  bare relative path.
- `docs/skills.md`, `README.md`, and `docs/tutorials/README.md` each have a new `planf3` entry;
  `docs/tutorials/agent-harness/planf3.md` exists with the tutorial content above.
- `plugin.json` and `marketplace.json` versions match each other and are bumped from their
  pre-migration value.
- `/agent-harness:plan` (`commands/plan.md`) is byte-for-byte unchanged.

## Validation Commands

Execute these commands to validate the task is complete:

- `test -f plugins/boss-dev/agent-harness/skills/planf3/SKILL.md` — confirm the skill was copied.
- `grep -c "CLAUDE_SKILL_DIR" plugins/boss-dev/agent-harness/skills/planf3/workflows/image-generation.md`
  — expect `2` (both script invocations qualified).
- `grep -n "disable-model-invocation" plugins/boss-dev/agent-harness/skills/planf3/SKILL.md` — expect
  a match.
- `uv run --no-project python -c "import yaml,sys; yaml.safe_load(open('plugins/boss-dev/agent-harness/skills/planf3/SKILL.md').read().split('---')[1])"`
  — confirms the frontmatter is still valid YAML after edits.
- `git diff --stat plugins/boss-dev/agent-harness/commands/plan.md` — expect no output (file
  untouched).
- `make markdown-lint` — confirm the new/edited markdown files pass `rumdl`.
- Manually invoke `/agent-harness:planf3 "add rate limiting to the API client"` in a scratch repo with
  a `specs/` directory and confirm an HTML file is produced with the expected sections.

## Notes

- The source skill (`disler/planf3`) has no `CLAUDE.md`, no sibling skills, and no hardcoded absolute
  paths — this made it a clean copy candidate; only the frontmatter/description/invocation-mode and
  one script-path reference needed adaptation for this plugin's conventions.
- `OPENAI_API_KEY` is already declared in the repo-root `.env.sample`; no new env var plumbing is
  needed for image generation to work once a real key is set.
- `specs/` at the repo root already exists and is used by other plans (including this one) — `planf3`
  will write `.html` files and an optional `<plan-name>/*.png` images directory there; no gitignore
  changes are required by this migration, but be aware future plan-image directories will accumulate
  under `specs/` unless cleaned up.
- The plugin's `docs/plugins/agent-harness.md` reference page and its skill count are already stale
  independent of this change (it defers to `docs/skills.md`) — out of scope to fix here.
- Kept explicitly out of scope per decision during planning: no changes to
  `plugins/boss-dev/agent-harness/commands/plan.md` — the existing markdown `/plan` command is
  preserved as-is alongside the new `planf3` skill.
