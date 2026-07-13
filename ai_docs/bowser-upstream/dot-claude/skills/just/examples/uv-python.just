# Astral UV + Python Justfile Example

# Use uv for running recipes
set script-interpreter := ['uv', 'run', '--script']

# List all recipes
default:
  @just --list

# Sync dependencies (creates venv and installs deps)
sync:
  uv sync

# Run the main application
run:
  uv run main.py

# Run tests
test:
  uv run pytest

# Add a dependency
add package:
  uv add {{package}}

# Run a Python script with inline metadata (PEP 723)
# This recipe will automatically manage its own dependencies!
[doc("Run a script with its own isolated dependencies")]
isolated-task:
  #!/usr/bin/env uv run
  # /// script
  # requires-python = ">=3.11"
  # dependencies = ["requests", "rich"]
  # ///
  import requests
  from rich import print
  
  print("[bold blue]Fetching data with isolated dependencies...[/bold blue]")
  r = requests.get("https://api.github.com/repos/casey/just")
  print(f"Just has {r.json()['stargazers_count']} stars!")
