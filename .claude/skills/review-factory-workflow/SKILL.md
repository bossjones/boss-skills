---
name: review-factory-workflow
description: Run the multi-agent code review factory using the Workflow tool — risk-tiered specialist fan-out, a judge pass, and a human-approved GitHub review. Use when asked to "review PR 123 with the review factory", "run the review factory", "/review-factory-workflow", "do a multi-agent review of this branch", or to review a branch or PR with specialist agents rather than a single reviewer. This is the Workflow arm of the cmux-vs-Workflow bake-off; the cmux arm is review-factory-cmux.
allowed-tools:
  - Bash
  - Read
  - Write
  - Workflow
  - AskUserQuestion
  - Skill
metadata:
  version: 0.1.0
  arm: workflow
---

# Review Factory — Workflow arm

Fan out a risk-tiered team of review specialists using the `Workflow` tool, judge their
findings, and post a single unified review — after a human says yes.

This is **Arm B** of a deliberate bake-off. Arm A (`review-factory-cmux`) does the same
job with visible cmux panes. Both share the same deterministic core, the same role
prompts, and the same judge, so the only thing under test is the substrate. Do not
"improve" one arm's prompts without the other, or the comparison becomes meaningless.

## When to use

- "review PR 123 with the review factory"
- "run a multi-agent review of this branch"
- "/review-factory-workflow --base main"
- Any review where specialization and a judged, deduplicated result are worth more than
  a single reviewer's single pass.

What this arm buys, and what it costs — the mirror of the cmux arm's table:

| Buys | Costs |
| :--- | :--- |
| Deterministic control flow; schema-validated returns | The run is invisible while it happens |
| No pane machinery: no heartbeat, stall probe, or teardown | Subagents die with this orchestrator session |
| Runs headless, so it **can** be CI-triggered | You cannot reach into an agent and correct it |

## Preconditions

**The `Workflow` tool must be available in this session.** If it is not, **stop** and tell
the user to run [`review-factory-cmux`](../review-factory-cmux/SKILL.md) instead.

Do **not** substitute a different fan-out mechanism (the `Agent`/`Task` tools, a shell
loop, or reviewing the files yourself). That would still produce a plausible review and a
scorecard stamped `--arm workflow`, while measuring a substrate that is not the one under
test — corrupting the bake-off rather than failing it, which is far worse. A loud failure
is the correct outcome here.

The shared core lives in the agent-harness plugin. Re-declare `CORE` in **every** Bash
block below — the fan-out can run for many minutes, and a later block may land in a fresh
shell where an earlier `export` no longer exists:

```text
plugins/boss-dev/agent-harness/skills/review-factory-core/
```

## Step 1 — Snapshot usage, then prepare the review

Snapshot **first**, or the cost scorer cannot tell this run's agents from pre-existing
sessions.

```bash
$ CORE=plugins/boss-dev/agent-harness/skills/review-factory-core
$ uv run "$CORE/scripts/prepare_review.py" --base main --dry-run
```

Show the user the dry-run: tier, roster, files reviewed, files filtered. Then commit:

```bash
$ CORE=plugins/boss-dev/agent-harness/skills/review-factory-core
$ uv run "$CORE/scripts/prepare_review.py" --base main
$ uv run "$CORE/scripts/score_run.py" snapshot .review/<slug>
```

On success `prepare_review.py` prints the slug it chose:
`review=<slug> tier=<t> roles=<...> workspace=<path>`. **That is where `<slug>` comes
from** — every command below interpolates it.

For a PR, swap `--base main` for `--pr <url>`. Add `--tier full` to override the risk
assessment.

Read `.review/<slug>/manifest.json`. It gives you the roster, the models, and the
workspace path. **Do not invent a roster** — `prepare_review.py` already pruned the
roles with nothing to review, and that pruning is a real cost saving.

## Step 2 — Fan out with the Workflow tool

Call `Workflow` with a script shaped like the one below. The essential properties:

- **One agent per role in the manifest**, on the manifest's `specialist_model`.
- **The prompt is a one-line pointer to the brief on disk.** Not the brief's contents.
  This is what keeps the launch cheap and prompt caching effective.
- **A `schema`** on every specialist, so findings are validated at the tool layer and
  the model retries on a malformed shape.
- **The judge runs last**, on the manifest's `lead_model`, and only after every
  specialist has returned.

```javascript
export const meta = {
  name: 'review-factory',
  description: 'Risk-tiered specialist code review with a judge pass',
  phases: [{ title: 'Review' }, { title: 'Judge' }],
}

const { workspace, roles, specialist_model, lead_model } = args

const FINDING = {
  type: 'object',
  required: ['findings'],
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        required: ['file', 'line', 'side', 'severity', 'title', 'body'],
        properties: {
          file: { type: 'string' },
          line: { type: 'integer', minimum: 1 },
          side: { type: 'string', enum: ['LEFT', 'RIGHT'] },
          severity: { type: 'string', enum: ['critical', 'moderate', 'nit'] },
          title: { type: 'string' },
          body: { type: 'string' },
          confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
          suggestion_patch: { type: 'string' },
        },
      },
    },
  },
}

phase('Review')
const results = await parallel(
  roles.map((role) => () =>
    agent(
      `Read ${workspace}/briefs/${role}.md and execute it exactly. ` +
      `Write your findings to ${workspace}/findings/${role}.jsonl, one JSON object per ` +
      `line, ending with the done-record. Also return them via StructuredOutput.`,
      { label: `review:${role}`, phase: 'Review', model: specialist_model, schema: FINDING }
    )
      .then((r) => ({ role, ...r }))
      // A dead specialist must NOT take down the run. Without this catch, one rejection
      // aborts parallel() and the judge never sees the findings the others already wrote
      // to disk. A partial review, honestly labeled, beats no review.
      .catch(() => null)
  )
)
const survived = results.filter(Boolean)

phase('Judge')
const judged = await agent(
  `Read ${workspace}/briefs/judge.md and execute it exactly. All specialists have ` +
  `finished; their findings are in ${workspace}/findings/. Write the validated ` +
  `payload to ${workspace}/review-payload.json.`,
  { label: 'judge', phase: 'Judge', model: lead_model }
)

return { workspace, specialists: survived.length, died: roles.length - survived.length, judged }
```

Pass `args` from the manifest — never hardcode the roster. If `died > 0`, say so plainly
in the summary: a review missing a specialist is still a useful review, but the user must
know which lens was absent.

## Step 3 — Validate the findings

The specialists also wrote JSONL to disk. Gate it before trusting the judge:

```bash
$ CORE=plugins/boss-dev/agent-harness/skills/review-factory-core
$ uv run "$CORE/scripts/validate_findings.py" .review/<slug>
```

This rejects findings anchored to lines that do not exist in the diff. If a role comes
back `MISSING` or `UNFINISHED`, its agent died — re-run just that agent rather than the
whole team.

## Step 4 — Validate the payload

The judge's payload must satisfy the schema that `pr-review` already owns:

```bash
$ uv run plugins/boss-dev/agent-harness/skills/pr-review/scripts/validate_review.py \
    .review/<slug>/review-payload.json
```

Fix and re-prompt the judge until this passes. Do not hand-edit the payload — if the
judge cannot produce a valid one, that is a finding about the judge.

## Step 5 — Show the human, then post

**Never post without explicit approval.** Review comments are public and permanent, and
this is a machine's opinion.

Show the verdict and every comment that would be posted — file, line, severity, and
body. Then use `AskUserQuestion` to confirm.

Only on a yes, post via the [`github-pr-review`](../../../plugins/boss-dev/agent-harness/skills/github-pr-review/SKILL.md)
rails: a pending review, batched comments, then submit with the payload's `event`.

In local mode (`--base`) there is nothing to post. Render the payload to
`.review/<slug>/report.md` and show it.

## Step 6 — Score the run

```bash
$ CORE=plugins/boss-dev/agent-harness/skills/review-factory-core
$ uv run "$CORE/scripts/score_run.py" report .review/<slug> --arm workflow
```

Report cost, cache hit rate, and the cost-per-finding table to the user. That table is
the point: it says which specialist earned its keep and which should be cut from
`review-tiers.json`.

## Rules

- **No agent posts to GitHub.** Specialists write only their own findings file. The
  judge writes only the payload. You post, and only after the human agrees.
- **Never skip the validators.** They exist because models hallucinate line numbers,
  and a wrong anchor is worse than a missing finding.
- **Never edit the shared core to make this arm look good.** Both arms must stay
  identical apart from the substrate, or the bake-off proves nothing.
- Finding nothing is a real, successful outcome. Report a clean review as a clean
  review.
