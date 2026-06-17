# Makefile for easy development workflows.
# See development.md for docs.
# Note GitHub Actions call uv directly, not this Makefile.

.DEFAULT_GOAL := help

# Skill quality regression floor for `make eval-ci`. Baseline (2026-05-20,
# 12 skills, static depth): lowest are fetch-unresolved-comments 60.9,
# fetch-diff 61.3, proxmox-infra 62.3, add-review-comment 62.8; highest is
# release-notes-generator 82.1. min(observed) - 5 = 55.9, so the floor stays at
# 57 — it is never lowered below 57. Re-baseline with `make eval` and raise
# this when skills genuinely improve.
EVAL_THRESHOLD ?= 57

.PHONY: default install lint test check open-coverage upgrade build clean agent-rules help monkeytype-create monkeytype-apply autotype markdown-lint markdown-fix intelligent-lint intelligent-lint-dry-run link-check link-check-verbose pre-commit test-plugins verify-structure verify-structure-strict test-twitter-downloader test-twitter-reel test-agent-harness ci smoke smoke-debug smoke-help logs eval eval-ci eval-skill eval-certify eval-llm-judge eval-monte-carlo changelog changelog-preview

default: agent-rules install lint test ## Run agent-rules, install, lint, and test

.PHONY: install
install: ## Install dependencies with all extras
	@echo "🚀 Installing dependencies with all extras"
	@uv sync --all-extras

.PHONY: lint
lint: ## Run linting tools
	@echo "🚀 Running linting tools"
	@uv run python devtools/lint.py

.PHONY: pre-commit
pre-commit: ## Run pre-commit hooks on all files
	@echo "🚀 Running pre-commit hooks..."
	@if command -v pre-commit >/dev/null 2>&1; then \
		pre-commit run --all-files; \
	else \
		echo "⚠️  Warning: pre-commit not installed"; \
	fi

.PHONY: test
test: ## Run tests with pytest
	@echo "🚀 Running tests with pytest"
	@uv run pytest

.PHONY: check
check: ## Run type checking with ty
	@echo "🚀 Running type checking with ty"
	@uv run ty check

.PHONY: open-coverage
open-coverage: ## Open coverage HTML report in browser
	@open htmlcov/index.html

.PHONY: upgrade
upgrade: ## Upgrade all dependencies to latest versions
	@echo "🚀 Upgrading all dependencies to latest versions"
	@uv sync --upgrade --all-extras --dev

.PHONY: build
build: ## Build the package distribution
	@echo "🚀 Building package distribution"
	@uv build

.PHONY: agent-rules
agent-rules: CLAUDE.md AGENTS.md ## Generate CLAUDE.md and AGENTS.md from .cursor/rules

# Use .cursor/rules for sources of rules.
# Create Claude and Codex rules from these.
CLAUDE.md: .cursor/rules/general.mdc .cursor/rules/python.mdc
	@echo "🚀 Generating CLAUDE.md from .cursor/rules"
	@cat .cursor/rules/general.mdc .cursor/rules/python.mdc > CLAUDE.md

AGENTS.md: .cursor/rules/general.mdc .cursor/rules/python.mdc
	@echo "🚀 Generating AGENTS.md from .cursor/rules"
	@cat .cursor/rules/general.mdc .cursor/rules/python.mdc > AGENTS.md

.PHONY: monkeytype-create
monkeytype-create: ## Run tests with monkeytype tracing
	@echo "🚀 Running tests with monkeytype tracing"
	@uv run monkeytype run `uv run which pytest`

.PHONY: monkeytype-apply
monkeytype-apply: ## Apply monkeytype stubs to all modules
	@echo "🚀 Applying monkeytype stubs to all modules"
	@uv run monkeytype list-modules | xargs -n1 -I{} sh -c 'uv run monkeytype apply {}'

.PHONY: autotype
autotype: monkeytype-create monkeytype-apply ## Run monkeytype tracing and apply stubs

.PHONY: clean
clean: ## Remove build artifacts and cache directories
	@echo "🚀 Removing build artifacts and cache directories"
	@rm -rf dist/
	@rm -rf *.egg-info/
	@rm -rf .pytest_cache/
	@rm -rf .mypy_cache/
	@rm -rf .venv/
	@find . -type d -name "__pycache__" -exec rm -rf {} +

.PHONY: help
help: ## Show this help message
	@uv run python -c "import re; \
	[[print(f'\033[36m{m[0]:<20}\033[0m {m[1]}') for m in re.findall(r'^([a-zA-Z_-]+):.*?## (.*)$$', open(makefile).read(), re.M)] for makefile in ('$(MAKEFILE_LIST)').strip().split()]"

.PHONY: markdown-lint
markdown-lint: ## Lint Markdown files
	@echo "🚀 Linting Markdown files"
	@uv run rumdl check .

.PHONY: markdown-fix
markdown-fix: ## Fix Markdown files
	@echo "🚀 Fixing Markdown files"
	@uv run rumdl fmt .

.PHONY: intelligent-lint
intelligent-lint: ## Run intelligent markdown linting with AI agents
	@echo "🚀 Running intelligent markdown linting with AI agents"
	@uv run python ./scripts/intelligent-markdown-lint.py

.PHONY: intelligent-lint-dry-run
intelligent-lint-dry-run: ## Analyze markdown linting errors (no fixes)
	@echo "🚀 Analyzing markdown linting errors (no fixes)"
	@uv run python ./scripts/intelligent-markdown-lint.py --dry-run

# lychee scrapes github.com HTML unauthenticated by default, which rate-limits
# into spurious 404s. Passing a token makes lychee use the GitHub API instead.
# Falls back to `gh auth token`, then to empty (unauthenticated) if neither.
.PHONY: link-check
link-check: ## Check all links in markdown files using lychee
	@echo "🚀 Checking all links in markdown files using lychee"
	@GITHUB_TOKEN="$${GITHUB_TOKEN:-$$(gh auth token 2>/dev/null)}" lychee --config lychee.toml '**/*.md'

.PHONY: link-check-verbose
link-check-verbose: ## Check all links in markdown files with verbose output
	@echo "🚀 Checking all links in markdown files with verbose output"
	@GITHUB_TOKEN="$${GITHUB_TOKEN:-$$(gh auth token 2>/dev/null)}" lychee --config lychee.toml --verbose debug '**/*.md'

.PHONY: test-plugins
test-plugins: ## Test plugins locally using claude --plugin-dir (usage: make test-plugins PLUGIN_DIR=./plugins/social-media/twitter-tools)
	@if [ -z "$(PLUGIN_DIR)" ]; then \
		echo "🚀 Finding plugins in plugins/ directory..."; \
		plugin_dirs=$$(find plugins -type d -name ".claude-plugin" -exec dirname {} \; 2>/dev/null || true); \
		if [ -z "$$plugin_dirs" ]; then \
			echo "⚠️  No plugins found with .claude-plugin/plugin.json"; \
			echo "Available plugin directories:"; \
			find plugins -type d -mindepth 2 -maxdepth 2 2>/dev/null | head -10; \
			exit 1; \
		fi; \
		echo "Found plugins:"; \
		echo "$$plugin_dirs" | while read plugin_dir; do \
			echo "  - $$plugin_dir"; \
		done; \
		echo ""; \
		echo "To test a specific plugin, run:"; \
		echo "  claude --plugin-dir <plugin-directory>"; \
		echo ""; \
		echo "Example:"; \
		first_plugin=$$(echo "$$plugin_dirs" | head -1); \
		echo "  claude --plugin-dir $$first_plugin"; \
	else \
		if [ ! -d "$(PLUGIN_DIR)" ]; then \
			echo "❌ Error: Plugin directory '$(PLUGIN_DIR)' does not exist"; \
			exit 1; \
		fi; \
		if [ ! -f "$(PLUGIN_DIR)/.claude-plugin/plugin.json" ]; then \
			echo "⚠️  Warning: No .claude-plugin/plugin.json found in '$(PLUGIN_DIR)'"; \
			echo "The plugin may still work if it has the correct structure."; \
		fi; \
		echo "🚀 Starting Claude Code with plugin: $(PLUGIN_DIR)"; \
		echo "Run '/help' in Claude Code to see your plugin commands."; \
		echo "Press Ctrl+C to exit."; \
		echo ""; \
		claude --plugin-dir "$(PLUGIN_DIR)"; \
	fi

.PHONY: verify-structure
verify-structure: ## Verify Claude Code marketplace structure and validate plugin manifests
	@echo "🚀 Verifying marketplace structure and plugin manifests"
	@uv run scripts/verify-structure.py

.PHONY: verify-structure-strict
verify-structure-strict: ## Verify marketplace structure in strict mode (warnings treated as errors)
	@echo "🚀 Verifying marketplace structure in strict mode"
	@uv run scripts/verify-structure.py --strict

.PHONY: eval
eval: ## Score all skills with plugin-eval (static depth, report only, never fails)
	@echo "🚀 Scoring skills with plugin-eval (quick depth)"
	@./scripts/eval-skills.py

.PHONY: eval-ci
eval-ci: ## Quality gate: fail if any skill scores below EVAL_THRESHOLD
	@echo "🚀 Quality gate: skills must score >= $(EVAL_THRESHOLD)"
	@./scripts/eval-skills.py --threshold $(EVAL_THRESHOLD)

.PHONY: eval-skill
eval-skill: ## Deep-dive one skill at standard depth (usage: make eval-skill SKILL=plugins/.../foo)
	@if [ -z "$(SKILL)" ]; then \
		echo "❌ Set SKILL=<path>, e.g. make eval-skill SKILL=plugins/social-media/twitter-tools/skills/twitter-to-reel"; \
		exit 1; \
	fi
	@echo "🚀 Evaluating $(SKILL) at standard depth (uses Claude Code Max via claude-agent-sdk)"
	@uvx --from "plugin-eval[llm] @ git+https://github.com/wshobson/agents.git#subdirectory=plugins/plugin-eval" \
		plugin-eval score "$(SKILL)" --depth standard --output markdown

.PHONY: eval-certify
eval-certify: ## Full certification (deep, badge) for one skill (usage: make eval-certify SKILL=plugins/.../foo)
	@if [ -z "$(SKILL)" ]; then \
		echo "❌ Set SKILL=<path>, e.g. make eval-certify SKILL=plugins/boss-dev/agent-harness/skills/git-worktree"; \
		exit 1; \
	fi
	@echo "🚀 Certifying $(SKILL) at deep depth (~15-20 min, uses Claude Code Max via claude-agent-sdk)"
	@./scripts/eval-skills.py --command certify "$(SKILL)"

.PHONY: eval-llm-judge
eval-llm-judge: ## LLM-judge eval all skills, or one with SKILL=<path> (~30s + 4 LLM calls per skill)
	@if [ -n "$(SKILL)" ]; then \
		echo "🚀 LLM-judge evaluating $(SKILL) (uses Claude Code Max via claude-agent-sdk)"; \
		./scripts/eval-skills.py --skill "$(SKILL)" --layer llm-judge; \
	else \
		echo "🚀 LLM-judge evaluating all skills at llm-judge layer (~30s + 4 LLM calls each)"; \
		./scripts/eval-skills.py --layer llm-judge; \
	fi

.PHONY: eval-monte-carlo
eval-monte-carlo: ## Monte-carlo eval all skills, or one with SKILL=<path> (~2-5 min per skill)
	@if [ -n "$(SKILL)" ]; then \
		echo "🚀 Monte-carlo evaluating $(SKILL) (uses Claude Code Max via claude-agent-sdk)"; \
		./scripts/eval-skills.py --skill "$(SKILL)" --layer monte-carlo; \
	else \
		echo "🚀 Monte-carlo evaluating all skills at monte-carlo layer (~2-5 min each)"; \
		./scripts/eval-skills.py --layer monte-carlo; \
	fi

.PHONY: test-twitter-downloader
test-twitter-downloader: ## Run twitter-media-downloader tests
	@echo "🚀 Running twitter-media-downloader tests"
	@uv run pytest plugins/social-media/twitter-tools/skills/twitter-media-downloader/scripts/tests/ -v

.PHONY: test-twitter-reel
test-twitter-reel: ## Run twitter-to-reel tests
	@echo "🚀 Running twitter-to-reel tests"
	@uv run pytest plugins/social-media/twitter-tools/skills/twitter-to-reel/scripts/tests/ -v

.PHONY: test-agent-harness
test-agent-harness: ## Run agent-harness tests (skills + hooks)
	@echo "🚀 Running agent-harness tests"
	@uv run pytest plugins/boss-dev/agent-harness/ -v

.PHONY: test-scripts
test-scripts: ## Run the root tests/ suite (scripts + hooks)
	@echo "🚀 Running tests/ suite"
	@uv run pytest tests/ -v

.PHONY: ci
ci: test-scripts test-twitter-downloader test-twitter-reel test-agent-harness ## Run all repo tests (CI target)

# Default test tweet URL (a public tweet with video)
SMOKE_URL ?= https://x.com/KameronBennett/status/2008195824304672928

.PHONY: smoke
smoke: ## Run smoke test - create a reel from a test tweet
	@echo "🚀 Running twitter-to-reel smoke test"
	cd plugins/social-media/twitter-tools/skills/twitter-to-reel && uv run scripts/create_reel.py "$(SMOKE_URL)" --browser firefox -o reel.mp4

.PHONY: smoke-debug
smoke-debug: ## Run smoke test with debug output for troubleshooting
	@echo "🚀 Running twitter-to-reel smoke test (debug mode)"
	cd plugins/social-media/twitter-tools/skills/twitter-to-reel && uv run scripts/create_reel.py "$(SMOKE_URL)" --browser firefox --debug -o reel.mp4

.PHONY: smoke-help
smoke-help: ## Show smoke test usage
	@echo "Usage: make smoke [SMOKE_URL=<url>]"
	@echo "       make smoke-debug [SMOKE_URL=<url>]  # with verbose debug output"
	@echo ""
	@echo "Examples:"
	@echo "  make smoke"
	@echo "  make smoke-debug"
	@echo "  make smoke SMOKE_URL='https://x.com/user/status/123'"

.PHONY: logs
logs: ## Tail logs/*.json and show notification_type and message via jq
	tail -f logs/*.json | ccze -A

# git-cliff resolves PR numbers / @usernames / first-time contributors via the
# GitHub API; pass a token (env, then `gh auth token`) to avoid rate limits.
.PHONY: changelog
changelog: ## Generate/refresh CHANGELOG.md (Keep a Changelog) using git-cliff
	@echo "🚀 Generating CHANGELOG.md with git-cliff"
	@if command -v git-cliff >/dev/null 2>&1; then \
		GITHUB_TOKEN="$${GITHUB_TOKEN:-$$(gh auth token 2>/dev/null)}" git-cliff --output CHANGELOG.md; \
	else \
		echo "⚠️  git-cliff not installed. Install: brew install git-cliff"; \
		exit 1; \
	fi

.PHONY: changelog-preview
changelog-preview: ## Preview the unreleased changelog section (stdout only, no write)
	@if command -v git-cliff >/dev/null 2>&1; then \
		GITHUB_TOKEN="$${GITHUB_TOKEN:-$$(gh auth token 2>/dev/null)}" git-cliff --unreleased; \
	else \
		echo "⚠️  git-cliff not installed. Install: brew install git-cliff"; \
		exit 1; \
	fi
