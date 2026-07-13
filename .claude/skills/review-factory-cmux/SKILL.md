---
name: review-factory-cmux
description: Run the multi-agent code review factory as a visible cmux team — a judge pane plus risk-tiered specialist panes, then a human-approved GitHub review. Use when asked to "review PR 123 with a cmux review team", "spin up a review team", "/review-factory-cmux", or to run the review factory in visible panes you can watch and intervene in. This is the cmux arm of the cmux-vs-Workflow bake-off; the Workflow arm is review-factory-workflow.
allowed-tools:
  - Bash
  - Read
  - Write
  - AskUserQuestion
  - Skill
metadata:
  version: 0.1.0
  arm: cmux
---

# Review Factory — cmux arm

Same factory, different substrate: the specialists run as **visible cmux panes** you can
watch, read, and intervene in, rather than as in-process subagents.

This is **Arm A** of a deliberate bake-off against
[`review-factory-workflow`](../review-factory-workflow/SKILL.md). Both arms share the
same deterministic core, the same role prompts, and the same judge. Only the substrate
differs. **Do not change one arm's prompts without the other** — that would invalidate
the comparison, which is the entire reason both exist.

What this arm buys, and what it costs, is exactly what the bake-off is measuring:

| Buys | Costs |
| :--- | :--- |
| You can *see* the agents work and intervene in a pane | A heartbeat loop, stall detection, and timeouts |
| Panes are independent OS processes with their own caches | The team can outlive (or be orphaned by) this session |
| Survives the orchestrator session dying | It cannot run headless, so it can never be CI-triggered |

## Step 1 — Prepare (identical to the other arm)

```bash
$ CORE=plugins/boss-dev/agent-harness/skills/review-factory-core
$ TEAM=plugins/boss-dev/agent-harness/skills/boss-cmux-team
$ uv run "$CORE/scripts/prepare_review.py" --base main --dry-run
```

Show the user the dry-run: tier, roster, files reviewed, files filtered. Then commit:

```bash
$ uv run "$CORE/scripts/prepare_review.py" --base main
$ uv run "$CORE/scripts/score_run.py" snapshot .review/<slug>
```

For a PR, swap `--base main` for `--pr <url>`. Add `--tier full` to override the risk
assessment. `prepare_review.py` prints the slug it chose (`review=<slug> ...`); every
command below uses it.

Read `.review/<slug>/manifest.json`. It gives you the roster, the models, and the
workspace path. **Do not invent a roster** — `prepare_review.py` already pruned the roles
with nothing to review, and that pruning is a real cost saving.

## Step 2 — Generate a team config

Write `.review/<slug>/team.json`, driven entirely by the manifest:

- **One role per role in `manifest.json`**, in manifest order, with the **judge first**
  (`spawn_team.py` treats the first role as the lead and gives it the left half).
- **Models come from the manifest**: `lead_model` for the judge, `specialist_model` for
  the rest. Never hardcode either.

> Getting this wrong does not merely produce a thin review — it silently corrupts the
> bake-off. A 2-role cmux run scored against a 5-role Workflow run makes the
> cost-per-finding table a lie, and that table is the whole deliverable.

Every role needs a per-role `command` override, because `spawn_team.py`'s default launch
shape is pi's and `claude` does not share it (no `--name`; its `--append-system-prompt`
takes an inline string, not a path).

The excerpt below shows the **shape** — emit one block per manifest role:

```json
{
  "cwd": ".",
  "env_file": ".env",
  "workspace_color": "Blue",
  "roles": [
    {
      "name": "judge",
      "model": "<manifest.lead_model>",
      "prompt": "../../review-factory-core/assets/roles/judge.md",
      "command": "claude --dangerously-skip-permissions --model __MODEL__ 'Read .review/<slug>/briefs/judge.md and follow it.'"
    },
    {
      "name": "security",
      "model": "<manifest.specialist_model>",
      "prompt": "../../review-factory-core/assets/roles/security.md",
      "command": "claude --dangerously-skip-permissions --model __MODEL__ 'Read .review/<slug>/briefs/security.md and execute it.'"
    }
  ]
}
```

Two things that will bite you if you skip them:

- **`prompt` is required by `spawn_team.py` even though the `command` override ignores
  it** (a missing `prompt` is a `KeyError`). Relative paths resolve against
  *boss-cmux-team's* `assets/`, not the core's — hence the `../../` above. The pane is
  **not** system-prompted with this file; the brief it reads at kickoff is what carries
  the role.
- **No `completion_sentinel`.** It is deliberately absent: the kickoff line names the
  brief, so any sentinel string would be echoed to the screen the instant the agent
  started. Completion is a file (Step 4), and a sentinel in the spawn file would only
  mislead a recovering orchestrator.

**Keep every kickoff to one line.** The brief lives on disk; the command carries only a
pointer. Nothing large ever goes on a command line — that is what keeps prompt caching
working.

## Step 3 — Spawn the team

```bash
$ uv run "$TEAM/scripts/spawn_team.py" cc review-<slug> \
    --config .review/<slug>/team.json --no-exec
```

`--no-exec` is **required**. Without it, `spawn_team.py` calls `execvp` to launch a fresh
orchestrator — which would hijack the shell this Bash call is waiting on, and hang.
*You* are already the orchestrator.

## Step 4 — Find the panes, then heartbeat

`spawn_team.py` prints `window=` and `workspace=`, but **surface refs are not stable** —
positional refs renumber. Rediscover them at the moment of use, by role name:

```bash
$ WIN=<window-uuid-from-spawn-output>
$ WS=$(cmux workspace list --window "$WIN" --json \
       | jq -r --arg n "review-<slug>" '.workspaces[] | select(.custom_title==$n) | .ref')
$ cmux list-pane-surfaces --workspace "$WS"     # -> role name to surface ref
```

**Completion is an artifact, never a sentinel on screen.** Watch the files:

```bash
$ until uv run "$CORE/scripts/validate_findings.py" .review/<slug> --json \
        | jq -e '[.roles[] | .done] | all' >/dev/null; do sleep 20; done
```

A specialist is finished when its `findings/<role>.jsonl` ends with a
`{"type":"done",...}` record.

`read-screen` is a **stall diagnostic only** — never a completion signal. If a role has
produced nothing for a while, take two reads ~10s apart and compare:

```bash
$ cmux read-screen --surface <ref> --lines 40
```

If they are identical, the pane is stuck (usually a permission prompt or a crashed
launcher). Report it rather than waiting forever.

Timeouts: **10 minutes per specialist, 25 minutes overall.** On a timeout, proceed with
whatever findings exist and say plainly which role did not finish. A partial review,
honestly labeled, beats a hung session.

## Step 5 — Prompt the judge

Only once **every** specialist has a done-record. The judge is a **pure judge, not a
dispatcher** — it does nothing until the findings exist. (An idle lead that is also
supposed to dispatch is the classic failure of this pattern: workers wait on the lead,
the lead waits on the workers, and the run stalls.)

`send` types, `send-key enter` submits — always two steps:

```bash
$ JUDGE=$(cmux list-pane-surfaces --workspace "$WS" --json | jq -r '.[] | select(.name=="judge") | .ref')
$ cmux send --surface "$JUDGE" "All specialists are done. Judge now."
$ cmux send-key --surface "$JUDGE" enter
```

## Step 6 — Validate, approve, post, score

Identical to the other arm, and this is where they converge:

```bash
$ uv run "$CORE/scripts/validate_findings.py" .review/<slug>
$ uv run plugins/boss-dev/agent-harness/skills/pr-review/scripts/validate_review.py \
    .review/<slug>/review-payload.json
```

Show the user the verdict and every comment, use `AskUserQuestion` to confirm, and only
then post via [`github-pr-review`](../../../plugins/boss-dev/agent-harness/skills/github-pr-review/SKILL.md).
Local mode renders `report.md` instead.

```bash
$ uv run "$CORE/scripts/score_run.py" report .review/<slug> --arm cmux
```

## Step 7 — Tear down

Close the workspace as a unit once the user has the result. Do not leave five panes
burning context. Never loop-close over the whole tree — close the review workspace only.

## Recovery

If this session is lost mid-run, the team survives (that is the point of panes). Re-orient
with `/cmux-did-spawn .team/review-<slug>.spawn.json`, then resume at Step 4 — the
findings files on disk are the state, so nothing is lost.

## Rules

- **No agent posts to GitHub.** Specialists write only their own findings file; the judge
  writes only the payload. You post, and only after the human agrees.
- **Never skip the validators.** They exist because models hallucinate line numbers, and a
  wrong anchor is worse than a missing finding.
- **Completion is a file, not a screen.** `read-screen` diagnoses stalls; it never
  declares success.
- **Never edit the shared core to make this arm look good.** Both arms must stay identical
  apart from the substrate, or the bake-off proves nothing.
- Finding nothing is a real, successful outcome. Report a clean review as a clean review.
