# review-factory-core — eval suites

Two suites, deliberately separated by cost.

| Suite | Location | Spawns review agents? | Costs money? | Run it |
| :--- | :--- | :--- | :--- | :--- |
| 1 — hermetic core | `eval.yaml` + `test-fixtures/` | **No** | No | `/run-skill-eval <skill path>` |
| 2 — seeded defects | `defects/` | **Yes** (5 specialists + judge per fixture) | Yes (~$0.50–1.00/fixture) | deliberately, never in CI |

## Suite 1 — hermetic core

Every task replays a canned annotated diff through `prepare_review.py --diff-file`:
**no git, no network, and no specialist or judge agent.** It pins the decisions that must
never drift: what counts as risky, what gets filtered, what a specialist is allowed to see,
and that a hostile PR body cannot impersonate a turn.

One honest caveat: the eval harness (skillgrade / `/run-skill-eval`) is *itself* agent-driven
— a task's `instruction` is always executed by an agent. Here that agent only runs a
deterministic script. "No agents" means **no review agents**, and no git or network.

**The real CI gate is [`../scripts/tests/test_fixtures_replay.py`](../scripts/tests/test_fixtures_replay.py)**,
which asserts the same fixtures directly against the pure functions — free, deterministic, and
run by `make test` on every commit. `eval.yaml` cannot be that gate: `run_eval.sh` bails without
`ANTHROPIC_API_KEY`, and a driving agent that mistypes a path fails you on code that is correct.
This file exists to exercise the **graders** and the CLI end to end. The two share
`test-fixtures/`; changing a fixture changes both, on purpose.

### Tasks

| Task | Asserts |
| :--- | :--- |
| `tier-trivial` | exactly 10 changed lines → `trivial` |
| `tier-lite-11` | 11 lines → `lite` (lower boundary) |
| `tier-lite-100` | 100 lines → `lite` (upper boundary) |
| `tier-full-by-size` | 101 lines → `full` |
| `tier-full-by-file-count` | 25 files × 1 line → `full` — broad blast radius, which a size-only heuristic misses |
| `security-glob-forces-full` | a **2-line** `.github/workflows/ci.yml` diff → `full`. Risk beats size |
| `noise-filter-keeps-migrations` | `uv.lock` masked, `db/migrations/*.py` still **reviewed** |
| `scoping-security-not-css` | `security` focus includes `src/auth/login.py`, excludes `styles/app.css` |
| `roster-pruning` | a docs-only diff prunes `security` **and** `performance` |
| `injection-stripped` | boundary tags gone from `shared-context.md`, **prose intact** |

### Two things the fixtures encode that are easy to get wrong

- **`roster-pruning` is >100 lines on purpose.** A small docs-only diff lands `trivial`
  (roster `[generalist]`), so `security` and `performance` were never hired and "pruning" them
  would prove nothing. It must reach `full` for the assertion to mean anything.
- **`noise-filter-keeps-migrations` tests mask *recognition*, not the mask *decision*.**
  `fetch_diff.py` decides what to mask and emits the `[Auto-generated file - diff masked]`
  sentinel; it takes no raw-diff input, so its filter cannot be replayed hermetically. The
  fixture ships the sentinel pre-baked, and this asserts `prepare_review` honors it (excluded
  from tiering, anchors and patches) while the migration survives. The decision itself is
  covered by fetch-diff's own tests.

## Suite 2 — seeded defects

See [`defects/README.md`](defects/README.md). Fixtures carry known planted defects at known
lines. **`clean-no-defects` is the most important task in the suite** — it must produce *zero*
findings. Every other task rewards finding things, so a factory that flags everything would ace
them all; only the clean diff separates a real factory from a plausible-sounding noisy one.

## Graders

All emit the harness contract — a single JSON line on stdout, and **always exit 0**. The exit
code is never the signal.

```json
{"score": 1.0, "details": "..."}
```

- `graders/check_manifest.py` — `--tier`, `--roles-include/-exclude`, `--reviewed`, `--masked`,
  `--focus-include ROLE=PATH`, `--focus-exclude ROLE=PATH`
- `graders/check_no_injection.py` — `--must-contain` (prose that must survive stripping)
- `graders/check_findings.py` — `--anchor FILE:LINE`, `--within`, `--severity`, `--role`,
  `--expect-none` (suite 2)

## Running

```bash
# Suite 1, in-session (no API key needed)
/run-skill-eval plugins/boss-dev/agent-harness/skills/review-factory-core

# The deterministic gate — what actually runs in CI
uv run pytest plugins/boss-dev/agent-harness/skills/review-factory-core/scripts/tests/

# Headless (needs ANTHROPIC_API_KEY)
./run_eval.sh --smoke
```

Note: `run_eval.sh` and `/run-skill-eval` execute from **this** directory, which is why task
commands use `../scripts/prepare_review.py` and graders use `ws/<slug>/manifest.json`. The
workspace slug is `replay-<fixture-stem>`, from `derive_review_id()`.
