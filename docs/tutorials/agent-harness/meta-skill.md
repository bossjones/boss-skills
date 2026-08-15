# Tutorial: Author a new skill with the meta-skill

The `Create New Skills` skill — internally called the meta-skill — is the repo's own skill for
building other skills. Rather than free-handing a `SKILL.md`, you describe what you want and the
meta-skill walks a fixed 9-step workflow: define the purpose, pick a destination, design the
frontmatter, write instructions and examples, add supporting files, validate, evaluate, and hand
off to a safe commit. This walkthrough runs that workflow once, end to end, against one running
example: a repo-internal skill named `changelog-linter` that reviews `CHANGELOG.md` entries
before a release.

**Time:** ~30 minutes · **Level:** intermediate · **Reference:**
[meta-skill `SKILL.md`](../../../plugins/boss-dev/agent-harness/skills/meta-skill/SKILL.md)

## Prerequisites

| You need | Check it |
|----------|----------|
| The plugin installed | `/plugin install agent-harness@boss-skills` |
| `uv` on PATH (for `scripts/verify-structure.py` and any PEP 723 scripts) | `uv --version` |
| A feature branch — the meta-skill never commits to `main` | `git switch -c skill/changelog-linter` |
| Familiarity with this repo's `CLAUDE.md` and `.claude/rules/skill-development.md` | skim once before starting |

The meta-skill has no slash command — it triggers on natural language, the same way any other
skill does. Just describe what you want to build and Claude Code loads it automatically because
the request matches its description ("create a new skill", "package this into a SKILL.md", and
so on).

## A sample session

> **Human:** Create a skill that lints our CHANGELOG entries.
>
> **Agent:** Before I build this, a few questions about the skill itself (Step 1 — define
> purpose):
>
> 1. What should it check — Keep a Changelog format, semver category headers
>    (Added/Changed/Fixed/Removed), entry wording, or all of the above?
> 2. When should Claude reach for it — only when explicitly asked to "lint the changelog," or
>    also proactively before a release/version bump?
> 3. Does it need a helper script, or is this a read-and-flag skill?
>
> **Human:** Format and category headers, mainly. Trigger on "lint the changelog" or "check
> CHANGELOG.md before release." A small script that parses entries would help.
>
> **Agent:** Got it. One more thing before I create the directory (Step 2 — destination): is this
> tooling just for this repo's own `CHANGELOG.md`, or something you want to ship to other repos
> as part of a plugin?
>
> [AskUserQuestion — "Where should this skill live?"]
>
> - (a) Repo-internal — `.claude/skills/changelog-linter/`, versioned via `metadata.version`
> - (b) Plugin — `plugins/<category>/<plugin-name>/skills/changelog-linter/`, versioned via
>   `plugin.json` + `marketplace.json`
>
> **Human:** Repo-internal — we're not shipping this.
>
> **Agent:** Creating `.claude/skills/changelog-linter/`. Drafting the frontmatter (Step 3):
>
> ```yaml
> ---
> name: Changelog Linter
> description: Reviews CHANGELOG.md entries against Keep a Changelog format and semver
>   category headers (Added/Changed/Fixed/Removed). Use when the user asks to lint, review, or
>   check the changelog, or before cutting a release.
> ---
> ```
>
> Now writing the workflow body (Step 4), 3 examples (Step 5), and a PEP 723 parsing script
> under `scripts/` (Step 6). Running validation next (Step 7):
> `./scripts/verify-structure.py`, `make lint`, `make markdown-lint` — all clean.
>
> Before I evaluate it (Step 8) — which eval system do you want, and how deep? This is a first
> draft, so I'd suggest PluginEval `quick` (static-only, free, <2s) or skillgrade `smoke`.
>
> **Human:** PluginEval quick is fine for now.
>
> **Agent:** Ran `make eval-skill SKILL=.claude/skills/changelog-linter DEPTH=quick` — report at
> `docs/evals/changelog-linter.md`, static checks pass, no anti-patterns flagged.
>
> The skill is ready, but I'm not committing it — you're on branch `skill/changelog-linter`.
> Take a look at `.claude/skills/changelog-linter/SKILL.md`, and when you're happy, say the word
> and I'll bump `metadata.version` and hand off to `commit-push-pr` (Step 9).
>
> **Human:** Looks good, ship it.
>
> **Agent:** Bumped `metadata.version` to `0.1.0` in the skill's frontmatter and invoked
> `commit-push-pr` to make the conventional commit, push the branch, and open the PR.

The rest of this tutorial walks the same nine steps in detail, showing what the agent actually
reads and writes at each one.

## Step 1 — Define the skill's purpose

```text
Create a skill that lints our CHANGELOG entries.
```

The meta-skill's first move is **not** to write code — it asks four questions and records the
answers (SKILL.md § "Step 1: Define the Skill's Purpose"):

1. What task or domain should this skill cover?
2. When should Claude use it — concrete triggers, not "when needed"?
3. What expertise or workflow needs to be captured?
4. Does it need scripts, templates, or reference files?

For `changelog-linter`, the answers land as: check Keep a Changelog format and semver category
headers; trigger on "lint the changelog" / "check CHANGELOG.md before release"; the expertise is
knowing the five valid category headers and the required `## [version] - date` heading shape;
yes, a small parsing script would help. These answers directly shape the frontmatter in Step 3
and the workflow in Step 4 — nothing here is thrown away.

Before answering, the meta-skill also reads its own bundled references for general skill theory
(`docs/claude_code_agent_skills.md`, `docs/claude_code_agent_skills_overview.md`,
`docs/blog_equipping_agents_with_skills.md` under the skill's own directory) — but this repo's
conventions override them wherever they conflict, per the callout at the top of its `SKILL.md`.

## Step 2 — Choose the destination and create the directory

Two hard rules govern where a skill can live, and the meta-skill will not guess when it's
unclear:

| Destination | Path | Versioned by |
|---|---|---|
| Repo-internal | `.claude/skills/<skill-name>/` | `metadata.version` in the skill's own frontmatter |
| Plugin | `plugins/<category>/<plugin-name>/skills/<skill-name>/` | the owning `plugin.json` **and** its `marketplace.json` entry, kept in lockstep |

Because "lints our CHANGELOG entries" doesn't say whether this is for this repo only or meant to
ship elsewhere, the meta-skill stops and asks with `AskUserQuestion` — (a) repo-internal or
plugin, and (b) if plugin, which category/plugin. It never assumes. Once you answer
repo-internal, it creates the directory:

```text
mkdir -p .claude/skills/changelog-linter
```

The third hard rule, restated because it's easy to violate by habit: **never** write into
`~/.claude/skills/`. Users choose install scope themselves by adding the marketplace; the agent
never installs into a home directory.

## Step 3 — Design the SKILL.md structure

Every skill needs valid YAML frontmatter before anything else:

```yaml
---
name: Changelog Linter
description: Reviews CHANGELOG.md entries against Keep a Changelog format and semver category
  headers (Added/Changed/Fixed/Removed). Use when the user asks to lint, review, or check the
  changelog, or before cutting a release.
---
```

Frontmatter requirements the meta-skill checks against:

- `name` — required, max 64 characters.
- `description` — required, max 1024 characters, and must state **both** what the skill does
  and *when* to use it, with concrete trigger words. A weak description is the single most common
  reason a skill never activates — "helps with changelogs" would fail this bar; "reviews... Use
  when the user asks to lint, review, or check the changelog" passes it.
- `allowed-tools` *(optional)* — restrict which tools the skill may use, if warranted.

## Step 4 — Write the instructions

The body follows a fixed shape: **Prerequisites → Workflow (numbered steps) → Supporting
details**. For `changelog-linter` that becomes something like:

1. Locate `CHANGELOG.md` at the repo root.
2. For each `## [version] - date` heading, confirm the version and ISO date parse.
3. Under each version, confirm every subsection header is one of `Added`, `Changed`, `Deprecated`,
   `Removed`, `Fixed`, `Security`.
4. Flag entries outside a valid subsection, or a missing `Unreleased` section at the top.
5. Report findings with line numbers, grouped by version.

The meta-skill keeps the main body focused — aiming for roughly 200–500 lines — and pushes
anything longer (a full category glossary, edge-case examples) into a `references/` file for
progressive disclosure, linked with a relative path such as
`[category-glossary.md](references/category-glossary.md)`. It also documents the skill's
**output** (a findings report with line references) and **input** (an optional path argument,
defaulting to `CHANGELOG.md`), so another agent can wire it into a release workflow later.

## Step 5 — Write the examples

Two to four concrete examples go in next — this is what lets an agent generalize the skill to a
request it hasn't seen verbatim. For `changelog-linter`, the examples cover: a correctly
formatted entry (no findings), an entry with an invalid category header like `## Improvements`
(flagged, suggested rename to `Changed`), and a version heading missing its date (flagged with
the expected `## [1.2.0] - 2026-08-15` shape).

## Step 6 — Add supporting files (optional)

Since Step 1 identified a parsing script as useful, it lands under `scripts/`, standalone with
PEP 723 inline metadata and marked executable:

```python
# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///
```

The layout for `changelog-linter` ends up as `SKILL.md` plus `scripts/lint_changelog.py` — no
`references/` needed here, since the workflow was short enough to stay in the main body.

## Step 7 — Test the skill

Validation is structural first, then behavioral:

```text
./scripts/verify-structure.py
make lint
make markdown-lint
ls -la .claude/skills/changelog-linter
```

`verify-structure.py` recognizes the plugin/skill layout, `eval/` suites, and `-workspace/`
scratch directories, and will fail if the skill folder holds anything else. `make lint` and
`make markdown-lint` catch Python and Markdown issues respectively. Then comes a live check: in a
fresh session, ask something that should match the description — "lint the changelog before I
tag this release" — and confirm Claude Code loads `changelog-linter` rather than staying silent.
If it doesn't fire, the fix is almost always a weaker-than-needed description; tighten it and
re-test.

> **Parser bug — GitHub #12781:** the skill parser executes exclamation-mark + backtick patterns
> **even inside fenced code blocks**, and a backslash escape does not help. Never put that pattern
> (or an `@`-prefixed file reference) inside a code fence in `SKILL.md` — use `$ command` notation
> and describe the syntax in prose instead. This is exactly why every command above is shown as
> plain text or a `$`-prefixed line rather than a live-executing pattern.

## Step 8 — Evaluate the skill

This repo has three eval systems, and the meta-skill interviews you for **which** system and
**how deep** before running anything — it never assumes, because depth should track maturity: a
first draft wants the fastest, cheapest signal; a later improvement loop wants a deeper one.

| Situation | Reach for | Depth |
|---|---|---|
| First draft, "does it trigger / is it structurally sane?" | PluginEval or skillgrade | PluginEval `quick`, or skillgrade `smoke` |
| Tuning a description so the skill activates reliably | skill-creator loop | benchmark + description optimizer |
| Improvement loop before merge | PluginEval | `standard` → `deep` |
| Regression gate / CI confidence | skillgrade | `reliable` → `regression` |
| Certification with a badge | PluginEval | `certify` (always deep) |

For a brand-new `changelog-linter`, the answer is PluginEval `quick` — deterministic, free, and
under 2 seconds because it's static analysis only, no LLM calls:

```text
make eval-skill SKILL=.claude/skills/changelog-linter DEPTH=quick
```

That writes a report to `docs/evals/changelog-linter.md` (repo-internal skills report directly
under `docs/evals/`; plugin skills report under `docs/evals/<plugin>/<skill>.md`). The same
invocation is also reachable through the `skill-evals` skill
(`/skill-evals --review --depth quick`), which fans out one subagent per skill. If the real
problem later turns out to be *activation* rather than structure — the skill exists but doesn't
fire reliably — reach for the `skill-creator` benchmark/description-optimizer loop instead; full
depths and invocations for all three systems live in
[references/eval-systems.md](../../../plugins/boss-dev/agent-harness/skills/meta-skill/references/eval-systems.md).

## Step 9 — Commit safely

The meta-skill will not auto-commit or auto-push, full stop. It stops here and hands control
back so you can verify the skill first. When you're ready:

- Confirm you're on a **feature branch** — skill work never lands straight on `main`.
- **Version bump.** For a repo-internal skill like `changelog-linter`, bump `metadata.version` in
  the skill's own frontmatter. (For a plugin skill, invoke the `version-bump-reviewer` skill
  instead — it bumps `plugin.json` and the matching `marketplace.json` entry in lockstep.)
- Hand off to the `commit-push-pr` skill (or make a conventional commit manually and open a PR).

Only once you say the equivalent of "looks good, ship it" does the agent perform the version
bump and invoke `commit-push-pr` — see the sample session above for exactly how that handoff
reads in practice.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Skill never activates | Vague description, no trigger phrase | Rewrite with concrete "Use when …" triggers; re-run the skill-creator loop |
| `verify-structure.py` fails | Wrong directory layout or stray files | Follow `.claude/rules/plugin-structure.md`; keep the folder to `SKILL.md` + `references/` + `scripts/` + `eval/` |
| Skill loads unexpectedly at parse time | Exclamation-mark + backtick pattern in a code fence (#12781) | Replace with `$ command` notation; move examples to a reference file |
| CI quality gate fails on a new skill | Low eval score or anti-patterns | Run PluginEval and fix the weakest dimensions before merging |
| Marketplace out of sync (plugin skills only) | `plugin.json` and `marketplace.json` versions diverged | Use the `version-bump-reviewer` skill to bump both in lockstep |

## Where to go next

- Compare with the lighter-weight `skill-creator` skill when the problem is purely
  *activation* — a skill that exists but won't fire reliably.
- Read [references/eval-systems.md](../../../plugins/boss-dev/agent-harness/skills/meta-skill/references/eval-systems.md)
  directly before an improvement loop — it has the full depths table for all three eval systems.
- Once a skill has shipped once, revisit Step 8 at a deeper depth (`standard`/`deep`, or
  skillgrade `reliable`) as part of your normal review cycle rather than only at first draft.
