# Skill Validation

`scripts/skill_validation.py` checks `SKILL.md` files against the agent skills
open-standard best practices. It recursively finds every `SKILL.md` under a
directory (`Path.rglob("SKILL.md")`) and runs each one through a fixed set of
validation rules, then prints a per-file report and a summary table.

This doc explains **what every criterion is**, what triggers it, and at what
severity — so you can author a skill that passes without reading the source.

## Usage

```text
./scripts/skill_validation.py <directory>            # Normal mode
./scripts/skill_validation.py <directory> --strict   # Treat warnings as errors
```

The script is a PEP 723 `uv` script (`requires-python >=3.13`, depends on
`pyyaml` and `rich`) — `uv run` installs its dependencies automatically.

| Exit code | Meaning |
|-----------|---------|
| 0 | All checks passed — warnings are allowed in normal mode |
| 1 | One or more errors found, or any warning while `--strict` is set |
| 1 | The given path is not a directory |
| 0 | No `SKILL.md` files found (nothing to validate) |

## Severity levels

Every finding is a `CheckResult` at one of three levels. The level decides
both the exit code and the per-file `Status` in the summary table.

| Level | Icon | Affects exit code? | Summary status |
|-------|------|--------------------|----------------|
| `ERROR` | `[x]` | Always fails the run | `FAIL` |
| `WARNING` | `[!]` | Fails only under `--strict` | `WARN`, or `FAIL` under `--strict` |
| `INFO` | `[-]` | Never | does not change status |

A file with only `INFO` notes still reports `PASS`.

## Validation rules

The module docstring calls these "16 validation rules." In the code there are
**17 distinct rule IDs** — rule 2 below covers two IDs (`name-format` and
`name-length`), which is why the IDs outnumber the rule numbers.

| # | Rule ID | Level | Check function | Triggers when |
|---|---------|-------|----------------|---------------|
| 1 | `name-exists` | ERROR | `check_name` | the `name` field is missing |
| 2 | `name-format` | ERROR | `check_name` | `name` is not lowercase letters, numbers, and hyphens (`^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$`) |
| 2 | `name-length` | ERROR | `check_name` | `name` is longer than 64 characters |
| 3 | `name-matches-dir` | ERROR | `check_name` | `name` differs from the parent directory name |
| 4 | `desc-exists` | ERROR | `check_description` | the `description` field is missing |
| 5 | `desc-length` | ERROR | `check_description` | `description` is longer than 1024 characters |
| 6 | `desc-trigger` | WARNING | `check_description` | `description` contains no trigger phrase (`use when`, `trigger when`, `activate when`, `invoke when`, `use this`, `use for`, `use to`) |
| 7 | `allowed-tools` | WARNING | `check_optional_fields` | a tool listed in `allowed-tools` is neither a known tool nor an `mcp__*` tool |
| 8 | `model-valid` | WARNING | `check_optional_fields` | `model` is not one of `sonnet`, `opus`, `haiku` |
| 9 | `desc-vague` | WARNING | `check_description_quality` | `description` contains a vague phrase (`when needed`, `as appropriate`, `if necessary`, `as required`, `when applicable`) with fewer than 10 characters of specifics after it |
| 10 | `line-count` | WARNING | `check_structure` | the `SKILL.md` file exceeds 500 lines |
| 11 | `progressive-disclosure` | WARNING | `check_structure` | the file exceeds 500 lines **and** has no `scripts/`, `references/`, or `assets/` subdirectory |
| 12 | `dir-conventions` | INFO | `check_directory_conventions` | one note per missing optional subdirectory (`scripts/`, `references/`, `assets/`) |
| 13 | `body-instructions` | WARNING | `check_body_content` | the body has no numbered list and no `##`-or-deeper section header |
| 14 | `body-examples` | WARNING | `check_body_content` | the body has no fenced code block (no triple-backtick fence) |
| 15 | `backtick-bang` | ERROR | `check_backtick_bang` | a backtick-bang pattern appears inside a fenced code block (parser bug #12781) |
| 16 | `frontmatter-valid` | ERROR | `check_frontmatter_valid` | the YAML frontmatter is missing, unclosed, not a mapping, or unparseable |

### Why each group of checks matters

- **`check_name` (rules 1–3).** A skill's `name` is its identifier. It must be
  a clean slug and must equal the directory it lives in, because the loader
  resolves skills by directory. A mismatch means the skill won't load under
  the name you declared.
- **`check_description` (rules 4–6).** The `description` is what the model
  reads to decide whether to invoke the skill. A trigger phrase
  ("Use when…", "Use this to…") makes that decision reliable; without one the
  skill may never fire.
- **`check_optional_fields` (rules 7–8).** `allowed-tools` and `model` are
  optional, but a typo there silently changes behavior. Unknown tool names and
  invalid model names are flagged so they're caught before runtime.
- **`check_description_quality` (rule 9).** Vague phrases like "as appropriate"
  give the model nothing to match against. The check only fires when the
  phrase is *not* followed by concrete detail — "use as appropriate when the
  CSV has duplicate rows" passes, "use as appropriate" does not.
- **`check_structure` (rules 10–11).** A `SKILL.md` over 500 lines should push
  detail into `scripts/`, `references/`, or `assets/` (progressive
  disclosure) so the main file stays scannable.
- **`check_directory_conventions` (rule 12).** Purely informational — it lists
  the conventional subdirectories you have not created. It never fails a run.
- **`check_body_content` (rules 13–14).** A useful skill has step-by-step
  instructions (a numbered list or headers) and at least one example code
  block.
- **`check_backtick_bang` (rule 15).** Claude Code's skill parser executes
  backtick-bang patterns even inside fenced code blocks
  ([GitHub #12781](https://github.com/anthropics/claude-code/issues/12781)).
  Use `$ command` notation in examples instead.
- **`check_frontmatter_valid` (rule 16).** Everything else depends on readable
  frontmatter — see the note below.

## Frontmatter short-circuit behavior

Validation begins by parsing the YAML frontmatter delimited by `---` markers.
If parsing fails — no opening `---`, no closing `---`, not a YAML mapping, or a
YAML syntax error — `frontmatter-valid` reports an `ERROR` and **every
frontmatter-dependent check returns nothing**. Rules 1–9 are skipped because
there is no frontmatter to inspect. The structure, directory, body, and
backtick-bang checks (10–15) still run, since they read the file body and
directory rather than the frontmatter.

So a file with broken frontmatter shows one `frontmatter-valid` error plus any
body/structure findings — fix the frontmatter first, then re-run to surface
the rest.

## Worked example: broken vs. fixed `SKILL.md`

### A `SKILL.md` that fails

This file lives at `data-cleaner/SKILL.md` and trips eight rules at once:

````markdown
---
name: My_Bad_Skill
description: Use as appropriate.
model: gpt-4
allowed-tools: Read, Bash, FooTool
---

This skill cleans up messy data files. It removes duplicate rows,
trims whitespace, and normalizes column headers.

Run it against any CSV directory and it will rewrite the files in place.

```bash
clean-data ./input `!ls`
```
````

What's wrong:

- `name: My_Bad_Skill` — uppercase letters and an underscore break the slug
  format (`name-format`), and it doesn't match the `data-cleaner/` directory
  (`name-matches-dir`).
- `description: Use as appropriate.` — no trigger phrase (`desc-trigger`) and a
  vague phrase with no specifics after it (`desc-vague`).
- `model: gpt-4` — not a valid model (`model-valid`).
- `allowed-tools: Read, Bash, FooTool` — `FooTool` is not a known tool
  (`allowed-tools`).
- The body has prose only — no numbered list, no headers (`body-instructions`).
- The fenced block contains a backtick-bang pattern (`backtick-bang`).

Running the validator:

```text
╭─────────────────────────────────────────────────────────╮
│ Validating 1 SKILL.md file(s) under ./skills            │
╰─────────────────────────────────────────────────────────╯

  data-cleaner/SKILL.md
    [x] name-format: name 'My_Bad_Skill' must be lowercase letters, numbers, and hyphens only
    [x] name-matches-dir: name 'My_Bad_Skill' does not match directory 'data-cleaner'
    [!] desc-trigger: description should indicate when to use this skill (e.g. 'Use when...', 'Use this to...')
    [!] allowed-tools: unknown tool 'FooTool' in allowed-tools
    [!] model-valid: model 'gpt-4' not in ['haiku', 'opus', 'sonnet']
    [!] desc-vague: description contains vague phrase 'as appropriate' without specifics
    [-] dir-conventions: no scripts/ directory (optional)
    [-] dir-conventions: no references/ directory (optional)
    [-] dir-conventions: no assets/ directory (optional)
    [!] body-instructions: no step-by-step instructions found (numbered lists or section headers)
    [x] backtick-bang: backtick-bang pattern in fenced code block (parser bug #12781): clean-data ./input `!ls`

                       Skill Validation Summary
┏━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━┳━━━━━━┳━━━━━━━━┓
┃ File                   ┃ Errors ┃ Warnings ┃ Info ┃ Status ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━╇━━━━━━╇━━━━━━━━┩
│ data-cleaner/SKILL.md  │      3 │        5 │    3 │  FAIL  │
└────────────────────────┴────────┴──────────┴──────┴────────┘
╭───────────────────────────────────╮
│ FAILED — 3 error(s), 5 warning(s) │
╰───────────────────────────────────╯
```

The three errors are `name-format`, `name-matches-dir`, and `backtick-bang`
(the `[x]` lines). Exit code is `1`. Note that `body-examples` does **not**
fire — the file *does* have a fenced block; that same block is what triggers
`backtick-bang`. Delete the block entirely and `body-examples` would fire
instead.

### The same `SKILL.md`, fixed

Place this at `data-cleaner/SKILL.md` (directory name now matches `name`):

````markdown
---
name: data-cleaner
description: Use when cleaning messy CSV files — deduplicates rows, trims whitespace, and normalizes column headers across a directory of CSVs.
model: sonnet
allowed-tools: Read, Bash
---

# Data Cleaner

Cleans messy CSV files in place: deduplicates rows, trims whitespace,
and normalizes column headers.

## Steps

1. Point the skill at a directory of CSV files.
2. Review the proposed changes before applying them.
3. Apply the cleanup and re-run to confirm a clean pass.

## Example

```bash
$ clean-data ./input
```
````

Each fix maps to a rule:

- `name: data-cleaner` — valid slug, matches the directory.
- `description:` — opens with "Use when…" (trigger phrase) and is concrete, so
  neither `desc-trigger` nor `desc-vague` fires.
- `model: sonnet` — a valid model.
- `allowed-tools: Read, Bash` — both are known tools; `FooTool` removed.
- A `## Steps` section with a numbered list satisfies `body-instructions`.
- The example uses `$ clean-data ./input` instead of a backtick-bang pattern.

Running the validator:

```text
╭───────────────────────────────────────────────────────────────╮
│ Validating 1 SKILL.md file(s) under ./skills                  │
╰───────────────────────────────────────────────────────────────╯

  data-cleaner/SKILL.md
    [-] dir-conventions: no scripts/ directory (optional)
    [-] dir-conventions: no references/ directory (optional)
    [-] dir-conventions: no assets/ directory (optional)

                       Skill Validation Summary
┏━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━┳━━━━━━┳━━━━━━━━┓
┃ File                   ┃ Errors ┃ Warnings ┃ Info ┃ Status ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━╇━━━━━━╇━━━━━━━━┩
│ data-cleaner/SKILL.md  │      0 │        0 │    3 │  PASS  │
└────────────────────────┴────────┴──────────┴──────┴────────┘
╭───────────────────────────────────╮
│ PASSED — 0 error(s), 0 warning(s) │
╰───────────────────────────────────╯
```

The three `dir-conventions` notes remain — they are `INFO`, so the file still
reports `PASS` and the run exits `0`. To silence them, add `scripts/`,
`references/`, and `assets/` subdirectories (all optional).

## Constants reference

The thresholds and word lists driving the rules are module-level constants in
`scripts/skill_validation.py`:

| Constant | Value | Lines | Used by |
|----------|-------|-------|---------|
| `NAME_RE` | `^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$` | 84 | `name-format` |
| `MAX_NAME_LEN` | `64` | 85 | `name-length` |
| `MAX_DESC_LEN` | `1024` | 86 | `desc-length` |
| `MAX_LINES` | `500` | 87 | `line-count`, `progressive-disclosure` |
| `KNOWN_TOOLS` | `Bash`, `Read`, `Write`, `Edit`, `Glob`, `Grep`, `WebSearch`, `WebFetch`, `Agent`, `TodoRead`, `TodoWrite`, `NotebookEdit`, `TaskCreate`, `TaskUpdate`, `AskUserQuestion` | 89–105 | `allowed-tools` |
| `VALID_MODELS` | `sonnet`, `opus`, `haiku` | 107 | `model-valid` |
| `TRIGGER_KEYWORDS` | `use when`, `trigger when`, `activate when`, `invoke when`, `use this`, `use for`, `use to` | 109–117 | `desc-trigger` |
| `VAGUE_PHRASES` | `when needed`, `as appropriate`, `if necessary`, `as required`, `when applicable` | 119–125 | `desc-vague` |

Any tool name beginning with `mcp__` is accepted by `allowed-tools` even
though it is not in `KNOWN_TOOLS`.

## CI integration

In normal mode the script never fails on warnings, so a build can pass with
warnings outstanding. To gate a build on warnings too, run with `--strict`,
which makes every warning fail the run:

```text
./scripts/skill_validation.py .claude/skills --strict
```

Pair it with a non-zero exit-code check in your pipeline. The exit codes in
the [Usage](#usage) table are stable, so `&&`-chaining or a CI step that
inspects `$?` is enough — no special parsing of the report is needed.

## See also

- [`scripts.md`](scripts.md) — overview of every script in `scripts/`.
- [`eval-skills.md`](eval-skills.md) — the companion `plugin-eval` quality gate.
