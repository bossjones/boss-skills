# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Review factory eval suites + write-path hardening** (agent-harness v0.30.0), by @bossjones
  - `append_finding.py`: a stdlib PEP 723 CLI that is now the *only* sanctioned way a
    specialist records a finding. It validates the anchor against `manifest.json` at write
    time — a hallucinated line number is rejected before it lands, with the reason on
    stderr so the agent can self-correct — refuses roles not on the roster, and computes
    the terminal done-record's counts from the file rather than the agent's say-so.
  - Suite 1 (`eval/`): 10 hermetic tasks replaying canned diffs through the deterministic
    core — tiering, roster pruning, scoping, injection defense — spawning no review agents;
    mirrored as `test_fixtures_replay.py` in `make test`.
  - Suite 2 (`eval/defects/`): 7 seeded-defect fixtures (SQL/shell injection, missing
    authz, quadratic loop, stale CLAUDE.md, the GitHub #12781 backtick bug) plus the
    `clean-no-defects` control, graded by `check_findings.py` against `planted.json`.
  - `prepare_review.py --context-file`: replay a PR's untrusted body hermetically, so the
    injection defense is testable offline.

- **Review factory** (agent-harness v0.29.0) — a risk-tiered, multi-specialist code review
  pipeline modeled on Cloudflare's AI code review system, by @bossjones
  - `review-factory-core` skill: the deterministic engine shared by both execution arms.
    `prepare_review.py` acquires the diff, assesses risk (a security-sensitive path forces
    Full tier regardless of size), prunes specialists with nothing to review, scopes
    per-file patches, strips prompt-injection boundary tags from untrusted PR text, and
    records every valid `(file, side, line)` anchor. `validate_findings.py` rejects findings
    anchored to lines that do not exist in the diff, before the judge ever reads them.
    `score_run.py` reports cost, cache hit rate, and cost-per-finding *per specialist* — so
    roster decisions are arithmetic rather than taste.
  - Two competing arms in `.claude/skills/`, sharing that core and differing only in
    substrate: `review-factory-workflow` (Workflow-tool fan-out) and `review-factory-cmux`
    (visible cmux panes). The winner gets promoted; the loser gets deleted.
  - Severity is `critical`/`moderate`/`nit` end to end, reusing `pr-review`'s existing
    payload schema and validator unchanged. No agent posts to GitHub — the orchestrator
    does, and only after a human approves.

### Fixed
- `fetch-diff`: a diff's trailing newline was annotated as a phantom context line, inventing
  a line number one past the end of the last hunk — a valid-looking anchor for a review
  comment on a line that does not exist, by @bossjones

### Changed
- `fetch-diff`: new local `--base <ref>` mode (diff `HEAD` against its merge-base) sharing the
  same annotator as PR mode, so a `file:line` anchor means one thing regardless of source.
  Widened the generated-file filter (all common lock files, minified bundles, sourcemaps,
  `@generated` markers) while exempting database migrations, which must always reach a
  reviewer, by @bossjones
- `boss-cmux-team`: `spawn_team.py` gains `--no-exec` (spawn the team without `execvp`-ing a
  new orchestrator, which would hijack a caller's shell) and a per-role `command` override,
  since the default launch shape is pi's and `claude` does not share it, by @bossjones
- Rename `cmux`/`cmux-team` skills to `boss-cmux`/`boss-cmux-team` in agent-harness (v0.23.0) by @bossjones

### Added
- Add boss-cmux driver skill + generalized boss-cmux-team orchestration skill and /cmux-fresh, /cmux-spawn-team, /cmux-did-spawn commands to agent-harness (v0.21.0) by @bossjones
- Add 18 Matt Pocock skills and reference docs by @bossjones
- Backport fixes + cosmetic/structural alignment (v0.4.1) by @bossjones
- Add /autobuild command (v0.3.0) by @bossjones
- Add /fix-gh-pr-comments slash command by @bossjones
- Expand to plugin-component changes (v0.1.0) by @bossjones
- Introduce basedpyright-lsp at v0.1.0 (v0.1.0) by @bossjones
- Add --rules-report flag by @bossjones
- Add eval-llm-judge and eval-monte-carlo make targets by @bossjones
- Port nine skills into the agent-harness plugin (v0.2.0) by @bossjones
- Add eval-skills.py script and update Makefile for GitHub API integration by @bossjones
- Port ten skills into the agent-harness plugin by @bossjones
- Multi-command wrapper + full pytest suite by @bossjones
- Port skill + uv-run PostToolUse hooks by @bossjones
- Add plugin-eval skill quality gate by @bossjones
- Add Proxmox VE tooling for Claude Code by @bossjones
- Introduce python-dev plugin for enhanced Python development tooling by @bossjones
- Add /create-plugin slash command for scaffolding plugins by @bossjones
- Add Gemini configuration and code review styleguide by @bossjones
- Enhance .claude settings and add new commands for CI debugging by @bossjones
- Add agents, commands, hooks, output-styles, and status lines to agent-harness plugin by @bossjones
- Scaffold boss-dev/agent-harness plugin by @bossjones
- Add new agents for task management and validation by @bossjones
- Add Claude Code hooks system with notifications, TTS, and LLM utilities by @bossjones
- Add slash commands for tools listing, git status, planning, and Q&A by @bossjones
- Add team planning command, hook validators, and status line scripts by @bossjones
- Add skill validation script and scripts documentation by @bossjones
- Add slash commands, stop hook validators, docs, and ty config by @bossjones
- Introduce new output styles for enhanced response formatting by @bossjones
- Add Twitter/X authentication setup script for manual login and cookie extraction by @bossjones
- Enhance Makefile and add debug features to twitter-tools by @bossjones
- Add verify-structure targets to Makefile for validating marketplace structure and plugin manifests by @bossjones
- Revamp README and enhance twitter-tools skills with auto-download functionality and JSON output support by @bossjones
- Implement ensure_chromium_installed function and add error handling in screenshot_tweet.py for improved reliability by @bossjones
- Add test-plugins target to Makefile for local plugin testing with detailed instructions by @bossjones
- Add pre-commit hook to Makefile and enhance project metadata in pyproject.toml with author and license information by @bossjones
- Add twitter-media-downloader and twitter-to-reel skills for downloading and converting Twitter content to Instagram Reels by @bossjones
- Add conversion commands and Python script standards documentation by @bossjones
- Add initial project structure with configuration files and development documentation by @bossjones

### Changed
- Update USER_NAME to 'bossjones' across various files by @bossjones
- Improve type annotations and error handling in create_reel.py and screenshot_tweet.py for enhanced clarity and type safety by @bossjones
- Enhance type annotations in download.py and compose_video.py for improved clarity and type safety by @bossjones

### Fixed
- Align verify-structure validators with array/custom-path schema by @bossjones
- Address PR #10 review feedback by @bossjones
- Register plugin in marketplace and align naming by @bossjones
- Render the error icon in the validation report by @bossjones
- Rename validator scripts for consistency by @bossjones
- Update status line command to use version 10 script by @bossjones
- Update Python version requirement to >=3.13 in various scripts by @bossjones
- Update Python version requirements across various scripts by @bossjones
- Update Python version constraints in pyproject.toml and uv.lock by @bossjones
- Update Python version constraints in pyproject.toml and uv.lock by @bossjones
- Update Python version requirement in pyttsx3 TTS script by @bossjones

### Security
- Add agent-harness backport plan from aif-skills by @bossjones
- Add specs for ansible-dev, terraform, and security-validation plugins by @bossjones

### New Contributors
* @bossjones made their first contribution in [#17](https://github.com/bossjones/boss-skills/pull/17)

[unreleased]: https://github.com/bossjones/boss-skills/commits/HEAD

<!-- generated by git-cliff -->
