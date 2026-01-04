# Makefile for easy development workflows.
# See development.md for docs.
# Note GitHub Actions call uv directly, not this Makefile.

.DEFAULT_GOAL := help

.PHONY: default install lint test check open-coverage upgrade build clean agent-rules help monkeytype-create monkeytype-apply autotype locust locust-ui serve serve-otel otel-deps markdown-lint markdown-fix intelligent-lint intelligent-lint-dry-run link-check link-check-verbose

default: agent-rules install lint test ## Run agent-rules, install, lint, and test

.PHONY: install
install: ## Install dependencies with all extras
	@echo "🚀 Installing dependencies with all extras"
	@uv sync --all-extras

.PHONY: lint
lint: ## Run linting tools
	@echo "🚀 Running linting tools"
	@uv run python devtools/lint.py

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
	@rm -rf CLAUDE.md AGENTS.md
	@find . -type d -name "__pycache__" -exec rm -rf {} +

.PHONY: help
help: ## Show this help message
	@uv run python -c "import re; \
	[[print(f'\033[36m{m[0]:<20}\033[0m {m[1]}') for m in re.findall(r'^([a-zA-Z_-]+):.*?## (.*)$$', open(makefile).read(), re.M)] for makefile in ('$(MAKEFILE_LIST)').strip().split()]"

claude-skills: ## Install Claude skills
	@echo "🚀 Installing Claude skills"
	@npx skills-installer install @SlanyCukr/riot-api-project/uvicorn --local --client claude-code
	@npx skills-installer install @SlanyCukr/riot-api-project/sqlalchemy --local --client claude-code
	@npx skills-installer install @SlanyCukr/riot-api-project/pytest --local --client claude-code
	@npx skills-installer install @SlanyCukr/riot-api-project/pydantic --local --client claude-code
	@npx skills-installer install @SlanyCukr/riot-api-project/httpx --local --client claude-code
	@npx skills-installer install @SlanyCukr/riot-api-project/fastapi --local --client claude-code
	@npx skills-installer install @SlanyCukr/riot-api-project/apscheduler --local --client claude-code
	@npx skills-installer install @SlanyCukr/riot-api-project/alembic --local --client claude-code
	@npx claude-plugins install @JosiahSiegel/claude-plugin-marketplace/python-master

.PHONY: locust
locust: ## Run Locust load tests (headless mode). Usage: make locust [USERS=10] [SPAWN_RATE=1] [HOST=http://localhost:5002]
	@echo "🚀 Running Locust load tests"
	@uv run locust -f locustfile.py --headless \
		--users $(or $(USERS),10) \
		--spawn-rate $(or $(SPAWN_RATE),1) \
		-H $(or $(HOST),http://localhost:5002)

.PHONY: locust-ui
locust-ui: ## Run Locust with web UI. Usage: make locust-ui [HOST=http://localhost:5002]
	@echo "🚀 Running Locust with web UI"
	@uv run locust -f locustfile.py -H $(or $(HOST),http://localhost:5002)

.PHONY: serve
serve: ## Start the FastAPI server. Usage: make serve [PORT=5002] [RELOAD=--reload]
	@echo "🚀 Starting FastAPI server"
	@uv run uvicorn logging_lab.app:app --host 0.0.0.0 --port $(or $(PORT),5002) $(RELOAD)

.PHONY: serve-otel
serve-otel: ## Start the FastAPI server with OpenTelemetry instrumentation. Usage: make serve-otel [PORT=5002] [RELOAD=--reload]
	@echo "🚀 Starting FastAPI server with OpenTelemetry instrumentation"
	@uv run opentelemetry-instrument uvicorn logging_lab.app:app --host 0.0.0.0 --port $(or $(PORT),5002) $(RELOAD)

.PHONY: otel-deps
otel-deps: ## List required OpenTelemetry dependencies
	@echo "🚀 Listing required OpenTelemetry dependencies"
	@uv run opentelemetry-bootstrap -a requirements

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

.PHONY: link-check
link-check: ## Check all links in markdown files using lychee
	@echo "🚀 Checking all links in markdown files using lychee"
	@lychee --config lychee.toml '**/*.md'

.PHONY: link-check-verbose
link-check-verbose: ## Check all links in markdown files with verbose output
	@echo "🚀 Checking all links in markdown files with verbose output"
	@lychee --config lychee.toml --verbose debug '**/*.md'
