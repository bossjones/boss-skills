---
name: scaffold-skill-eval
description: Scaffolds a complete, runnable eval suite (fixtures, grader scripts, eval.yaml, runner) for a Claude Code skill. Use when asked to "scaffold an eval", "generate an eval suite for a skill", "create test fixtures and graders for a skill", or "add skillgrade tests".
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
---

# Scaffold Skill Eval

Generates a complete eval suite for a target skill. The output is immediately runnable via `run_eval.sh` (headless/CI) or `/run-skill-eval` (interactive local).

## Input

- `skill_path`: Path to the skill directory (e.g., `plugins/boss-experimental/boss-experimental/skills/my-skill`). Must contain `SKILL.md`.

## Constraints

- MUST NOT create files outside the target skill's `eval/` directory.
- MUST NOT add code blocks with language identifiers inside SKILL.md files.
- MUST follow the `{skill-name}/SKILL.md` directory convention.
- Every generated grader script MUST output valid JSON: `{"score": 0.0-1.0, "details": "..."}`.
- The `run_eval.sh` MUST be copied verbatim from the reference implementation — it auto-detects the skill name from the directory, no edits needed.
- Test fixtures MUST be minimal — only the files the skill actually reads.

## Steps

### 1. Validate the target skill

Read `{skill_path}/SKILL.md`. Verify it exists and has YAML frontmatter with a `description` field. If it doesn't, stop and report what's missing — don't scaffold an eval for a broken skill.

### 2. Analyze the skill's contract

From the SKILL.md, extract:

- **Inputs**: What does the skill expect as input? (e.g., a project path, a file path, a configuration)
- **Outputs**: What format does the skill produce? (e.g., markdown table, JSON, checklist)
- **Checks or steps**: What are the discrete things the skill validates or produces? Each one becomes a potential fixture.
- **Pass/fail criteria**: What keywords or patterns indicate success or failure in the output? (e.g., PASS, FAIL, WARN, error messages, specific section headers)

Write this analysis to `{skill_path}/eval/ANALYSIS.md` as a working doc. This file is not checked in — it's a scratchpad for the next steps.

### 3. Design test fixtures

Create one fixture per failure mode. Every fixture must have both a **positive control** (expected to pass) and at least one **negative control** (expected to fail in a specific, predictable way).

For each fixture:

1. Create a directory under `{skill_path}/eval/test-fixtures/{fixture-name}/`.
2. Add only the files the skill reads. Keep them minimal — the smallest input that triggers the specific behavior.
3. Name fixtures after what they test, not what they contain (e.g., `missing-config` not `project-without-config-file`).

**Fixture selection strategy:**

1. **Identify categories.** Group the skill's checks by category (e.g., structure, content quality, references). If the skill doesn't have explicit categories, group by the type of thing being checked.
2. **Cover every category.** At least one negative fixture per category. A fixture that only tests a category you already cover is less valuable than one that opens a new category.
3. **Prioritize by real-world frequency.** Within a category, prefer checks that catch mistakes developers actually make — not just the ones that are easiest to construct fixtures for. Common anti-patterns (content in the wrong place, duplication, oversized files, inline code) are more valuable than edge cases.
4. **One positive control** where the skill should report full success.
5. **Target range:** 3–12 fixtures total. Don't stop at the minimum if the skill has checks across many categories.

### 4. Write grader scripts

Create grader scripts under `{skill_path}/eval/graders/`. Each grader must:

- Accept an output file path as its last argument.
- Output a single JSON line: `{"score": 0.0, "details": "..."}` or `{"score": 1.0, "details": "..."}`.
- Handle the missing-file case (output score 0.0).
- Exit 0 regardless of score.
- Do NOT require `chmod +x` — eval.yaml invokes graders via `node graders/...` so execute permission is not needed.

**Reuse these patterns where possible** — read the reference graders at `references/graders/` (within this skill) before writing new ones. Only create a new grader when the reference patterns don't fit.

Available reference graders:
- `check-fail-present.js <pattern> <output-file>` — asserts FAIL appears for a named check.
- `check-no-fails.js <output-file>` — asserts zero FAILs (for positive controls).
- `check-warn-or-fail-present.js <pattern> <output-file>` — asserts WARN or FAIL for a named check.
- `check-no-fail-for-pattern.js <pattern> <output-file>` — asserts no FAIL appears for a named check.
- `check-eval-structure.js <skill-dir>` — asserts eval.yaml/README/run_eval.sh + ≥1 grader + ≥1 fixture.
- `check-eval-yaml-tasks.js <output-file>` — asserts eval.yaml has ≥1 well-formed task.
- `check-fixture-count.js <output-file>` — asserts the fixture count is in range.
- `check-stopped-early.js <output-file>` — asserts the scaffolder stopped when the target was invalid.

If the target skill's output format differs from a status table (e.g., JSON, checklist, prose), write graders that match that format. The scoring protocol (JSON with `score` and `details`) is always the same.

**When to add `llm_rubric` graders:**

Prefer deterministic graders wherever possible. Add `llm_rubric` (as a weighted complement, not a replacement) when:

- **Positive controls** — the deterministic grader checks for absence of failures, but `llm_rubric` can verify output format completeness and that all expected sections/categories are present.
- **Recommendation quality matters** — if the skill's value is in *what it suggests* (not just what it flags), a deterministic grader only confirms detection. Add `llm_rubric` to verify the recommendation is actionable and specific (e.g., "did it name the specific file to move?" rather than just "did it say WARN?").
- **Subjective output** — prose summaries, explanations, or reports where correctness can't be reduced to keyword matching.

For tasks where detection alone is sufficient (the grader checks that the right status appeared for the right check), deterministic-only is fine. Don't add `llm_rubric` to every task — it adds cost and non-determinism.

### 5. Write eval.yaml

Read the schema reference at `plugins/boss-experimental/boss-experimental/references/skillgrade-eval-yaml-schema.md` — the generated eval.yaml must conform to this schema since skillgrade parses it in CI.

Create `{skill_path}/eval/eval.yaml` with one task per fixture. Follow this structure:

- `version: "1"`
- `defaults`: set `agent: claude`, `provider: local`, `trials: 5`, `timeout: 300`, `threshold: 0.8`.
- `tasks`: one entry per fixture. Each task has:
  - `name`: matches the fixture directory name.
  - `instruction`: tells the agent to read the SKILL.md, run it against the fixture, and write output to `output.md`. Be explicit — name the skill, provide the fixture path, specify the output filename.
  - `workspace`: maps the fixture into the agent's workspace.
  - `graders`: one or more graders per task with `weight` fields. Use `type: deterministic` with a `run` command for pattern-matching graders. Use `type: llm_rubric` with a `rubric` field for subjective quality checks. Prefer deterministic graders; add `llm_rubric` only when needed.

### 6. Copy the unified runner

Read the reference runner at `references/run_eval.sh` (within this skill). Copy it verbatim to `{skill_path}/eval/run_eval.sh`. It delegates to skillgrade in CI and directs users to `/run-skill-eval` for local dev. No edits needed — it auto-detects the skill name from the directory.

### 7. Write README.md

Create `{skill_path}/eval/README.md` covering:

- What the eval tests (one sentence).
- Table of fixtures: name, what it tests, expected result.
- How to run: locally (`./run_eval.sh`) and interactively (`/run-skill-eval`).
- How to add new fixtures.

### 8. Add .gitignore for eval outputs

Create `{skill_path}/eval/.gitignore` to prevent transient output files from being committed:

```
# eval output files are transient — generated by /run-skill-eval
output-*.md
```

### 9. Clean up and verify

- Delete `ANALYSIS.md` (working doc, not checked in).
- Run each grader against a mock output to confirm it produces valid JSON (use `node graders/check-*.js` — no execute permission needed).
- List all created files and report the fixture count.

## Output

Report the scaffolded eval suite:

```
Eval scaffolded for: {skill-name}
  Fixtures: {count}
  Graders:  {count}
  Files created:
    {skill_path}/eval/eval.yaml
    {skill_path}/eval/run_eval.sh
    {skill_path}/eval/README.md
    {skill_path}/eval/.gitignore
    {skill_path}/eval/graders/...
    {skill_path}/eval/test-fixtures/...

  Run: cd {skill_path}/eval && ./run_eval.sh --smoke
  Or:  /run-skill-eval {skill_path}
```

## Reference

- Schema: `plugins/boss-experimental/boss-experimental/references/skillgrade-eval-yaml-schema.md`
- Reusable graders: `references/graders/` (within this skill)
- Reference skill: `plugins/boss-experimental/boss-experimental/skills/claude-config-validation`
