"""Pytest configuration for agent-harness hook tests.

Mirrors the skill test suites under
``plugins/boss-dev/agent-harness/skills/*/scripts/tests/``: the sibling source
directory is placed on ``sys.path`` so the modules under test import without
packaging. Shared fixtures isolate the working directory (hooks write to
``./logs`` and ``./.claude/data``) and scrub LLM credentials from the env.
"""

from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).resolve().parent

# Put the tests dir on the path so test modules can ``from hook_loader import
# load_hook``. The hooks directory is deliberately NOT added globally — see
# hook_loader.load_hook, which adds/removes it per-load to avoid leaking a
# top-level ``utils`` package that would shadow other test suites.
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))


@pytest.fixture
def in_tmp_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Run the test with the current working directory set to an isolated tmp dir.

    Required for any hook that writes to ``./logs`` or ``./.claude/data`` (relative
    paths) and to ensure ``load_dotenv()`` finds no stray ``.env``.
    """
    monkeypatch.chdir(tmp_path)
    yield tmp_path


@pytest.fixture
def no_llm_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    """Scrub LLM API keys / engineer name so the real env can't leak into tests."""
    for var in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "ENGINEER_NAME", "OLLAMA_MODEL"):
        monkeypatch.delenv(var, raising=False)
