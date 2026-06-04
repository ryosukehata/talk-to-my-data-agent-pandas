import asyncio
from typing import Any

from utils.llm_client import (
    CompletionsProxy,
    CompletionTokenCompatibilityProxy,
)


class _RecordingCompletions:
    def __init__(self) -> None:
        self.kwargs: dict[str, Any] | None = None

    async def create(self, **kwargs: Any) -> str:
        self.kwargs = kwargs
        return "created"

    async def create_with_completion(self, **kwargs: Any) -> tuple[str, str]:
        self.kwargs = kwargs
        return "created", "raw"


def test_completions_proxy_rewrites_max_tokens_for_create() -> None:
    completions = _RecordingCompletions()
    proxy = CompletionsProxy(completions, tracker=None)

    result = asyncio.run(proxy.create(messages=[], model="model", max_tokens=128))

    assert result == "created"
    assert completions.kwargs is not None
    assert "max_tokens" not in completions.kwargs
    assert completions.kwargs["max_completion_tokens"] == 128


def test_completion_token_compatibility_proxy_rewrites_max_tokens() -> None:
    completions = _RecordingCompletions()
    proxy = CompletionTokenCompatibilityProxy(completions)

    result = asyncio.run(proxy.create(messages=[], model="model", max_tokens=128))

    assert result == "created"
    assert completions.kwargs is not None
    assert "max_tokens" not in completions.kwargs
    assert completions.kwargs["max_completion_tokens"] == 128
