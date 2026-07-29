# Harness doctor eval

Tests that the doctor produces a structured advisory report for both clean repositories and repositories containing legacy runtime artifacts.

| Fixture | Coverage | Expected result |
| --- | --- | --- |
| `clean-project` | Baseline report structure | Storage and advisory fields are present |
| `stale-artifacts` | Legacy artifact detection | At least one stale artifact is reported |

Run headlessly with `./run_eval.sh`, or interactively with `/run-skill-eval plugins/boss-dev/agent-harness/skills/harness-doctor`.

To add coverage, create a minimal fixture under `test-fixtures/`, add a task to `eval.yaml`, and add a deterministic grader when the expected report shape changes.
