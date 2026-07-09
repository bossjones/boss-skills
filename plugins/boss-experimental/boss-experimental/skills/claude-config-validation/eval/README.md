# Eval: claude-config-validation

Tests whether the config validation skill correctly detects valid and invalid Claude Code configurations across all 4 check categories.

## Fixtures

| Fixture                   | Category            | What it tests                                        | Expected                         |
| ------------------------- | ------------------- | ---------------------------------------------------- | -------------------------------- |
| valid-project             | Positive control    | All checks pass                                      | All PASS                         |
| missing-claude-dir        | Project Structure   | No `.claude/` directory                              | FAIL: Config exists              |
| misplaced-canonical-agent | Project Structure   | Project redefines a canonical agent (name collision) | FAIL: Canonical agents           |
| custom-pipeline-agent     | Project Structure   | Declared project-prefixed custom pipeline agent      | No FAIL: Canonical agents        |
| bad-agent-frontmatter     | Project Structure   | Agent with invalid frontmatter                       | WARN/FAIL: Agent frontmatter     |
| convention-in-agent       | Knowledge Placement | File conventions in agent body                       | WARN: Convention placement       |
| duplicated-content        | Knowledge Placement | CLAUDE.md content copied into agent                  | WARN: Duplication                |
| oversized-claude-md       | Knowledge Placement | CLAUDE.md over 200 lines                             | WARN: CLAUDE.md size             |
| skill-with-code-blocks    | Skill Quality       | Skill with fenced code blocks                        | WARN/FAIL: Skill content quality |
| oversized-skill           | Skill Quality       | Skill over 150 lines                                 | WARN: Skill size                 |
| missing-skill-ref         | Discoverability     | Skill not in routing table                           | FAIL: Routing table              |
| broken-cross-ref          | Discoverability     | Broken cross-file reference                          | WARN/FAIL: Cross-file references |
| rule-doc-in-routing-table | Discoverability     | Rule's doc also listed in routing table              | WARN: context discipline         |

## Running

**Local dev (inside Claude Code):**

```
/run-skill-eval skills/claude-config-validation
```

**CI / headless:**

```
cd skills/claude-config-validation/eval
./run_eval.sh --smoke
```

`run_eval.sh` delegates to [skillgrade](https://www.npmjs.com/package/skillgrade)
(on PATH, or via `npx skillgrade`) when `ANTHROPIC_API_KEY` is set; otherwise it
prints the local `/run-skill-eval` instructions above.

## Adding fixtures

1. Create a directory under `test-fixtures/{fixture-name}/`
2. Add only the files the skill reads (minimal `.claude/` structure)
3. Add a task in `eval.yaml` with instruction, workspace, and graders
4. Use existing graders where possible (`check-fail-present.js`, `check-warn-or-fail-present.js`, `check-no-fails.js`)

## Reference

-   Check definitions: `../../../references/config-validation-checks.md`
-   Knowledge architecture: `../../../references/knowledge-architecture.md`
