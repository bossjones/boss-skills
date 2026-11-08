default_prompt := "Get the current date, then go to https://simonwillison.net/, find the latest blog post by Simon, summarize it, and give it a rating out of 10."

default_qa_prompt := "Navigate to https://news.ycombinator.com/. Verify the front page loads with posts. Click 'More' to go to the next page. Verify page 2 loads with a new set of posts. Go back to page 1. Click into the first post's comments link. Verify the comments page loads and at least one comment is visible."

default_hop_demo_prompt := "m4 mac mini with top specs, flowers for valentines day, pack of 10 sketch notebooks, mechanical keyboard with brown switches, USB-C docking station, blue light blocking glasses, standing desk anti-fatigue mat, Anker wireless charging pad"

# List available commands
default:
    @just --list

# ─── Layer 1: Skill (Capability) ─────────────────────────────

# Playwright skill — direct (headless by default)
test-playwright-skill headed="true" prompt=default_prompt:
    claude --dangerously-skip-permissions --model opus "/playwright-bowser (headed: {{headed}}) {{prompt}}"

# Chrome skill — direct (requires --chrome)
test-chrome-skill prompt=default_prompt:
    claude --dangerously-skip-permissions --model opus --chrome "/claude-bowser {{prompt}}"

# ─── Layer 2: Subagent (Scale) ───────────────────────────────

# Playwright subagent — isolated browser session
test-playwright-agent headed="true" prompt=default_prompt:
    claude --dangerously-skip-permissions --model opus "Use a @playwright-bowser-agent to do this: (headed: {{headed}}) {{prompt}}"

# Chrome subagent (requires --chrome)
test-chrome-agent prompt=default_prompt:
    claude --dangerously-skip-permissions --model opus --chrome "Use a @claude-bowser-agent to do this: {{prompt}}"

# QA agent — structured user story validation
test-qa headed="true" prompt=default_qa_prompt:
    claude --dangerously-skip-permissions --model opus "Use a @bowser-qa-agent: (headed: {{headed}}) {{prompt}}"

# ─── Layer 3: Command (Orchestration) ────────────────────────

# Run a saved browser automation workflow (requires --chrome)
hop workflow="amazon-add-to-cart" prompt="pack of 10 sketch notebooks" *flags="":
    export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 && claude --dangerously-skip-permissions --model opus --chrome "/bowser:hop-automate {{workflow}} {{prompt}} {{flags}}"

# UI Review — parallel user story validation across all YAML stories
ui-review headed="headed" filter="" *flags="":
    claude --dangerously-skip-permissions --model opus "/ui-review {{headed}} {{filter}} {{flags}}"

# ─── Layer 4: Just (Reusability) ─────────────────────────────

# Amazon add-to-cart — multiple items in one shot
automate-amazon prompt=default_hop_demo_prompt:
    just hop amazon-add-to-cart "{{prompt}}"

# Summarize a blog's latest post (headless, no auth needed)
summarize-blog url="https://simonwillison.net/":
    claude --dangerously-skip-permissions --model opus "/bowser:hop-automate blog-summarizer \"{{url}}\" playwright headless"
