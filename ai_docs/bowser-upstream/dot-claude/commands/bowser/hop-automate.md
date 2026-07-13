---
model: opus
description: Run a saved browser automation workflow with configurable skill, mode, and vision settings
argument-hint: <workflow-name> [prompt] [playwright|claude] [headed|headless] [vision]
---

# Hop Automate

Run a saved browser automation workflow from `.claude/commands/bowser/` with configurable defaults and overrides.

## Variables

Parse `$ARGUMENTS` to extract these variables:

- **WORKFLOW:** $1 (required) — name of the workflow file (without `.md`)
- **SKILL:** keyword detection — `playwright-bowser` (default) or `claude-bowser`
- **MODE:** keyword detection — `headed` (default) or `headless`
- **VISION:** keyword detection — `false` (default), `true` if `vision` keyword present
- **PROMPT:** all remaining non-keyword text after WORKFLOW

**Keyword detection rules (case-insensitive, applied to $ARGUMENTS after extracting WORKFLOW):**
- `claude` → SKILL = `claude-bowser`
- `playwright` → SKILL = `playwright-bowser`
- `headless` → MODE = `headless`
- `headed` → MODE = `headed`
- `vision` → VISION = `true`
- Everything else after WORKFLOW (minus detected keywords) → PROMPT

## Workflow

### Phase 1: Parse and Validate

1. If no `$ARGUMENTS` provided, list all available workflows in `.claude/commands/bowser/` (excluding `hop-automate.md`) and stop.
2. Extract WORKFLOW from the first argument.
3. Use Glob to check that `.claude/commands/bowser/{WORKFLOW}.md` exists. If not found, list available workflows and stop with an error message.
4. Parse remaining arguments for keywords (SKILL, MODE, VISION) and collect leftover text as PROMPT.

### Phase 2: Load Workflow

5. Read `.claude/commands/bowser/{WORKFLOW}.md`.
6. Check the workflow's frontmatter for `defaults:` — if present, use those as base values for SKILL, MODE, and VISION. Any keyword overrides from step 4 take priority over workflow defaults.
7. Extract the workflow content (everything after the frontmatter `---` block). This contains the browser automation steps.

### Phase 3: Execute

8. Execute the resolved skill (`/playwright-bowser` or `/claude-bowser`) with a combined prompt:

```
(headed: {MODE}) (vision: {VISION})

{workflow content with {PROMPT} replaced by the actual PROMPT value}
```

### Phase 4: Report

9. Report the results back to the user, including:
   - Which workflow was run
   - Which skill and mode were used
   - The skill's output/results
