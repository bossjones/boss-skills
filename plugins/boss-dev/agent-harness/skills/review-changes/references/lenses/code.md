# Lens: code

`theme: "code"`. Source code, build scripts, CI workflow files, and agent/skill definitions, in
whichever languages the target repo actually uses.

Run every gate in `quality-gates.md`. Return only the JSON in `observation-format.md`.

## Domain

Source files in any language, build and CI configuration, and agent-harness config
(`.claude/skills/**`, `.claude/agents/**` or equivalent for the tool in use).

**Not yours:** prose claims in docs about the code (`claims` verifies those), file placement
(`placement`).

## Universal defect classes

These apply regardless of language:

- a swallowed exception: an empty catch block, a caught error the caller needed, a bare
  `except:` in Python or an empty `catch {}` in JS/TS/Go/Rust equivalents
- **a change to a documented CLI/API/exit-code contract that CI gates on.** If a repo's own docs
  say "exit code 0 = clean, 1 = findings", changing what an exit code means breaks whatever CI
  workflow gates on it, silently — CRITICAL if the discovered rules or CI config confirm the
  contract is real
- a new CLI subcommand, flag, API endpoint, or output format shape with no test covering it
- output pollution on a machine-readable path — a `--quiet` / `--format json` mode that still
  writes extra text to stdout; these interfaces are often consumed by other programs or agents,
  and stray output is context pollution
- mutable default arguments (Python), a path built by string concatenation instead of the
  language's path-joining primitive, a file opened without an explicit encoding
- a CI or script step whose failure is swallowed (`continue-on-error` on a gate that should
  block, a trailing `|| true` that discards a real failure)
- a gate that reports success from a tool whose exit code does not reflect the actual result —
  some CLIs always exit 0 regardless of outcome, so a check gating on exit code alone silently
  passes; it must inspect actual output or stderr instead
- a script that assumes a tool is installed with no guard or error message

## The declared-entrypoints truth

The commands that actually exist are the ones the repo declares — `[project.scripts]` in
`pyproject.toml`, `bin`/`scripts` in `package.json`, `[[bin]]` in `Cargo.toml`,
`Makefile`/`justfile` targets. A doc, script, or skill body naming any other command as if it
exists is a finding — check the declared list, do not assume a command exists because it sounds
plausible.

## Per-language dispatch

Check what the diff's languages already have covering them (quality gate 8), then look past
that:

| Language | Style already owned by | Look past style for |
|---|---|---|
| Python | `black`/`ruff format`, `flake8`/`ruff check`, `mypy`/`pyright` if configured | swallowed exceptions, mutable defaults, missing encoding, untested new CLI surface |
| TypeScript/JavaScript | `eslint`/`biome`, `prettier` if configured | unhandled promise rejections, `any`-typed public API surface, untested new endpoint |
| Go | `gofmt`, `golangci-lint` if configured | ignored error returns (`_ = err`), goroutine leaks, untested new exported function |
| Rust | `rustfmt`, `clippy` if configured | `.unwrap()`/`.expect()` on a fallible path reachable from external input, untested new public API |
| Shell | `shellcheck` if configured | unquoted variable expansion on a path from untrusted input, missing `set -e`/`set -euo pipefail` on a script that should fail loudly |

## Skill and agent definitions

If the diff touches a skill, agent, or command definition for this or another agent harness,
mechanical frontmatter rules (quoting, required fields, casing) are usually enforced by a linter
or CI check — verify against quality gate 8 and do not re-report those. Report what a linter
cannot see:

- a `description` that will not trigger: no concrete user phrasings, or phrasings that collide
  with an existing skill's
- a `references/*.md` cited by **bare filename** with no arrangement to pass the absolute
  path — it resolves from nowhere and is silently never opened, while the agent still returns
  well-formed output. An invisible failure.
- `allowed-tools` (or the harness's equivalent) omitting a tool the skill body actually uses
- a skill body that instructs a write to an external system (a tracker, a wiki, a chat channel,
  a git host) with no confirmation step
- a `SKILL.md` (or equivalent) that references a workflow, CLI command, or file that does not
  exist

## Categories

`swallowed-error`, `missing-test`, `cli-contract`, `exit-code-contract`, `nonexistent-command`,
`skill-frontmatter`, `skill-description-quality`, `unresolvable-reference-path`,
`unconfirmed-outbound-write`, `meaningless-ci-gate`, `output-pollution`.

## Evidence bar

Name the reachable path: which caller, which input, which exit code. For a test gap, name the
untested branch precisely and say where you looked for a covering test — "needs more tests" is
not a finding.

## Do not report

Anything a discovered linter, formatter, or type checker already catches (quality gate 8).
Formatting, import order, line length. A missing test for code the diff did not add — that is a
pre-existing absence and the challenger will reject it. A preference for a different library or
file layout. Type hints on a codebase that is not fully typed.
