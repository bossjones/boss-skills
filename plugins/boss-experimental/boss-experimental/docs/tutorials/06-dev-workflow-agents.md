# Tutorial 6 — Using the dev-workflow agents

The plugin ships eight subagents under
[`agents/`](../../agents/). They implement a lightweight architect → coder → test → review →
ship loop, plus a read-only config reviewer.

> **Experimental / optional.** This set overlaps with `agent-harness`'s existing `builder` /
> `validator` team agents. You do **not** need these agents to use the eval system (Tutorials
> 2–4) or config validation (Tutorial 5). Adopt them only if you want this particular workflow.

## The set

| Agent | Role | Writes files? |
|-------|------|---------------|
| `architect` | Produces a technical requirements / design document (TRD) before implementation | Only the design doc |
| `coder` | Implements features / fixes production code | Yes |
| `test-writer` | Writes test files (TDD red) | Yes (tests) |
| `tester` | Runs build/lint/test and reports a structured pass/fail table | No (read-only) |
| `reviewer` | Reviews a diff; emits a parseable verdict | No (read-only) |
| `pr-submission` | Branch, commit, push, open a PR — behind a hard human gate | No source writes |
| `learner` | After a workflow, updates CLAUDE.md / agents / skills with what was learned | Yes (config) |
| `config-reviewer` | Reviews `.claude/` config against the knowledge architecture | No (read-only) |

## 1. Invoke an agent

Agents are invoked like any Claude Code subagent — by asking for the role, or explicitly via the
Task tool / your harness's agent selector. For example:

- *"Use the **architect** agent to write a TRD for adding rate-limiting to the API."*
- *"Have the **coder** agent implement the plan in `docs/trd-rate-limiting.md`."*
- *"Ask the **tester** agent to run the suite and report what fails."*
- *"Get the **reviewer** agent to review the current diff."*

Each agent's frontmatter declares its `tools` and `capabilities`; e.g. `tester`, `reviewer`, and
`config-reviewer` have no write tools because their contract is read-only.

## 2. Behavior contracts worth knowing

These are intentional and preserved from the source agents:

- **`architect` writes only the design doc.** It has the `Write` tool, but its instructions
  restrict it to the TRD — it never authors production code.
- **`reviewer` emits a parseable verdict.** Its output ends with a line of the form:

  ```text
  ## Verdict: APPROVE
  ```

  or `## Verdict: REQUEST_CHANGES`, so an orchestrator can gate on it.
- **`pr-submission` has a hard human gate.** Because it runs with elevated permissions, it will
  **not push** until you reply with the literal string:

  ```text
  CONFIRM PUSH
  ```

  Anything else aborts the push. This is a deliberate stop-check before code leaves your machine.
- **`config-reviewer` is read-only and leans on Component B.** Its first step runs the
  [`claude-config-validation`](../../skills/claude-config-validation/SKILL.md) skill as a
  mechanical floor (Tutorial 5), then it adds architectural judgment from
  [`references/knowledge-architecture.md`](../../references/knowledge-architecture.md). It reports
  findings and never modifies files.

## 3. A minimal end-to-end loop

```text
1. architect      → "Write a TRD for feature X"            (produces docs/trd-x.md)
2. coder          → "Implement docs/trd-x.md"              (edits source)
3. test-writer    → "Write tests for the new behavior"     (adds tests)
4. tester         → "Run the suite"                        (reports pass/fail)
5. reviewer       → "Review the diff"                      (## Verdict: APPROVE)
6. pr-submission  → "Open a PR"  → replies, you type: CONFIRM PUSH
7. learner        → "Capture what we learned"              (updates CLAUDE.md/skills)
```

You can run any subset — the agents are independent. Commands like build/lint/test are taken
from the project's `CLAUDE.md`, so the agents adapt to your repo rather than assuming a
particular toolchain.

## That's the tour

You've now covered the whole plugin: install (1), local evals (2), scaffolding evals (3), CI
with skillgrade (4), config validation (5), and the dev-workflow agents (6). For the *what* and
*why* behind each piece, see the [coding docs](../01-architecture.md) and the
[plugin README](../../README.md).
