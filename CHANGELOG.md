# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
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
