"""Tests for the LLM utility no-credential fallback paths.

These verify the graceful-degradation contract that the hooks rely on when no
API key (or no local model) is available: prompting returns ``None`` and name
generation falls back to a built-in random name. The real SDKs are never
exercised — every code path here short-circuits before a network call.
"""

from __future__ import annotations

import pytest
from hook_loader import load_hook

anth = load_hook("utils/llm/anth.py")
oai = load_hook("utils/llm/oai.py")
ollama = load_hook("utils/llm/ollama.py")
task_summarizer = load_hook("utils/llm/task_summarizer.py")

pytestmark = pytest.mark.usefixtures("in_tmp_cwd", "no_llm_keys")


class TestApiKeyGatedProviders:
    """anth.py and oai.py both short-circuit when their API key is unset."""

    @pytest.mark.parametrize("mod", [anth, oai])
    def test_prompt_llm_returns_none_without_key(self, mod: object) -> None:
        assert mod.prompt_llm("hello") is None

    @pytest.mark.parametrize("mod", [anth, oai])
    def test_completion_message_is_none_without_key(self, mod: object) -> None:
        assert mod.generate_completion_message() is None

    @pytest.mark.parametrize("mod", [anth, oai])
    def test_agent_name_falls_back_to_random(self, mod: object) -> None:
        name = mod.generate_agent_name()
        assert isinstance(name, str)
        assert name.isalpha()
        assert len(name) >= 3


class TestOllamaFallback:
    """ollama.py has no API key; it fails closed when no local model responds."""

    def test_prompt_llm_returns_none_when_unreachable(self, capsys: pytest.CaptureFixture[str]) -> None:
        assert ollama.prompt_llm("hello") is None
        capsys.readouterr()  # drain the diagnostic traceback it prints on failure

    def test_agent_name_falls_back_to_random(self, capsys: pytest.CaptureFixture[str]) -> None:
        name = ollama.generate_agent_name()
        capsys.readouterr()
        assert isinstance(name, str)
        assert name.isalpha()
        assert len(name) >= 3


class TestTaskSummarizer:
    def test_returns_default_summary_without_key(self) -> None:
        result = task_summarizer.summarize_subagent_task("Built the auth system")
        assert result == "Subagent task completed"

    def test_default_summary_ignores_agent_name(self) -> None:
        result = task_summarizer.summarize_subagent_task("Built the auth system", agent_name="builder")
        assert result == "Subagent task completed"
