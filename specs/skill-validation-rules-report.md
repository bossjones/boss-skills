# Plan: Add `--rules-report` flag to `skill_validation.py`

## Task Description

Add a new opt-in CLI flag, `--rules-report`, to `scripts/skill_validation.py`.
When passed, the script prints an **itemized list of every validation rule** and
whether it was OK or not — both as a per-file breakdown and as a single
aggregate table across all scanned `SKILL.md` files. The report uses `rich`
tables with color highlighting keyed to each rule's severity. Default behavior
(without the flag) is unchanged.

## Objective

When this plan is complete:

- `scripts/skill_validation.py` accepts `--rules-report` (additive; combinable with `--strict`).
- A central **rule registry** lists all 17 validation rule IDs with a human-readable title and severity.
- With `--rules-report`, the script prints, for each `SKILL.md`, a per-file table of all rules with status `OK` / `INFO` / `NOT OK`, plus a final aggregate per-rule table with passed/failed counts across all files.
- Severity is color-highlighted (ERROR red, WARNING yellow, INFO cyan/dim).
- Exit codes are unchanged — the flag only adds output.
- The feature is built test-first (TDD); the new code is covered in `tests/test_skill_validation.py`.
- `make lint` and `make test` pass with zero warnings.

## Problem Statement

`scripts/skill_validation.py` reports validation results as `CheckResult` objects
that are **only created when a rule fails**. A rule that passes produces nothing.
The current output (`print_file_report`, `print_summary`) therefore shows
*findings* but never confirms *which rules were checked and passed*. A user
auditing a skill cannot see, at a glance, the full checklist of 17 rules with a
pass/fail mark against each. There is also no single source of truth for the set
of rule IDs — they exist only as scattered string literals inside check
functions, which makes a complete "all rules" view impossible to build reliably.

## Solution Approach

1. **Add a rule registry** — a `RULE_REGISTRY` tuple of `RuleSpec(rule_id, title, level)`
   covering all 17 rule IDs currently emitted as `CheckResult(...)` literals. This
   becomes the canonical list the report iterates over. A meta-test guards the
   registry against drift by scanning the source for `CheckResult("...")` literals.
2. **Add pure aggregation functions** (no I/O, mirroring the existing
   "pure check functions / separate display" pattern):
   - `build_file_rules_report(report)` -> per-file rule rows.
   - `build_rules_report(reports)` -> aggregate per-rule outcomes.
3. **Add display functions** that render `rich` tables: `print_file_rules_report`
   and `print_rules_report`.
4. **Wire `--rules-report` into `main()`** so per-file tables print alongside each
   per-file report and the aggregate table prints before the final summary panel.

A rule counts as **OK** for a file when it emits no finding (this includes the
case where the rule was not applicable, e.g. `name-format` when `name` is
missing — documented as a deliberate simplification). A rule that emits only
INFO-level findings shows status **INFO**; a rule that emits an ERROR or WARNING
shows **NOT OK**.

## Relevant Files

Use these files to complete the task:

- `scripts/skill_validation.py` — the script being extended. Key existing pieces to reuse:
  - `Level` enum, `CheckResult`, `FileReport` dataclasses (lines 50-78) — reused as-is.
  - `LEVEL_STYLE` constant (lines 458-462) — reused for the Severity column color.
  - `print_file_report` / `print_summary` (lines 465-529) — patterns to mirror; not modified except call sites.
  - `main()` (lines 537-577) — argparse block and the per-file loop get the new flag wired in.
  - All 9 `check_*` functions (lines 168-416) — read to enumerate the 17 rule IDs and their severities; **not modified**.
- `tests/test_skill_validation.py` — existing suite; new test classes appended. Reuse the `sv` module handle, `_load`, `_rules`, `_skill_path`, and `SCRIPT` constant.
- `pyproject.toml` / PEP 723 header — no dependency changes (`rich`, `pyyaml` already present).
- `specs/` — destination for the spec copy; match the house style of existing files (e.g. `specs/hooks-update-with-team.md`).

## The 17 rules in the registry

| rule_id | level | title |
|---|---|---|
| `frontmatter-valid` | ERROR | YAML frontmatter is present and parseable |
| `name-exists` | ERROR | name field is present |
| `name-format` | ERROR | name is lowercase letters, numbers, and hyphens only |
| `name-length` | ERROR | name is within the 64-character limit |
| `name-matches-dir` | ERROR | name matches the skill's directory name |
| `desc-exists` | ERROR | description field is present |
| `desc-length` | ERROR | description is within the 1024-character limit |
| `desc-trigger` | WARNING | description states when to use the skill |
| `desc-vague` | WARNING | description avoids vague phrases without specifics |
| `allowed-tools` | WARNING | allowed-tools lists only known tools |
| `model-valid` | WARNING | model is one of sonnet/opus/haiku |
| `line-count` | WARNING | SKILL.md is within the 500-line recommendation |
| `progressive-disclosure` | WARNING | large skills use scripts/references/assets |
| `dir-conventions` | INFO | recommended scripts/references/assets dirs present |
| `body-instructions` | WARNING | body has step-by-step instructions |
| `body-examples` | WARNING | body has example code blocks |
| `backtick-bang` | ERROR | no backtick-bang patterns in fenced code blocks (#12781) |

## Implementation Phases

### Phase 1: Foundation

Add the `RuleSpec` dataclass and `RULE_REGISTRY` constant. Add the
registry-coverage meta-test first (TDD) so the registry is proven complete and
drift-proof before anything depends on it.

### Phase 2: Core Implementation

TDD the two pure data structures (`FileRuleRow`, `RuleOutcome`) and their two
builder functions (`build_file_rules_report`, `build_rules_report`): write
failing tests, then implement until green.

### Phase 3: Integration & Polish

Add the two `rich` display functions, wire `--rules-report` into `main()`,
add integration tests asserting exit codes are unchanged, then run lint + tests.

## New code design

```python
# --- Rule registry -------------------------------------------------------
@dataclasses.dataclass(frozen=True)
class RuleSpec:
    rule_id: str
    title: str
    level: Level

RULE_REGISTRY: tuple[RuleSpec, ...] = (
    RuleSpec("frontmatter-valid", "YAML frontmatter is present and parseable", Level.ERROR),
    # ... all 17 rows from the table above, in validation-flow order ...
)

# --- Status helper -------------------------------------------------------
# Three-state status: "OK" (no finding), "INFO" (INFO-only finding),
# "NOT OK" (ERROR/WARNING finding).
def rule_status(spec: RuleSpec, fired: bool) -> str:
    if not fired:
        return "OK"
    return "INFO" if spec.level is Level.INFO else "NOT OK"

# --- Per-file rows (pure) ------------------------------------------------
@dataclasses.dataclass
class FileRuleRow:
    spec: RuleSpec
    findings: list[CheckResult]          # CheckResults in this file for this rule

    @property
    def fired(self) -> bool:
        return bool(self.findings)

def build_file_rules_report(report: FileReport) -> list[FileRuleRow]:
    """For one file, one row per registry rule (pure, no I/O)."""
    return [
        FileRuleRow(spec, [r for r in report.results if r.rule == spec.rule_id])
        for spec in RULE_REGISTRY
    ]

# --- Aggregate outcomes (pure) -------------------------------------------
@dataclasses.dataclass
class RuleOutcome:
    spec: RuleSpec
    passing_files: list[Path]
    failing_files: list[Path]

    @property
    def ok(self) -> bool:
        return not self.failing_files

def build_rules_report(reports: list[FileReport]) -> list[RuleOutcome]:
    """One outcome per registry rule, partitioning files (pure, no I/O)."""
    outcomes: list[RuleOutcome] = []
    for spec in RULE_REGISTRY:
        passing: list[Path] = []
        failing: list[Path] = []
        for rep in reports:
            fired = any(r.rule == spec.rule_id for r in rep.results)
            (failing if fired else passing).append(rep.path)
        outcomes.append(RuleOutcome(spec, passing, failing))
    return outcomes
```

Display functions (`rich`, mirror `print_summary`'s style):

- `print_file_rules_report(report, rows)` — table titled `Rules — <relpath>`,
  columns **Rule / Severity / Status / Detail**; one row per rule; `Detail`
  shows the finding message(s) for non-OK rows, `—` otherwise.
- `print_rules_report(outcomes)` — table titled `Validation Rules Report`,
  columns **Rule / Severity / Status / Passed / Failed / Failing Files**;
  closes with a `Panel.fit` summary line (`N OK / N INFO / N NOT OK of 17 rules`).
- Severity column color: `LEVEL_STYLE[spec.level][0]`. Status color: green for
  OK, cyan for INFO, and `LEVEL_STYLE[spec.level][0]` (red/yellow) for NOT OK.

`main()` wiring:

```python
parser.add_argument(
    "--rules-report", action="store_true",
    help="Print an itemized per-rule report (per-file tables and an aggregate table)",
)
# ... in the per-file loop:
for skill_file in skill_files:
    report = validate_skill_file(skill_file)
    reports.append(report)
    print_file_report(report)
    if args.rules_report:
        print_file_rules_report(report, build_file_rules_report(report))
if args.rules_report:
    print_rules_report(build_rules_report(reports))
return print_summary(reports, strict=args.strict)
```

## Step by Step Tasks

IMPORTANT: Execute every step in order, top to bottom. This follows TDD —
write the failing test, then the implementation, then confirm green.

### 1. TDD: rule registry + drift guard

- In `tests/test_skill_validation.py`, add `TestRuleRegistry` with failing tests:
  - `RULE_REGISTRY` is non-empty and every entry is a `RuleSpec`.
  - All `rule_id`s are unique.
  - **Drift guard:** read `SCRIPT.read_text()`, regex-extract every literal from
    `CheckResult(\s*["']([a-z0-9-]+)["']`, and assert that set equals
    `{s.rule_id for s in sv.RULE_REGISTRY}` (both directions — no missing, no extra).
- Implement `RuleSpec` and `RULE_REGISTRY` (17 entries) in `skill_validation.py`.
- Run `uv run pytest -s tests/test_skill_validation.py -k RuleRegistry` -> green.

### 2. TDD: `build_file_rules_report`

- Add `TestBuildFileRulesReport`:
  - Clean `FileReport` (no results) -> 17 rows, all `fired is False`.
  - `FileReport` with a `CheckResult("name-matches-dir", ERROR, ...)` -> that row
    `fired is True` with the finding; all others `fired is False`.
  - Row order matches `RULE_REGISTRY` order.
- Implement `FileRuleRow` + `build_file_rules_report`.
- Run the new tests -> green.

### 3. TDD: `build_rules_report`

- Add `TestBuildRulesReport`:
  - Empty `reports` -> every outcome `ok is True`, empty passing/failing.
  - One failing file + one clean file for a rule -> `failing_files` has 1 path,
    `passing_files` has 1 path.
  - Multiple files, mixed -> counts correct per rule.
  - An INFO rule (`dir-conventions`) that fired -> outcome `ok is False`
    (status resolves to `INFO` at render time).
- Implement `RuleOutcome` + `build_rules_report`.
- Run the new tests -> green.

### 4. Implement display functions

- Add `rule_status`, `print_file_rules_report`, `print_rules_report` to
  `skill_validation.py`, reusing `LEVEL_STYLE`, `escape`, `Table`, `Panel`,
  `console`.
- Add `TestPrintRulesReport` smoke tests (mirror `TestPrintSummary`): patch
  `sv.console` with `mocker`, call each display function with built data,
  assert no exception and `console.print` was called.

### 5. Wire `--rules-report` into `main()`

- Add the `--rules-report` argparse argument.
- Add the conditional per-file and aggregate calls in the validation loop.
- Update the module docstring `Usage:` block to show the new flag.

### 6. TDD: `main()` integration

- Extend `TestMain`:
  - `test_rules_report_flag_returns_0` — valid skill + `--rules-report` -> `0`.
  - `test_rules_report_does_not_change_exit_code` — same fixture with and
    without `--rules-report` yields the same exit code (passing and failing).
  - `test_rules_report_with_strict` — `--rules-report --strict` still returns
    `1` on warnings.
- Confirm all pass.

### 7. Validate the whole change

- Run the full validation command set below; fix any lint/type/test issue.
- Confirm zero ruff / basedpyright warnings and all tests green.

## Testing Strategy

- **Unit (pure functions):** `build_file_rules_report` and `build_rules_report`
  are I/O-free and tested directly on hand-built `FileReport`/`CheckResult`
  objects — no `tmp_path`, no console.
- **Drift guard:** the registry meta-test statically proves `RULE_REGISTRY`
  matches every `CheckResult` literal in the source, so adding a future rule
  without registering it fails CI.
- **Display:** smoke-tested by patching `sv.console` (existing `TestPrintSummary`
  pattern) — assert no exceptions and that output was produced; no brittle
  string assertions on `rich` markup.
- **Integration:** `TestMain` confirms the flag runs end-to-end and, critically,
  that exit codes are identical with and without the flag (the feature is
  strictly additive).
- **Edge cases:** empty `reports` list; a rule that fired in some files but not
  others; an INFO-only rule (`dir-conventions`) firing; `--rules-report`
  combined with `--strict`.

## Acceptance Criteria

- `uv run scripts/skill_validation.py .claude/skills --rules-report` prints a
  per-file rule table for each `SKILL.md` and one aggregate `Validation Rules
  Report` table, then the existing summary.
- The aggregate table has one row per rule (17 rows), each showing severity,
  `OK`/`INFO`/`NOT OK` status, passed count, and failed count.
- Severity is color-highlighted: ERROR red, WARNING yellow, INFO cyan/dim.
- Running with vs. without `--rules-report` produces the **same exit code**.
- `--rules-report --strict` still fails (exit 1) on warnings.
- New test classes (`TestRuleRegistry`, `TestBuildFileRulesReport`,
  `TestBuildRulesReport`, `TestPrintRulesReport`, extended `TestMain`) all pass.
- `make lint` and `make test` pass with zero warnings/errors.

## Validation Commands

Execute these commands to validate the task is complete:

- `uv run python -m py_compile scripts/skill_validation.py` — script compiles.
- `uv run pytest -s tests/test_skill_validation.py` — full skill-validation suite passes.
- `uv run scripts/skill_validation.py .claude/skills --rules-report` — manual run shows per-file + aggregate rule tables.
- `uv run scripts/skill_validation.py .claude/skills --rules-report --strict` — flag combines with `--strict`; exit code unchanged vs. the non-`--rules-report` strict run.
- `uv run scripts/skill_validation.py plugins --rules-report` — exercises a multi-file run (aggregate counts > 1).
- `make lint` — ruff + basedpyright clean.
- `make test` — full repo test suite passes.

## Notes

- **No new dependencies** — `rich` and `pyyaml` are already in the PEP 723 header.
- The feature is strictly additive: no existing `check_*` function, data class,
  or output path is modified; `--rules-report` defaults off.
- Known simplification: a rule is "OK" for a file whenever it emits no finding,
  including when it was not applicable (e.g. `name-format` is skipped when
  `name` is absent). This is documented behavior, acceptable for a checklist view.
- The "Both" scope means per-file tables are printed for every `SKILL.md`;
  output is verbose on large trees by design — `--rules-report` is opt-in.
