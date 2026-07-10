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
