# Development

This guide covers setting up a local dev environment for working on the `boss-skills` repo itself.
To **install and use** the published plugins, see the [root README](README.md). To **add a new
plugin/skill**, see [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Setting Up uv

This project is set up to use [uv](https://docs.astral.sh/uv/) to manage Python and
dependencies. First, be sure you
[have uv installed](https://docs.astral.sh/uv/getting-started/installation/) — see
[`installation.md`](installation.md) for a quick cheat sheet.

Then [fork the bossjones/boss-skills
repo](https://github.com/bossjones/boss-skills/fork) (having your own
fork will make it easier to contribute) and
[clone it](https://docs.github.com/en/repositories/creating-and-managing-repositories/cloning-a-repository).

## Basic Developer Workflows

The `Makefile` simply offers shortcuts to `uv` commands for developer convenience.
(For clarity, GitHub Actions don't use the Makefile and just call `uv` directly.)

```shell
# First, install all dependencies and set up your virtual environment.
# This simply runs `uv sync --all-extras` to install all packages,
# including dev dependencies and optional dependencies.
make install

# Run uv sync, lint, and test (and also generate agent rules):
make

# Build wheel:
make build

# Linting:
make lint

# Run tests:
make test

# Delete all the build artifacts:
make clean

# Upgrade dependencies to compatible versions:
make upgrade

# To run tests by hand:
uv run pytest   # all tests
uv run pytest -s tests/test_some_file.py  # one test, showing outputs

# Build and install current dev executables, to let you use your dev copies
# as local tools:
uv tool install --editable .

# Dependency management directly with uv:
# Add a new dependency:
uv add package_name
# Add a development dependency:
uv add --dev package_name
# Update to latest compatible versions (including dependencies on git repos):
uv sync --upgrade
# Update a specific package:
uv lock --upgrade-package package_name
# Update dependencies on a package:
uv add package_name@latest

# Run a shell within the Python environment:
uv venv
source .venv/bin/activate
```

See [uv docs](https://docs.astral.sh/uv/) for details.

## Agent Rules

See [.cursor/rules](.cursor/rules) for agent rules.
These are written for [Cursor](https://www.cursor.com/) but are also used by other
agents because the Makefile will generate `CLAUDE.md` and `AGENTS.md` from the same
rules.

```shell
make agent-rules
```

## IDE setup

If you use VSCode or a fork like Cursor or Windsurf, you can install the following
extensions:

- [Python](https://marketplace.visualstudio.com/items?itemName=ms-python.python)

- [Based Pyright](https://marketplace.visualstudio.com/items?itemName=detachhead.basedpyright)
  for type checking. Note that this extension works with non-Microsoft VSCode forks like
  Cursor.

## Marketplace-specific checks

Beyond `make lint` and `make test`, this repo has targets for validating plugins and docs:

```shell
# Validate marketplace structure + every plugin manifest
make verify-structure

# Static quality scores for every skill (plugin-eval; never fails)
make eval
# The CI quality gate (fails below the threshold)
make eval-ci

# Lint and link-check Markdown
make markdown-lint
make link-check
```

## Documentation

- [Documentation index](docs/README.md) — everything under `docs/`
- [Contributing a plugin](CONTRIBUTING.md)
- [uv docs](https://docs.astral.sh/uv/) · [basedpyright docs](https://docs.basedpyright.com/latest/)
