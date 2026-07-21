# Plan: Vendor bowser 4-layer browser automation into agent-harness (cmux port)

> Self-contained spec. Authored to be executed by a fresh agent with zero prior conversation context.

## Task Description

Vendor IndyDevDan's **bowser** repo — a 4-layer agentic browser-automation stack — into the `agent-harness` plugin (`plugins/boss-dev/agent-harness/`), porting the `claude --chrome` (Chrome MCP) layer to **cmux browser automation** so the stack works without the `--chrome` flag and supports parallel instances.

Upstream source (already staged in-repo, no external clone needed):

- **Snapshot:** [ai_docs/bowser-upstream/](../ai_docs/bowser-upstream/) — pinned to `https://github.com/disler/bowser` commit `26541acddc0626e97e8f4398e47b288e97f97ebd` (2026-02-22), author IndyDevDan (disler). Upstream `.claude/` is staged as `dot-claude/` and upstream `README.md` as `UPSTREAM-README.md` (see the snapshot's `README.md` for provenance).
- **Design docs:** `ai_docs/my-4-layer-claude-code-playwright-cli-skill-agentic-browser-automation-{summary.md,transcript.txt}` — the video that explains the architecture (https://www.youtube.com/watch?v=efctPj6bjCY).
- **cmux command surface:** https://cmux.com/docs/browser-automation, plus the repo's existing `plugins/boss-dev/agent-harness/skills/boss-cmux/` references and the globally installed `cmux-browser` skill (`~/.claude/skills/cmux-browser/SKILL.md`, a symlink → `~/.agents/skills/cmux-browser/`; presence verified in Step 0) for battle-tested cmux browser conventions (surface targeting, snapshot/ref loop, `js_error` fallbacks).

The 4 layers (upstream `UPSTREAM-README.md`):

| Layer | Name | Role | Upstream location |
|---|---|---|---|
| 4 | Just | Reusability — one command to run everything | `justfile` |
| 3 | Command | Orchestration — discover stories, fan out agents, collect results | `dot-claude/commands/` |
| 2 | Subagent | Scale — parallel execution, isolated sessions, structured reporting | `dot-claude/agents/` |
| 1 | Skill | Capability — drive the browser via CLI or Chrome MCP | `dot-claude/skills/` |

### Confirmed scope decisions

1. **cmux replaces `claude-bowser`** — do NOT vendor the `--chrome` skill/agent; port them. The originals stay readable in the snapshot.
2. **Include the `just` skill and layer-4 recipes**, adapted for cmux where the upstream recipe used `--chrome`.
3. **Include the example workflows and sample user stories**, but **replace `amazon-add-to-cart` with a safe demo** against `https://www.saucedemo.com` (Sauce Labs' fake e-commerce sandbox: real login form, cart, checkout, zero money) — keep upstream's stop-before-final-submit safety pattern.
4. **Skip** upstream `build.md`, `prime.md`, `list-tools.md` commands — agent-harness already ships `build`/`prime` equivalents; `list-tools` is a one-off generator.

## Objective

When complete, `agent-harness` provides the full bowser stack, cmux-native:

- Skills `playwright-bowser`, `cmux-bowser`, `just` under `plugins/boss-dev/agent-harness/skills/`
- Agents `bowser-qa-agent`, `playwright-bowser-agent`, `cmux-bowser-agent` under `plugins/boss-dev/agent-harness/agents/`
- Commands `ui-review` and `bowser/{hop-automate,demo-shop-add-to-cart,blog-summarizer}` under `plugins/boss-dev/agent-harness/commands/`
- Every vendored skill carries `references/attribution.md` provenance; agent-harness bumps `0.28.0 → 0.29.0` in both `plugin.json` and `marketplace.json`; `make verify-structure`, `make markdown-lint`, and `make lint` pass.

## Problem Statement

bowser's Chrome path depends on `claude --chrome` and Chrome MCP tools (`mcp__claude_in_chrome__*`), which upstream itself documents as: single-instance only ("All Chrome MCP connections share a single Chrome extension controller. Only one bowser task at a time"), unavailable in programmatic `-p` mode, token-heavy (verbose MCP schemas), not CI-friendly, and sharing the user's real browser profile. The playwright path is solid but the repo ships nothing browser-automation-shaped today, and boss-skills' agent surface of choice is cmux.

### Does cmux fix the `claude --chrome` problems?

| `--chrome` limitation (upstream README/video) | cmux browser | Verdict |
|---|---|---|
| No parallel instances (single extension controller; the video's Amazon run held the browser 14+ min) | One `surface:N` per agent — `cmux browser open` returns an isolated surface; N sub-agents drive N surfaces concurrently | ✅ Resolved |
| Requires `--chrome` at startup; "Not available in programmatic (`-p`) mode" | `cmux` CLI callable from any session, including headless `-p` runs | ✅ Resolved |
| Lower token efficiency (verbose MCP tool schemas) | Plain CLI verbs (`snapshot --interactive`, `click`, `fill`, `wait`) — same CLI-over-MCP philosophy as `playwright-bowser` | ✅ Improved |
| Shares your real browser/profile | Isolated webview surfaces; auth via `state save/load` + `cookies`/`storage` commands (log in once, persist state) | ✅ Resolved (different auth mechanism) |
| Observable-only / no headless mode | cmux surfaces are also visible (WKWebView GUI); `playwright-bowser` remains the headless path | ➖ Unchanged (by design — the two skills split this) |
| Not CI-friendly | cmux needs the macOS app running; `playwright-bowser` covers CI | ➖ Unchanged |

cmux gaps the ported skill MUST document: WKWebView returns `not_supported` for viewport emulation, offline emulation, network route interception/mocking, trace/screencast recording, and raw input injection; complex pages can throw `js_error` on `snapshot --interactive`/`eval` (fall back to `get url` → `get text body` → `get html body`); no equivalents for Chrome MCP's `gif_creator`/`shortcuts_*`.

## Solution Approach

Copy-and-normalize per the repo's established vendoring pattern (exemplar: `plugins/boss-dev/agent-harness/skills/github-pr-review/` and `specs/vendored-plugin-eval.md`, `specs/port-skills-to-agent-harness.md`):

- Copy from `ai_docs/bowser-upstream/dot-claude/` into the plugin, normalizing each file (frontmatter `name` == directory name; description = what-it-does + "Use when…"; scoped `Bash(...)` `allowed-tools`; strip upstream-repo path assumptions).
- Port, don't copy, the Chrome pieces: `claude-bowser` skill → `cmux-bowser` skill, `claude-bowser-agent` → `cmux-bowser-agent`, `amazon-add-to-cart` → `demo-shop-add-to-cart`. The cmux command vocabulary comes from the `cmux-browser` skill and https://cmux.com/docs/browser-automation.
- Record provenance in each vendored skill's `references/attribution.md` (upstream URL, pinned tag/sha, author, MIT license text, "## Local modifications" list) + a one-line provenance note at the top of each vendored `SKILL.md`/agent/command body.
- Preserve upstream's layered entry points: each layer independently invocable (skill directly, agent via `@`-mention, command via slash, justfile recipe wrapping all of it).

## Pre-Implementation Verification (Step 0)

This spec references live resources (a docs website, a globally-installed skill, an installed CLI, in-repo exemplars, version numbers) that can drift between authoring and execution. **Run every check below before building anything** (all checks are read-only), and apply the per-check failure action. Baselines in parentheses reflect what was verified on disk at spec-authoring time (2026-07-21).

### A. Upstream snapshot intact (the vendoring source)

- `test -d ai_docs/bowser-upstream/dot-claude` and confirm the expected members exist:
  - `dot-claude/skills/{claude-bowser,just,playwright-bowser}/SKILL.md`
  - `dot-claude/agents/{bowser-qa-agent,claude-bowser-agent,playwright-bowser-agent}.md`
  - `dot-claude/commands/ui-review.md` and `dot-claude/commands/bowser/`
  - `justfile`, `UPSTREAM-README.md`, `TOOLS.md`, `ai_review/user_stories/*.yaml`
- Confirm the pinned commit `26541acddc0626e97e8f4398e47b288e97f97ebd` in the snapshot's `README.md` provenance note.
- **If missing → STOP.** The vendoring source is gone; do not silently re-clone upstream (the `dot-claude/` rename is load-bearing — see Notes).

### B. cmux-browser skill present (cmux verb conventions source)

- `test -f ~/.claude/skills/cmux-browser/SKILL.md` — note this is a **symlink** resolving into `~/.agents/skills/cmux-browser/` (check with `readlink -f`); it is NOT in this repo.
- Read the SKILL.md and confirm it still documents the verbs the `cmux-bowser` port relies on: `browser open`, `snapshot --interactive`, `click`/`fill`/`type`/`press`, `wait --load-state`, `screenshot --out`, `state save`/`state load`, and the `js_error` fallback chain.
- **If absent → degrade, don't stop:** fall back to `plugins/boss-dev/agent-harness/skills/boss-cmux/` references plus the cmux docs URL (check D), and note the gap in the port's `references/attribution.md`.

### C. cmux CLI + live command surface (ground truth for the installed version)

- `which cmux && cmux --version` (baseline: `0.64.17`).
- `cmux browser --help` — and `cmux identify --json` if the app is running — and confirm every verb used in the `cmux-bowser` workflow (see New Files) exists in the installed CLI. Flag any renamed/removed flags and adapt the skill text to the installed surface.
- **If the CLI is missing → STOP for the cmux port pieces** (`cmux-bowser` skill, `cmux-bowser-agent`, `demo-shop-add-to-cart`); the playwright/just vendoring (Phase 1) can still proceed.

### D. cmux browser docs website (documented conventions)

- WebFetch `https://cmux.com/docs/browser-automation` and cross-check the same verb set as B/C.
- On any conflict, **local `--help` output wins** (it reflects the installed version); record doc/CLI discrepancies in the ported SKILL.md.
- **If unreachable → non-fatal**; rely on checks B and C.

### E. In-repo exemplars and targets

- `test -f plugins/boss-dev/agent-harness/skills/github-pr-review/references/attribution.md` (attribution template)
- `test -f plugins/boss-dev/agent-harness/skills/boss-cmux/SKILL.md` (cmux CLI conventions)
- `test -f plugins/boss-dev/agent-harness/docs/skills.md && test -f plugins/boss-dev/agent-harness/docs/commands.md` (indexes to update in step 6)
- `test -f scripts/verify-structure.py`
- **If an exemplar moved → locate the replacement with Glob before proceeding.**

### F. Version baseline still true

- Read `plugins/boss-dev/agent-harness/.claude-plugin/plugin.json` and the agent-harness entry in `.claude-plugin/marketplace.json`; confirm both say `0.28.0`.
- **If drifted** (another PR landed a bump) → recompute the target as `current + minor` and substitute it everywhere this spec says `0.29.0`. Parity between the two files remains the hard invariant.

### G. Playwright CLI package name

- `npm view @playwright/cli version` (or WebSearch) to confirm the package name — upstream's README says `@playwright/cli` while linking `microsoft/playwright-cli`. Use whichever name npm actually resolves in the prerequisites doc (step 6) and `bowser.just`.

### H. Permission flag surface on the installed CLI

- `claude --version` (baseline `2.1.216`) and `claude --help | grep -A2 -- '--permission-mode'`; confirm `auto` is still among the accepted modes.
- `claude --help | grep -- '--enable-auto-mode'` — expected to return **nothing** on 2.1.216. If a future version *does* ship it as the ergonomic alias, prefer it in `bowser.just` and note the substitution in `docs/bowser.md`.
- **If `auto` is gone from `--permission-mode` → degrade:** default `perm` to `--permission-mode acceptEdits` and record why in `docs/bowser.md`. Never silently fall back to `--dangerously-skip-permissions`.

## Relevant Files

Existing files to read or modify:

- `ai_docs/bowser-upstream/dot-claude/**` — vendoring source (skills, agents, commands), `ai_docs/bowser-upstream/{justfile,UPSTREAM-README.md,TOOLS.md}`, `ai_docs/bowser-upstream/ai_review/user_stories/*.yaml`
- `plugins/boss-dev/agent-harness/skills/github-pr-review/references/attribution.md` — the attribution template to imitate
- `plugins/boss-dev/agent-harness/skills/boss-cmux/SKILL.md` + `references/` — cmux CLI conventions (surface refs, identify, topology targeting)
- `~/.claude/skills/cmux-browser/SKILL.md` — cmux browser verb reference (snapshot/ref loop, wait patterns, `js_error` recovery); a symlink → `~/.agents/skills/cmux-browser/`, verified in Step 0; do not copy wholesale, cite the doc URL
- `plugins/boss-dev/agent-harness/.claude-plugin/plugin.json` — version bump `0.28.0 → 0.29.0`
- `.claude-plugin/marketplace.json` — matching agent-harness `plugins[].version` bump (parity is a hard invariant)
- `plugins/boss-dev/agent-harness/docs/skills.md` and `docs/commands.md` — add the new entries if these indexes enumerate skills/commands
- `scripts/verify-structure.py` — read-only constraint reference (SKILL.md required per skill dir, `description` required per command, components at plugin root)

### New Files

All under `plugins/boss-dev/agent-harness/` unless noted:

**Skills**

- `skills/playwright-bowser/SKILL.md` — vendored near-as-is from `dot-claude/skills/playwright-bowser/SKILL.md` (headless/parallel/CI path; named sessions `-s=<kebab>`, `--persistent`, `PLAYWRIGHT_MCP_VIEWPORT_SIZE=1440x900`, `PLAYWRIGHT_MCP_CAPS=vision` opt-in, mandatory `close`). `allowed-tools`: scoped `Bash(playwright-cli:*)` (+ `Bash(mkdir:*)` for screenshot dirs) instead of upstream's bare `Bash`.
- `skills/playwright-bowser/references/playwright-cli.md` — upstream `docs/playwright-cli.md` relocated to the repo's `references/` convention
- `skills/playwright-bowser/references/attribution.md`
- `skills/playwright-bowser/examples/user_stories/{hackernews,example-app}.yaml` — sample stories from `ai_review/user_stories/`
- `skills/cmux-bowser/SKILL.md` — **new port** of `claude-bowser`. Pre-flight: `cmux identify --json` succeeds (else stop: "start the cmux app / install the cmux CLI") — replaces upstream's `mcp__claude_in_chrome__*` grep. Workflow: `cmux --json browser open <url>` → capture `surface:N` → `get url` to verify → `wait --load-state complete --timeout-ms 15000` → `snapshot --interactive` → act by refs (`click`/`fill`/`type`/`press` with `--snapshot-after`) → screenshot trail via `screenshot --out <path>` → close/cleanup. Sections: parallel-surface usage (one surface per task/agent), auth via `state save/load` + cookies/storage, WKWebView limits + `js_error` fallback chain (all listed in Problem Statement above). `allowed-tools`: `Bash(cmux:*)`, `Bash(mkdir:*)`.
- `skills/cmux-bowser/references/attribution.md` — notes this is a *port* (claude-bowser rewritten for cmux), not a copy
- `skills/just/SKILL.md` — vendored generic just skill
- `skills/just/examples/{bun-typescript,multi-module,node-docker,python-venv,uv-python}.just` — upstream templates
- `skills/just/examples/bowser.just` — **new**: upstream `justfile` recipes adapted — playwright recipes kept as-is; `--chrome` recipes (`test-chrome-skill`, `test-chrome-agent`, `hop`, `automate-amazon`) become cmux-skill invocations with the `--chrome` flag removed (`/cmux-bowser`, `@cmux-bowser-agent`, `/agent-harness:bowser:hop-automate <workflow> ... cmux`), `automate-amazon` → `automate-demo-shop`; keep `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` on the `hop` recipe; users copy this into their project.

  **Permission flag is a variable, not a hardcoded literal.** Upstream hardcodes `--dangerously-skip-permissions` on all 8 recipes; the vendored file defaults to auto mode and lets callers opt back in:

  ```just
  # Permission posture. Default: auto mode (classifier-gated).
  # Override per-invocation, e.g. `just perm="--dangerously-skip-permissions" test-qa`.
  perm := "--permission-mode auto"

  test-playwright-skill headed="true" prompt=default_prompt:
      claude {{perm}} --model opus "/playwright-bowser (headed: {{headed}}) {{prompt}}"
  ```

  **Every** recipe interpolates `{{perm}}`; no recipe hardcodes a permission flag. The `hop` recipe keeps its `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` export and gains `{{perm}}` like the rest.

- `skills/just/references/attribution.md`

**Agents**

- `agents/bowser-qa-agent.md` — vendored from `dot-claude/agents/bowser-qa-agent.md`: parses user stories (5 accepted formats), screenshots every step to `./screenshots/bowser-qa/<story-kebab>_<8-char-uuid>/`, PASS/FAIL per step, console-error capture on failure, mandatory session close, structured report tables. Keep `skills: [playwright-bowser]` and the `VISION` variable.
- `agents/playwright-bowser-agent.md` — vendored thin wrapper (`skills: [playwright-bowser]`)
- `agents/cmux-bowser-agent.md` — port of `claude-bowser-agent`: thin wrapper over `cmux-bowser`; description updated to **"Supports parallel instances — each instance opens its own cmux surface"** (upstream said "Cannot run in parallel"); report `result` + `surface` ref back to caller

**Commands**

Every vendored command carries `description` + `argument-hint` frontmatter, matching `plugins/boss-dev/agent-harness/commands/plan.md`:

| Command | `argument-hint` |
|---|---|
| `commands/ui-review.md` | `[headed\|headless] [story-filter] [flags]` |
| `commands/bowser/hop-automate.md` | `<workflow> <prompt> [playwright-bowser\|cmux-bowser] [headed\|headless]` |
| `commands/bowser/demo-shop-add-to-cart.md` | `<item description>` |
| `commands/bowser/blog-summarizer.md` | `<blog url>` |

- `commands/ui-review.md` — vendored orchestrator: discover `ai_review/user_stories/*.yaml` in the target project, TeamCreate/TaskCreate fan-out of one `bowser-qa-agent` per story (all Task calls in one message = parallel), per-story `SCREENSHOT_PATH`, collect `RESULT: {PASS|FAIL} | Steps: x/y` lines, TeamDelete, aggregate summary table. Keep resilience rules (skip unparseable YAML with warning; timeout/crash → FAIL with partial output; `subagent_type` exactly `bowser-qa-agent`). Requires `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` — say so in the command body.
- `commands/bowser/hop-automate.md` — vendored higher-order prompt with SKILL keyword values changed: `playwright` → `playwright-bowser` (default), **`cmux` → `cmux-bowser`** (replaces upstream's `claude` keyword). Workflow-file glob rewritten from `.claude/commands/bowser/` to the plugin's `commands/bowser/` directory (resolve via `${CLAUDE_PLUGIN_ROOT}` if available to commands, else instruct Glob over both plugin and project `commands/bowser/` paths — implementer verifies which resolves at runtime).
- `commands/bowser/demo-shop-add-to-cart.md` — **replaces amazon-add-to-cart**. Same 12-step shape against `https://www.saucedemo.com`: login (`standard_user` / `secret_sauce` — public demo creds printed on the site's login page), add `{PROMPT}`-matching item(s) to cart, proceed to checkout, fill the fake checkout form, **STOP before "Finish"**, report item + price. Vars: SKILL=`cmux-bowser`, MODE=`headed`.
- `commands/bowser/blog-summarizer.md` — vendored as-is (SKILL=`playwright-bowser`, MODE=`headless`): navigate `{PROMPT}` URL → latest post → 3-5 bullet summary → rating /10

**Docs & attribution**

- `plugins/boss-dev/agent-harness/docs/bowser.md` — short usage doc: the 4-layer map as it lands in this plugin, prerequisites (`npm install -g @playwright/cli@latest` (Node 18+), `brew install just`, cmux app + CLI), entry points per layer, link to `ai_docs/bowser-upstream/` and the video docs

## Implementation Phases

### Phase 1: Foundation

Vendor Layer 1 verbatim-ish: `playwright-bowser` skill (+ references, examples, attribution), `just` skill (+ templates, attribution). These have no cmux dependency and validate the vendoring mechanics.

### Phase 2: Core Implementation

The cmux port: `cmux-bowser` skill, then Layer 2 agents (`bowser-qa-agent`, `playwright-bowser-agent`, `cmux-bowser-agent`), then Layer 3 commands (`ui-review`, `bowser/hop-automate`, `bowser/demo-shop-add-to-cart`, `bowser/blog-summarizer`).

### Phase 3: Integration & Polish

Layer 4 (`skills/just/examples/bowser.just`), plugin docs, attribution completeness pass, version bump, validation suite, smoke tests.

## Step by Step Tasks

### 0. Run the Pre-Implementation Verification

- Execute every check in **Pre-Implementation Verification (Step 0)** above; record a short pass/fail note per check
- Apply the per-check failure actions (STOP / degrade / substitute) before touching any other step

### 1. Vendor the playwright-bowser skill

- Create `skills/playwright-bowser/` from `ai_docs/bowser-upstream/dot-claude/skills/playwright-bowser/`; move `docs/playwright-cli.md` → `references/playwright-cli.md` and fix the intra-skill link
- Normalize frontmatter (name == dir, "Use when…" description, `allowed-tools: [Bash(playwright-cli:*), Bash(mkdir:*)]`); add provenance note; beware GitHub #12781 — use `$ command` notation, never backtick-`!` patterns, in SKILL.md
- Copy `ai_review/user_stories/*.yaml` → `skills/playwright-bowser/examples/user_stories/`
- Write `references/attribution.md` modeled on `skills/github-pr-review/references/attribution.md` (repo URL, commit `26541ac…`, author, MIT text, local-modifications list)

### 2. Vendor the just skill

- Create `skills/just/` from `dot-claude/skills/just/` (SKILL.md + 5 example templates), normalize frontmatter, write attribution

### 3. Write the cmux-bowser skill (port)

- Author `skills/cmux-bowser/SKILL.md` per the New Files description: pre-flight `cmux identify --json`, open-surface workflow, snapshot/ref action loop, screenshot trail, parallel-surface section, `state save/load` auth section, WKWebView limits + `js_error` fallback chain
- Keep it structurally parallel to upstream `claude-bowser/SKILL.md` (Purpose / Pre-flight / Workflow / Limitations) so the port is reviewable side-by-side
- Write `references/attribution.md` marking it a port

### 4. Vendor/port the agents

- `agents/bowser-qa-agent.md` and `agents/playwright-bowser-agent.md`: copy, normalize descriptions, keep `skills:` frontmatter linkage and `model: opus`
- `agents/cmux-bowser-agent.md`: port from `claude-bowser-agent.md` — swap skill to `cmux-bowser`, flip the parallelism claim, report `result` + `surface`

### 5. Vendor/port the commands

- For each command below, write frontmatter with both `description` and `argument-hint` (values in the New Files table); `scripts/verify-structure.py` enforces only `description`, but the plugin's existing commands all carry both
- `commands/ui-review.md`: copy + normalize; keep team-orchestration workflow and resilience rules; document the `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` requirement
- `commands/bowser/hop-automate.md`: copy; change SKILL keyword map (`playwright`→`playwright-bowser` default, `cmux`→`cmux-bowser`); fix workflow-file resolution for plugin context (test whether `${CLAUDE_PLUGIN_ROOT}` expands in command bodies; otherwise Glob both plugin + project `commands/bowser/`)
- `commands/bowser/demo-shop-add-to-cart.md`: author the saucedemo.com workflow (12-step shape, STOP before "Finish")
- `commands/bowser/blog-summarizer.md`: copy + normalize

### 6. Layer 4 + docs

- Author `skills/just/examples/bowser.just` (adapted recipes per New Files)
- Author `plugins/boss-dev/agent-harness/docs/bowser.md`; add entries to `docs/skills.md` / `docs/commands.md` if those indexes exist
- `docs/bowser.md` gains a short "Permissions" section: the `perm` variable, its default, the `--dangerously-skip-permissions` override, and why the default differs from upstream

### 7. Version bump + changelog hygiene

- Bump `plugins/boss-dev/agent-harness/.claude-plugin/plugin.json` `0.28.0 → 0.29.0` AND the agent-harness entry in `.claude-plugin/marketplace.json` (minor: new skills/agents/commands)
- Run the repo's `version-bump-reviewer` skill to corroborate tier and commit format

### 8. Validate everything

- Run the full Validation Commands list below; fix until clean
- Invoke the `plugin-dev:skill-reviewer` agent on each new skill directory (untainted per `.claude/rules/audit-protocol.md`: pass only the path)

## Testing Strategy

- **Structural:** `make verify-structure` (skill dirs have SKILL.md with name+description; every command has `description`; nothing under `.claude-plugin/` but plugin.json; version parity)
- **Lint:** `make markdown-lint` (rumdl, token-lean ruleset), `make lint` (no Python is added, so this is a regression check)
- **Skill quality:** `plugin-dev:skill-reviewer` per skill; optionally `make eval-skill` / `/skill-evals` for report generation into `docs/evals/agent-harness/`
- **Smoke (manual, cmux app running):** `/cmux-bowser` → open `https://example.com`, snapshot, screenshot — verifies pre-flight, surface capture, verb set. Two parallel `@cmux-bowser-agent` invocations in one message — verifies the parallel-surface claim.
- **Smoke (playwright):** `@bowser-qa-agent` with the hackernews sample story (needs `npm install -g @playwright/cli@latest`) — verifies screenshot trail + report format. `/agent-harness:bowser:demo-shop-add-to-cart backpack` — verifies the saucedemo flow STOPs before Finish.
- **Edge cases the implementation must preserve:** ui-review with zero/unparseable YAML stories (warn + skip, not abort); QA agent FAIL path (console capture, SKIPPED marking, session still closed); hop-automate with no arguments (list workflows and stop); cmux not running (pre-flight message, no retry loop).

## Acceptance Criteria

- [ ] Pre-Implementation Verification (Step 0) was run; every check passed or its documented fallback was applied
- [ ] Skills `playwright-bowser`, `cmux-bowser`, `just` exist under `plugins/boss-dev/agent-harness/skills/`, each with `references/attribution.md` pinning commit `26541acddc0626e97e8f4398e47b288e97f97ebd`
- [ ] `cmux-bowser` contains zero references to `mcp__claude_in_chrome__*` or `--chrome`; documents parallel surfaces, `state save/load` auth, WKWebView limits, `js_error` fallback
- [ ] Agents `bowser-qa-agent`, `playwright-bowser-agent`, `cmux-bowser-agent` exist; `cmux-bowser-agent` advertises parallel support
- [ ] Commands `ui-review`, `bowser/hop-automate` (with `cmux` keyword), `bowser/demo-shop-add-to-cart` (saucedemo, stop-before-Finish), `bowser/blog-summarizer` exist with `description` frontmatter
- [ ] No `amazon-add-to-cart` command is shipped; no vendored `build`/`prime`/`list-tools` duplicates
- [ ] `skills/just/examples/bowser.just` exists with cmux-adapted recipes
- [ ] `skills/just/examples/bowser.just` defines `perm := "--permission-mode auto"` and every recipe interpolates `{{perm}}`; no recipe hardcodes `--dangerously-skip-permissions`
- [ ] All four vendored commands carry both `description` and `argument-hint` frontmatter
- [ ] agent-harness version is `0.29.0` in BOTH plugin.json and marketplace.json
- [ ] All Validation Commands pass

## Validation Commands

- `make verify-structure` — plugin/skill/command structural rules
- `make markdown-lint` — rumdl over all new markdown
- `make lint` — repo lint regression check
- `make link-check` — verifies links in new docs (attribution URLs, cmux docs URL)
- `rg -l "mcp__claude_in_chrome|--chrome" plugins/boss-dev/agent-harness/` — MUST return nothing
- `rg -l "amazon" plugins/boss-dev/agent-harness/commands/` — MUST return nothing
- `rg -n -- '--dangerously-skip-permissions' plugins/boss-dev/agent-harness/` — only allowed hits are comment/doc lines in `bowser.just` and `docs/bowser.md`; **no recipe body may contain it**
- `rg -L -- 'argument-hint' plugins/boss-dev/agent-harness/commands/ui-review.md plugins/boss-dev/agent-harness/commands/bowser/*.md` — MUST return nothing (i.e. every one of those files has the key)
- `python3 -c "import json; p=json.load(open('plugins/boss-dev/agent-harness/.claude-plugin/plugin.json')); m=json.load(open('.claude-plugin/marketplace.json')); e=[x for x in m['plugins'] if x['name']=='agent-harness'][0]; assert p['version']==e['version']=='0.29.0', (p['version'], e['version'])"` — version parity

## Notes

- **Prerequisites** (document, don't install): `npm install -g @playwright/cli@latest` (Node 18+; package name confirmed by Step 0 check G), `brew install just`, cmux app + CLI on PATH.
- **Permissions posture.** Upstream runs every justfile recipe with `--dangerously-skip-permissions` (see `ai_docs/bowser-upstream/justfile`). The vendored `bowser.just` does **not**: it defaults to auto mode via a `perm := "--permission-mode auto"` variable, so browser-driving recipes get classifier-gated permissions instead of a blanket bypass. Users who want upstream's behavior override per-invocation: `just perm="--dangerously-skip-permissions" test-playwright-skill`. Independently, the vendored *skills* carry least-privilege `allowed-tools` (`Bash(playwright-cli:*)`, `Bash(cmux:*)`) — upstream ships no permissions block at all.
- **Flag-name caveat (verified 2026-07-21, claude 2.1.216):** there is no `--enable-auto-mode` flag; auto mode is `--permission-mode auto` (choices: `acceptEdits`, `auto`, `bypassPermissions`, `manual`, `dontAsk`, `plan`). Step 0 check H re-verifies this against the CLI at implementation time.
- The snapshot's `dot-claude/` rename exists specifically so Claude Code does not auto-discover upstream's stale skills; never rename it back.
- `ui-review` depends on experimental agent teams (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`); if teams are unavailable, the command should degrade to plain parallel Task fan-out — note this in the command body.
- Upstream `images/four-layer-stack.gif` was intentionally not snapshotted (binary asset); link the video/README instead.
- Session-note (2026-07-12): `mcp__claude_in_chrome__*` naming in upstream uses underscores (`claude_in_chrome`); current Claude Code exposes `mcp__claude-in-chrome__*` (hyphens). Irrelevant after the port, but useful if diffing against upstream.
