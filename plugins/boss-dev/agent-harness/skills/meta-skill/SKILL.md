---
name: Create New Skills
description: >
  Creates new Agent Skills for Claude Code following this repository's conventions.
  Use when the user wants to create a new skill, when building or authoring a plugin skill,
  when packaging a workflow or domain expertise into a reusable SKILL.md, or when extending
  an existing skill. Use proactively when creating skills — it guides choosing the destination
  (repo-internal vs plugin), evaluating quality, and committing safely on a feature branch.
---

# Create New Skills

## Instructions

This skill helps you author new Agent Skills **inside this repository**. It reads the vendored
Anthropic reference docs for general skill theory, but this repo has its own conventions that
override them (see the callout below).

### Prerequisites

**Required reading** — the bundled Anthropic references in the [docs/](docs/) directory give the
general model of what a skill is and how progressive disclosure works:

1. [docs/claude_code_agent_skills.md](docs/claude_code_agent_skills.md) — guide to creating and managing skills
2. [docs/claude_code_agent_skills_overview.md](docs/claude_code_agent_skills_overview.md) — architecture
3. [docs/blog_equipping_agents_with_skills.md](docs/blog_equipping_agents_with_skills.md) — design principles

### Repository Conventions (authoritative)

> **These conventions win.** The `docs/` files are Anthropic's *general* reference. Where they
> conflict with this repository, **this callout and the repo's `rules` files win**. The
> authoritative sources are `.claude/rules/plugin-structure.md`,
> `.claude/rules/skill-development.md`, and the repo `CLAUDE.md`.

Two hard rules:

1. **Skills are created in exactly one of two places:**
   - **Repo-internal** — `.claude/skills/<skill-name>/` (tooling for *this* repo's own use).
   - **Plugin** — `plugins/<category>/<plugin-name>/skills/<skill-name>/` (a shippable unit
     distributed via `marketplace.json`).
2. **Never create or write into `~/.claude/skills/`** (or any home-directory skills dir). Users
   choose install scope themselves by adding the marketplace — the agent never installs skills
   into a user's home directory.

Throughout the steps below, `<skill-dir>` is the chosen destination — either
`.claude/skills/<skill-name>/` or `plugins/<category>/<plugin-name>/skills/<skill-name>/`.

### Understanding Skills

**What is a Skill?**

- A directory containing a `SKILL.md` file with YAML frontmatter.
- Instructions Claude loads on-demand when the description matches the task.
- Optional supporting files (scripts, references, templates).

**Progressive disclosure (3 levels):**

1. **Metadata** (always loaded): `name` and `description` in YAML frontmatter.
2. **Instructions** (loaded when triggered): the body of SKILL.md.
3. **Resources** (loaded as needed): reference files, scripts, templates.

Only relevant content enters the context window at any time.

## Skill Creation Workflow

### Step 1: Define the Skill's Purpose

Ask the user (and record the answers):

1. What task or domain should this skill cover?
2. When should Claude use it? (concrete triggers, not "when needed")
3. What expertise or workflow needs to be captured?
4. Does it need scripts, templates, or reference files?

### Step 2: Choose the destination and create the directory

Decide **repo-internal vs plugin** — this determines both the path and how the change is
versioned:

| Destination | Path | Versioned by |
| --- | --- | --- |
| Repo-internal | `.claude/skills/<skill-name>/` | a `metadata.version` field in the skill's own frontmatter |
| Plugin | `plugins/<category>/<plugin-name>/skills/<skill-name>/` | the owning `plugin.json` **and** its `marketplace.json` entry, kept in lockstep |

**Decision rule — when to use which:** repo-internal is for locally-scoped tooling only this
repo uses; a plugin is for something shippable to others. **If the destination is not clear from
the request or context, STOP and ask with `AskUserQuestion`** — (a) repo-internal or plugin, and
(b) if plugin, which existing category/plugin (list the plugin directories) or a new plugin. Do
not assume.

Create the chosen directory:

```bash
# Repo-internal
mkdir -p .claude/skills/<skill-name>

# Plugin (pick the category + plugin per .claude/rules/plugin-structure.md)
mkdir -p plugins/<category>/<plugin-name>/skills/<skill-name>
```

**Naming conventions:** lowercase with hyphens (e.g. `pdf-processing`), descriptive but concise,
avoid generic names. See `.claude/rules/plugin-structure.md` for the category list and
`CLAUDE.md` for the repo-internal-vs-plugin distinction.

### Step 3: Design the SKILL.md structure

Every skill needs valid frontmatter and a focused body:

```yaml
---
name: Your Skill Name
description: What this skill does AND when to use it, with concrete trigger phrases.
---
```

**Frontmatter requirements:**

- `name` — required, max 64 characters.
- `description` — required, max 1024 characters. Include **both** what it does and *when* to use
  it, name concrete trigger words, and be specific. A weak description is the single most common
  reason a skill never activates.
- `allowed-tools` *(optional, Claude Code only)* — restrict which tools the skill may use.

### Step 4: Write the instructions

Structure the body as: **Prerequisites → Workflow (numbered steps) → Supporting details**.

- Use clear, actionable language; number sequential steps.
- Keep the main body focused (aim for ~200–500 lines); push long menus and tables into
  `references/` files for progressive disclosure.
- Reference supporting files with relative links: `[eval-systems.md](references/eval-systems.md)`.
- Document the skill's **output** (what it produces/returns) and its **input** (arguments or
  parameters it accepts) so an agent knows how to wire it into a larger task.

### Step 5: Write the examples

Provide 2–4 concrete examples showing different use cases, input formats, and expected outcomes.
Examples are what let an agent generalize the skill to a new request.

### Step 6: Add supporting files (optional)

If the skill needs more than the main body:

- Reference docs in `references/`, templates in `templates/`, helper scripts in `scripts/`.
- Make Python scripts standalone with PEP 723 inline metadata and mark them executable.
- Use progressive disclosure — split by topic so only the needed file loads.

### Step 7: Test the skill (destination-agnostic + repo-aware)

Validate structurally and by triggering, using `<skill-dir>` (the path chosen in Step 2):

```bash
# Structure: recognizes plugin/skill layout, eval/ suites, and -workspace/ scratch
./scripts/verify-structure.py

# Lint the repo (Python + markdown)
make lint
make markdown-lint

# Confirm the frontmatter is valid and the body reads well
ls -la <skill-dir>
```

Then test triggering: in a fresh session, ask questions that match the description and confirm
Claude loads and uses the skill; refine the description if it doesn't fire.

> **Parser bug — GitHub #12781:** the skill parser executes exclamation-mark + backtick patterns
> **even inside fenced code blocks**, and the backslash escape does not help. In `SKILL.md`, never
> put that pattern (or an `@`-prefixed file reference) inside a code fence — use `$ command`
> notation and describe the syntax in prose instead. See `.claude/rules/skill-development.md`.

### Step 8: Evaluate the skill (interview-driven — never assume)

This repo has **three** eval systems. **Interview the user before running anything** — ask
(a) *which* system and (b) *how deep* — and tie depth to maturity: a first draft wants the
fastest, cheapest signal; a later improvement loop wants a deeper one. Do not assume a system or
depth.

The three systems, one line each (full menu, invocations, and the depths table live in
[references/eval-systems.md](references/eval-systems.md)):

1. **skill-creator loop** — a with-skill-vs-baseline benchmark plus a description/trigger
   optimizer; best when the issue is *activation*.
2. **PluginEval** — invoke the `skill-evals` skill, or `make eval-skill SKILL=<skill-dir>
   DEPTH=<quick|standard|deep|thorough>`; reports go to `docs/evals/`. The `quick` (static)
   depth is deterministic and free — ideal for a first-draft loop.
3. **skillgrade suites** — scaffold an `eval/` suite (the `scaffold-skill-eval` skill), then run
   it (the `run-skill-eval` skill) with the smoke/reliable/regression presets.

Concrete maturity guidance: first draft → PluginEval `quick` or skillgrade `smoke`; improvement
loop → PluginEval `deep`/`thorough` or skillgrade `reliable`/`regression`.

### Step 9: Commit safely (never auto-commit)

**Do not auto-commit or auto-push.** Stop and have the user verify the skill first. When they are
ready:

- Work on a **feature branch** — never commit skill work straight to `main`.
- **Version bump.** For a **plugin** skill, invoke the `version-bump-reviewer` skill first; it
  bumps `plugin.json` and the matching `marketplace.json` entry in lockstep. For a
  **repo-internal** skill, bump the `metadata.version` in the skill's own frontmatter.
- Then hand off to the `commit-push-pr` skill (or make a conventional commit on the feature
  branch and open a PR manually).

## Best Practices

**Description writing:**

- Good: "Transcribes audio/video to text using the Fireworks API. Use when the user asks to
  transcribe, convert speech to text, or needs a transcript."
- Bad: "Helps with audio."

**Instruction organization:**

- Keep the main body focused (~200–500 lines); split long material into `references/` files.
- One skill = one capability. Don't combine unrelated tasks.
- Use relative links for supporting files; be explicit about read-vs-execute.

## Examples

### Example 1: A code-review skill (repo-internal)

User request: *"Create a skill that reviews Python code for best practices."*

You would:

1. Read the [docs/](docs/) references for general theory.
2. Since this is tooling for *this* repo, choose the **repo-internal** destination
   (`<skill-dir>` = `.claude/skills/<skill-name>/`). If it were unclear, ask with
   `AskUserQuestion`.
3. Clarify scope: which practices (PEP 8, security, performance)? check-only or suggest fixes?
4. Create the directory and write the frontmatter:

   ```yaml
   ---
   name: Python Code Review
   description: Reviews Python code for PEP 8, security, and performance. Use when reviewing Python code or checking code quality.
   allowed-tools: Read, Grep, Glob
   ---
   ```

5. Write the workflow (read files → check style → flag security → suggest perf → summarize with
   line references), add 2–4 examples, then run Step 7 validation.

### Example 2: A data-analysis skill with scripts (plugin)

User request: *"Build a skill for analyzing CSV data with statistics and visualizations."*

You would:

1. This is a shippable capability, so choose the **plugin** destination — ask which category and
   plugin with `AskUserQuestion` if it isn't obvious.
2. Create `<skill-dir>` and a `scripts/` subdirectory beside `SKILL.md`.
3. Write PEP 723 scripts with inline dependencies:

   ```python
   # /// script
   # requires-python = ">=3.11"
   # dependencies = ["pandas", "matplotlib"]
   # ///
   ```

4. Document when to run each script and how to read its output; add examples; validate (Step 7);
   evaluate (Step 8, interview for system + depth); then commit on a feature branch with a
   version bump (Step 9).

### Example 3: A multi-file documentation skill

User request: *"Create a skill for writing docs with our company style guide."*

You would:

1. Gather the style guide and the doc types (API, user guides, architecture).
2. Choose the destination (ask if unclear), then organize supporting files under `<skill-dir>`:
   a `references/` folder for the style rules and per-doc-type guidance, and a `templates/`
   folder for the doc templates.
3. Write a `SKILL.md` that loads only the needed reference per doc type (progressive disclosure),
   add examples per doc type, and run Steps 7–9.

### Example 4: Extending an existing skill

User request: *"Add spell correction to our transcribe skill."*

You would:

1. Locate the existing skill under its `<skill-dir>` and read its `SKILL.md`.
2. Add a `references/` file with the correction mappings and wire a new workflow step that
   applies them before final output.
3. Update the examples, re-validate (Step 7), re-evaluate at a depth matched to the change
   (Step 8), and commit on a feature branch with the appropriate version bump (Step 9).

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Skill never activates | Vague description, no trigger phrase | Rewrite the description with concrete "Use when …" triggers; re-run the skill-creator loop |
| `verify-structure.py` fails | Wrong directory layout or stray files | Follow `.claude/rules/plugin-structure.md`; keep the skill folder to `SKILL.md` + `references/` + `scripts/` + `eval/` |
| Skill loads unexpectedly at parse time | Exclamation-mark + backtick pattern in a code fence (#12781) | Replace with `$ command` notation; move examples to a reference file |
| CI quality gate fails on a new skill | Low eval score or anti-patterns | Run PluginEval and fix the weakest dimensions before merging |
| Marketplace out of sync | `plugin.json` and `marketplace.json` versions diverged | Use the `version-bump-reviewer` skill to bump both in lockstep |

## Related

See also the repo's other skill-authoring and evaluation tooling — `skill-creator` and
`write-a-skill` (authoring), `skill-evals` / `scaffold-skill-eval` / `run-skill-eval`
(evaluation), and `version-bump-reviewer` / `commit-push-pr` (versioning and shipping). The full
evaluation menu is the companion file [references/eval-systems.md](references/eval-systems.md).

## Summary

Creating skills is about packaging expertise into discoverable, composable capabilities. In this
repo:

1. **Read the docs first**, but let the repo conventions override them.
2. **Choose the right destination** — repo-internal vs plugin; ask with `AskUserQuestion` if
   unclear, and never write to `~/.claude/skills/`.
3. **Write a strong description** — include what *and* when, with concrete triggers.
4. **Keep instructions focused** — offload long material to `references/`.
5. **Validate and evaluate before shipping** — interview for eval system + depth, matched to
   maturity.
6. **Commit only on a feature branch after you verify** — delegate versioning to
   `version-bump-reviewer` and shipping to `commit-push-pr`; never auto-push to `main`.
