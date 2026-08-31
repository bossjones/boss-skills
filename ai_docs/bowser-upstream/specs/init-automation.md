# Init Browser Automation

Build a reusable browser automation command system — composable slash commands stored in `.claude/commands/bowser/` that wrap the existing Bowser skills for repeatable, parameterized workflows.

## Problem

Right now Bowser has skills (low-level browser driving) and agents (parallel QA validation), but no middle layer for **repeatable personal automation workflows** — things like "add items to my Amazon cart", "check my GitHub notifications", "scrape a competitor's pricing page". Each time you want to run one, you type a freeform prompt. There's no way to save, reuse, or share these workflows.

## Solution

A two-layer command system:

1. **`hop-automate.md`** — A higher-order orchestration command that accepts a workflow name + optional overrides, resolves defaults, and delegates to the actual workflow command.
2. **`<workflow>.md`** — Individual workflow commands containing step-by-step browser automation instructions. Focused purely on _what to do in the browser_.

```
User runs:  /bowser:hop-automate amazon-add-to-cart "wireless earbuds under $30"

            ┌─────────────────────────────────────────────────┐
            │  hop-automate.md                                │
            │  Resolves: skill=claude-bowser, mode=headed,    │
            │  vision=false, workflow=amazon-add-to-cart       │
            │                                                 │
            │  ┌───────────────────────────────────────────┐  │
            │  │  amazon-add-to-cart.md                     │  │
            │  │  Steps: search → filter → add to cart →   │  │
            │  │  proceed to checkout → stop                │  │
            │  └───────────────────────────────────────────┘  │
            └─────────────────────────────────────────────────┘
```

## File Structure

```
.claude/commands/bowser/
├── hop-automate.md              # Higher-order orchestrator
├── amazon-add-to-cart.md        # Example workflow: Amazon shopping
└── <future-workflows>.md       # Drop new workflows here
```

## Deliverables

### 1. `hop-automate.md`

The orchestration command. Accepts a workflow name and optional parameter overrides.

**Frontmatter:**

```yaml
---
model: opus
description: Run a saved browser automation workflow with configurable skill, mode, and vision settings
argument-hint: <workflow-name> [prompt] [playwright|claude] [headed|headless] [vision]
---
```

**Variables (parsed from `$ARGUMENTS`):**

| Variable | Source | Default | Description |
|----------|--------|---------|-------------|
| WORKFLOW | $1 (required) | — | Name of the workflow file in `.claude/commands/bowser/` (without `.md`) |
| PROMPT | $2 (optional) | "" | Freeform input passed to the workflow (e.g., item to search for) |
| SKILL | keyword detection | `playwright-bowser` | Which skill to use: `playwright` or `claude` |
| MODE | keyword detection | `headed` | Browser visibility: `headed` or `headless` |
| VISION | keyword detection | `false` | Whether to enable vision mode |

**Keyword detection rules:**
- If `claude` appears in args → SKILL = `claude-bowser`
- If `playwright` appears in args → SKILL = `playwright-bowser`
- If `headless` appears in args → MODE = `headless`
- If `headed` appears in args → MODE = `headed`
- If `vision` appears in args → VISION = `true`
- Remaining non-keyword text after WORKFLOW becomes PROMPT

**Workflow:**

1. Parse `$ARGUMENTS` to extract WORKFLOW, PROMPT, SKILL, MODE, VISION
2. Validate WORKFLOW — check that `.claude/commands/bowser/{WORKFLOW}.md` exists (via Glob). If not found, list available workflows and stop.
3. Read the workflow file to get the workflow steps
4. Execute the appropriate skill (`/playwright-bowser` or `/claude-bowser`) with:
   - The workflow steps as the primary instructions
   - PROMPT injected where the workflow references `{PROMPT}`
   - MODE passed as `headed: {MODE}`
   - VISION applied if enabled
5. Report results back to the user

### 2. `amazon-add-to-cart.md` (Example Workflow)

The first workflow to validate the system. Uses `claude-bowser` (your real Chrome, already logged in to Amazon) by default.

**Frontmatter:**

```yaml
---
description: Search Amazon, add item(s) to cart, proceed to checkout, stop
defaults:
  skill: claude-bowser
  mode: headed
  vision: false
---
```

**Workflow steps:**

```
1. Navigate to https://www.amazon.com
2. Verify the homepage loads (look for the search bar)
3. Search for: {PROMPT}
4. Verify search results appear
5. Click into the first relevant result
6. Verify the product detail page loads with title, price, and "Add to Cart" button
7. Click "Add to Cart"
8. Verify the cart confirmation appears (look for "Added to Cart" or cart count increment)
9. Click "Proceed to checkout" or navigate to the cart
10. Verify the checkout page loads with the item visible
11. STOP — do not submit the order
12. Report: item name, price, and confirmation that it reached checkout
```

**Key design points:**
- Steps reference `{PROMPT}` for the search query — this gets injected by `hop-automate`
- Uses `claude-bowser` by default because Amazon requires authentication for checkout
- Explicitly stops before submitting any order
- Reports what it found so the user can verify

## Conventions

- Workflow files are **pure browser instructions** — no skill selection, no mode config. That's `hop-automate`'s job.
- Workflows reference `{PROMPT}` as a placeholder for user-provided freeform input.
- Each workflow file can declare `defaults:` in its frontmatter to suggest a preferred skill/mode, but `hop-automate` overrides always win.
- Workflow files live alongside `hop-automate.md` in `.claude/commands/bowser/` so they're discoverable as standalone commands too (for power users who want to skip the orchestrator).

## Usage Examples

```bash
# Run Amazon workflow with claude-bowser (its default)
/bowser:hop-automate amazon-add-to-cart "wireless earbuds under $30"

# Override to use playwright instead
/bowser:hop-automate amazon-add-to-cart "usb-c hub" playwright headless

# Run directly without the orchestrator (power user)
/bowser:amazon-add-to-cart "mechanical keyboard"

# Future workflows follow the same pattern
/bowser:hop-automate github-check-notifications
/bowser:hop-automate competitor-pricing "acme.com/pricing"
```

## Relationship to Existing Architecture

This sits as a **new command layer** alongside `ui-review`, not replacing anything:

```
.claude/commands/
├── ui-review.md              # Existing: parallel QA validation
└── bowser/                   # New: repeatable personal automations
    ├── hop-automate.md       # Orchestrator with defaults + overrides
    └── amazon-add-to-cart.md # Individual workflow
```

The existing four-layer architecture stays intact. This adds a **fifth use case** — saved, parameterized automation workflows — using the same underlying skills.

## Implementation Order

1. Create `.claude/commands/bowser/` directory
2. Build `hop-automate.md` with argument parsing, validation, and skill delegation
3. Build `amazon-add-to-cart.md` as the first workflow
4. Test: `/bowser:hop-automate amazon-add-to-cart "phone case"` with `claude-bowser`
5. Test: `/bowser:hop-automate amazon-add-to-cart "phone case" playwright headed` to verify override
