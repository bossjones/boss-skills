# Self-Service Claude KA Validation for Your PR

Before requesting a review, run **both checks** below and then attach the results to your PR. Each check catches a different class of issue — they're complementary, not redundant.

## Why both are needed

**Step 1** is mechanical. It runs a fixed set of yes/no checks: does this exist, is this under N lines, do these references resolve. Same answer every time. Comprehensive on what it covers, but blind to judgment.

**Step 2** is judgment-driven. It answers questions Step 1 can't: is this skill *worth having*, is the placement actually right, does the description drive discovery, does this duplicate something that already exists, does the procedure gloss over hard steps. Different answer depending on context. Catches issues a checklist can't enumerate.

A PR can pass Step 1 cleanly and still have real problems Step 2 surfaces — premature abstraction, wrong placement, content that contradicts the actual codebase, descriptions that don't auto-route. The reverse is also true — Step 2 can miss mechanical issues like "this skill has no `eval/`" because the model is focused on judgment, not enumeration. Run both.

## Step 1 — Mechanical validation (skill-driven)

Run the validation skill against your project:

```
/claude-config-validation <project_path>
```

Examples:

```
/claude-config-validation apps/your-app
/claude-config-validation services/your-service
```

This runs all checks defined in [config-validation-checks.md](config-validation-checks.md), organized in six categories:

- **Project Structure** — `.claude/` exists, canonical agents, agent frontmatter
- **Knowledge Placement** — conventions in the right facility, no duplication, CLAUDE.md size
- **Skill Quality** — frontmatter, content quality, directory structure, size, `eval/` present (opt-in)
- **Discoverability & References** — routing tables, cross-file references resolve
- **Compliance Placement** — skills should be procedures, not constraint lists
- **Loading & Registration** — no nested `.claude/`, no `@import` of `.claude/` artifacts

Treat **FAIL** as blocking and **WARN** as items to either fix or justify.

**What Step 1 covers well:** structural, yes/no, present-or-not. *Is* there an `eval/`? *Is* `paths` frontmatter present? *Does* this routing entry resolve? Same answer every run.

**What Step 1 doesn't cover:** judgment. The checks are deliberately mechanical — they avoid grading "quality" because that's not enumerable.

## Step 2 — Judgment review (Claude session)

Ask Claude to review your PR directly. In a Claude Code session with your branch checked out, ask freely. Examples:

```
Review PR #<number> for Claude KA compliance and overall quality.
```

```
Review my current branch's diff against the Claude Code Knowledge Architecture.
```

```
Look at my .claude/ changes in this PR — anything off?
```

Claude reads the diff, applies the KA ([knowledge-architecture.md](knowledge-architecture.md) — point to it explicitly if you want a rigorous check), and exercises judgment a checklist can't.

The authoring-rules file (`../rules/claude-config-authoring.md`) auto-loads when your PR touches `.claude/**/*.md` or `CLAUDE.md` — no need to point Claude at it.

**What Step 2 covers well:**

- Is this skill *worth having*? Three-occurrence rule. Real adoption signal vs. documented preference.
- Is the placement actually right, or just check-passing? Skills at root that meet criteria mechanically but really belong in a project. Skills at project level that should be promoted.
- Is the description specific enough to drive auto-discovery? Step 1 only validates that `description` exists, not whether it's *good*.
- Does the skill duplicate an existing one? Step 1 catches 5+ identical consecutive lines; Step 2 catches conceptual overlap.
- Is the skill content *correct and current*? Does the guidance match what's actually in the codebase?
- Forward compatibility — does this pre-position cleanly for canonical agents, root skills, upcoming KA changes?

**What Step 2 doesn't cover:** mechanical enumeration. The model can miss "this skill has no eval/" because it's reading for judgment, not running a checklist. That's why Step 1 still matters even on a small PR.

## Step 3 — Include results in the PR description

```markdown
## Claude KA Compliance

- [ ] Ran `/claude-config-validation <path>` — results: <N PASS, M WARN, 0 FAIL>
- [ ] Asked Claude to review the PR diff (Step 2)

WARNs and how I'm handling them:

- <list any WARN you're not fixing and why>
```

This signals you've done the homework and lets the reviewer focus on judgment calls instead of mechanical checks.

## What still needs a human eye

Even with both Steps run, some things still need judgment from the config governance owners:

- **Placement judgment for KA gaps** — shared-platform skills with scattered consumers, framework-migration skills, novel content shapes the KA hasn't named yet
- **Cross-PR pattern observations** — when something recurs across PRs, it usually means the KA needs updating, not that this PR is wrong
- **Strategic forward compatibility** — does the artifact pre-position cleanly for canonical agents, root skills, or initiatives the KA hasn't formalized
- **Composition across PRs** — does the new skill compose with rules, agents, and other skills the way the KA prescribes

If your PR self-services through Steps 1 and 2, expect a fast turnaround.
