---
name: run-skill-eval
description: Runs a Claude Code skill's eval suite — executes each eval.yaml task against its fixtures, scores with graders, reports pass/fail. Use when asked to "run skill evals", "run the eval suite", "score a skill against its fixtures", or "check if a skill passes its evals".
allowed-tools:
  - Read
  - Bash
  - Glob
  - Grep
---

# Run Skill Eval

Run the skill eval suite for the skill path given in the request (default: `plugins/boss-experimental/boss-experimental/skills/claude-config-validation`).

## Constraints

- This skill requires `Bash` to run grader scripts. It must execute in the main session — do NOT delegate to a background subagent. Background subagents auto-deny Bash prompts, causing silent failures.
- Run every task in the eval.yaml — do not skip any.
- For each task, actually execute the full skill procedure (all checks). Do not shortcut.
- Write output files in the exact format the skill specifies so graders can parse them.
- If a grader fails to run, report score 0.0 for that task and note the error.
- For `llm_rubric` graders, be strict — only score 1.0 if the output clearly meets the rubric criteria.

## Steps

1. **Cleanup**: Delete any `eval/output-*.md` files from a previous run so graders see fresh results.

2. Read the `eval/eval.yaml` inside the skill directory. Parse all tasks — each has a `name`, `instruction`, `workspace` (fixture path), and `graders`.

3. For each task:
   a. Read the skill's `SKILL.md` to understand what it does.
   b. Follow the skill's steps against the fixture at the path specified in the task's `workspace`.
   c. Write the full skill output to `eval/output-{task-name}.md`.
   d. Run **all** graders for the task and compute a weighted score:
      - **`deterministic` graders**: Run the `run` command with `Bash` from the `eval/` directory. Replace `output.md` in the command with `output-{task-name}.md`.
      - **`llm_rubric` graders**: Read the `rubric` text and the output file (`eval/output-{task-name}.md`). Evaluate the output against the rubric yourself — score 1.0 if the output meets the rubric, 0.0 if not. Return a JSON object: `{"score": 1.0, "details": "reason"}`.
   e. Compute the weighted score: `sum(score * weight) / sum(weight)` across all graders. The task passes if the weighted score is 1.0.

4. After all tasks complete, print a summary table:

```
| Task | Score | Details |
|------|-------|---------|
| valid-project | 1.0 | deterministic(0.7): 1.0, llm_rubric(0.3): 1.0 |
| missing-agents | 1.0 | deterministic(1.0): 1.0 |
| ... | ... | ... |
```

5. Report the overall pass rate: `{passed}/{total} tasks passed`.
