# Matt Pocock Skills

**Source:** [https://github.com/mattpocock/skills](https://github.com/mattpocock/skills)

**Install:** `npx skills@latest add mattpocock/skills`

These skills are built around four core engineering principles: **alignment** (close the gap between developer intent and agent action), **concise communication** (shared vocabulary cuts token waste), **feedback loops** (static types, tests, and instrumentation keep agents on track), and **deliberate architecture** (domain language and ADRs slow entropy as projects scale). Each skill targets one or more of these principles and works across AI models while keeping the developer in control.

---

## Engineering Skills

### `/diagnose`

Structured debugging methodology for hard bugs that resist obvious fixes.

The skill drives a disciplined loop: build a fast, deterministic feedback loop first, then reproduce the bug, form a hypothesis, instrument the code, apply a fix, and write a regression test. Disproportionate time is spent on the feedback loop — without it everything else is guesswork.

**Key behaviors:**

- Offers 10 concrete strategies for constructing a feedback loop (failing test, `curl`, CLI invocation, browser script, etc.)
- Handles non-deterministic bugs through repeated sampling and statistical reasoning
- Never skips the regression-test step

---

### `/grill-me`

Relentless one-question-at-a-time interview that resolves every decision branch in a plan before work starts.

The agent walks the full design tree, surfaces all dependencies, and asks each question with a recommended answer so the user can confirm or redirect quickly. Optionally explores the codebase to answer questions itself before surfacing them.

**Key behaviors:**

- Asks only one question at a time — never a list
- Provides a recommended answer for each question
- Stops only when all branches are resolved

---

### `/grill-with-docs`

A grilling session anchored to the project's existing domain model.

Before challenging the plan, the agent reads `CONTEXT.md` and any architecture decision records (ADRs) in `docs/adr/`. It then probes the plan for glossary violations, fuzzy language, and concrete scenario gaps — updating `CONTEXT.md` inline as new decisions crystallize. ADRs are offered only when a decision is hard to reverse, surprising, and the result of a genuine trade-off.

**Key behaviors:**

- Domain-aware: grills against the project's own vocabulary
- Updates `CONTEXT.md` in place as alignment emerges
- Proposes ADRs sparingly; explains when one is warranted

---

### `/improve-codebase-architecture`

Finds opportunities to turn shallow modules into deep ones using the project's domain language.

The agent explores the codebase informed by `CONTEXT.md` and `docs/adr/`, then presents refactoring candidates in a visual HTML report with before/after Mermaid diagrams. A grilling loop follows so the user can prioritize candidates before any code changes.

**Key behaviors:**

- Uses consistent architectural vocabulary: Module, Interface, Implementation, Depth, Seam, Adapter, Leverage, Locality
- Generates a Tailwind + Mermaid HTML report — no plain text candidate lists
- Grilling loop runs before implementation begins

---

### `/prototype`

Builds a throwaway prototype to validate a design before committing to production code.

Routes between two branches: `LOGIC.md` (a terminal app that surfaces state and business logic) or `UI.md` (several UI variations toggled via a URL parameter). The prototype is explicitly marked throwaway and must run with a single command.

**Key behaviors:**

- No persistence, no polish, no production concerns
- UI branch exposes all variations under one URL via a query-param toggle
- Deleted after the design decision is made

---

### `/qa`

Interactive QA session in which the user reports bugs and the agent files durable GitHub issues.

The agent listens, clarifies ambiguity, explores the codebase in the background to assess scope, then files issues using the project's templates and domain language. The session continues until the user ends it.

**Key behaviors:**

- Issues are user-focused and use project domain vocabulary
- Scope assessment determines whether a report becomes one issue or several
- Session is open-ended; the agent doesn't close it unilaterally

---

### `/review`

Two-axis code review of a diff run as parallel sub-agents.

**Standards axis** checks whether the diff follows documented coding standards. **Spec axis** checks whether the diff matches its originating issue or PRD. Both axes run concurrently; findings are aggregated and presented together.

**Key behaviors:**

- Pins a fixed point (issue, PRD, or commit) before reviewing
- Standards and spec sub-agents run in parallel — wall-clock time is the slower of the two, not both
- Aggregated findings distinguish standards violations from spec drift

---

### `/setup-matt-pocock-skills`

One-time per-repository configuration that wires all Matt Pocock skills into the project.

Sets up the issue tracker (GitHub, GitLab, local markdown, or other), triage label vocabulary, and domain docs layout. Creates or updates the `## Agent skills` block in `CLAUDE.md`/`AGENTS.md` and writes `docs/agents/` configuration files.

**Key behaviors:**

- Idempotent — safe to re-run as preferences change
- Configures issue tracker once; other skills read the setting automatically
- Writes `docs/agents/` files that provide per-skill context

---

### `/to-issues`

Breaks a plan into independently-grabbable GitHub issues structured as vertical slices.

Each slice covers a complete path through all layers (UI → logic → persistence) so it can be worked in isolation. Issues are classified as HITL (requires human interaction) or AFK (fully autonomous). The agent quizzes the user on the slice boundaries before publishing.

**Key behaviors:**

- Tracer-bullet vertical slices — no horizontal "backend only" issues
- HITL vs AFK classification on every issue
- Published in dependency order

---

### `/to-prd`

Converts an in-progress conversation into a formal Product Requirements Document published as a GitHub issue.

The agent explores the repo for context, sketches test seams, then writes a PRD with: Problem Statement, Solution, User Stories (extensive), Implementation Decisions, Testing Decisions, Out of Scope, and Further Notes. Applies the `ready-for-agent` label automatically.

**Key behaviors:**

- Synthesizes the full conversation — the user doesn't need to summarize
- User Stories section is intentionally extensive
- Applies `ready-for-agent` so the issue is immediately pickable

---

### `/triage`

Moves issues through a two-category, five-state machine.

Categories: `bug` / `enhancement`. States: `needs-triage` → `needs-info` / `ready-for-agent` / `ready-for-human` / `wontfix`. The agent gathers context, recommends a state, reproduces bugs when possible, and grills the reporter when information is missing. Every comment starts with an AI-generated disclaimer.

**Key behaviors:**

- State machine is strict — no skipping states
- Bugs trigger a reproduction attempt before triage completes
- All agent comments include the required AI disclosure

---

### `/zoom-out`

Minimal skill that requests a broad context map when the agent is working in unfamiliar territory.

Instructs the agent to step back and return a map of all relevant modules and their callers using the project's domain glossary. Useful before any large refactor or when the current context window has become too narrowly focused.

**Key behaviors:**

- Uses the project's domain vocabulary (not generic terms like "file" or "function")
- Returns callers and dependencies, not just the target module
- `disable-model-invocation: true` — no model call on the skill itself

---

## Productivity & Communication Skills

### `/caveman`

Ultra-compressed communication mode that cuts token usage by approximately 75%.

Once activated, the agent drops articles, filler words, pleasantries, and hedging language in every response. Technical accuracy is preserved; only ceremony is removed. Stays active until the user explicitly disables it.

**Key behaviors:**

- Terse fragments over full sentences
- Short synonyms preferred (e.g., "use" not "utilize")
- Persists across the entire conversation once triggered

---

### `/handoff`

Compacts the current conversation into a handoff document so another agent can continue the work.

The document is saved to the OS temp directory and includes a "suggested skills" section listing which skills the next agent should load. It does not duplicate content already in artifacts and redacts sensitive information.

**Key behaviors:**

- Saves to temp dir (not the project) — lightweight, not committed
- Suggested skills section helps the receiving agent orient quickly
- Redacts credentials, tokens, and PII

---

### `/teach`

Multi-session skill instruction that builds lasting fluency, not just momentary recall.

The agent captures teaching context in `MISSION.md` (why the user is learning), `RESOURCES.md`, learning records, and self-contained HTML lesson files. Lessons are tied to the user's zone of proximal development and use retrieval practice and spaced repetition principles.

**Key behaviors:**

- Lessons are standalone HTML files (no external dependencies)
- `NOTES.md` captures running insights across sessions
- Explicitly distinguishes knowledge (knowing that), skills (knowing how), and wisdom (knowing when)

---

### `/write-a-skill`

Scaffolds a new agent skill with correct structure and supporting files.

The agent gathers requirements, drafts `SKILL.md` plus any needed `REFERENCE.md`, `EXAMPLES.md`, or `scripts/`, and reviews the draft with the user before finalizing. The description field is treated as critical — it must be ≤1024 characters, written in third person, and clearly state what triggers the skill.

**Key behaviors:**

- Description written for agent discovery, not human reading
- Splits into multiple files when a single SKILL.md would exceed ~100 lines
- Review step is mandatory before the skill is considered done

---

## Design & Content Skills

### `/design-an-interface`

Generates multiple radically different interface designs in parallel before committing to one.

Implements the "Design It Twice" principle: after gathering requirements, the agent spawns parallel sub-agents each working under different constraints to produce 3+ distinct designs. Designs are evaluated on simplicity, generality, implementation efficiency, depth, and ease of correct use, then synthesized.

**Key behaviors:**

- Minimum 3 designs, each with genuinely different trade-offs
- Parallel generation — wall-clock time is the slowest single design, not the sum
- Synthesis step produces a final recommendation that may combine elements from multiple designs

---

### `/edit-article`

Edits and improves an article section by section, treating its information as a directed acyclic graph.

The agent divides the article by headings, presents the section breakdown for user confirmation, then rewrites each section for clarity. Paragraphs are capped at 240 characters to enforce concision.

**Key behaviors:**

- Section plan confirmed with user before any rewriting begins
- ≤240 characters per paragraph — enforced, not advisory
- Information dependencies between sections are respected (DAG ordering)
