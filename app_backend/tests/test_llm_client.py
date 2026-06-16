import asyncio
from types import SimpleNamespace
from typing import Any

import pytest
from core import llm_client
from utils.llm_client import (
    AsyncLLMClient,
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


class _RecordingTracker:
    def __init__(self) -> None:
        self.calls: list[tuple[list[Any], Any, str]] = []

    def track_call(self, messages: list[Any], response: Any, model: str) -> None:
        self.calls.append((messages, response, model))


class _FakeInstructorClient:
    def __init__(self, completions: _RecordingCompletions) -> None:
        self.chat = SimpleNamespace(completions=completions)


class _FakeOpenAIClient:
    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs
        self.chat = SimpleNamespace(completions=_RecordingCompletions())
        self.closed = False

    async def close(self) -> None:
        self.closed = True


class _FakeDataRobotClient:
    token = "dr-token"


def _clear_llm_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for env_name in (
        "DATAROBOT_API_TOKEN",
        "DATAROBOT_ENDPOINT",
        "LLM_DEPLOYMENT_ID",
        "LLM_DEFAULT_MODEL",
        "TEXTGEN_DEPLOYMENT_ID",
        "USE_DATAROBOT_LLM_GATEWAY",
    ):
        monkeypatch.delenv(env_name, raising=False)


def test_completions_proxy_rewrites_max_tokens_for_create() -> None:
    completions = _RecordingCompletions()
    proxy = CompletionsProxy(completions, tracker=None)

    result = asyncio.run(proxy.create(messages=[], model="model", max_tokens=128))

    assert result == "created"
    assert completions.kwargs is not None
    assert "max_tokens" not in completions.kwargs
    assert completions.kwargs["max_completion_tokens"] == 128


def test_completions_proxy_tracks_tokens_for_create_with_completion() -> None:
    completions = _RecordingCompletions()
    tracker = _RecordingTracker()
    proxy = CompletionsProxy(completions, tracker=tracker)  # type: ignore[arg-type]
    messages = [{"role": "user", "content": "hello"}]

    result, raw = asyncio.run(
        proxy.create_with_completion(
            messages=messages,
            model="model",
            max_tokens=128,
            timeout=12,
        )
    )

    assert (result, raw) == ("created", "raw")
    assert completions.kwargs is not None
    assert completions.kwargs["timeout"] == 12
    assert completions.kwargs["max_completion_tokens"] == 128
    assert tracker.calls == [(messages, "created", "model")]


def test_completion_token_compatibility_proxy_rewrites_max_tokens() -> None:
    completions = _RecordingCompletions()
    proxy = CompletionTokenCompatibilityProxy(completions)

    result = asyncio.run(proxy.create(messages=[], model="model", max_tokens=128))

    assert result == "created"
    assert completions.kwargs is not None
    assert "max_tokens" not in completions.kwargs
    assert completions.kwargs["max_completion_tokens"] == 128


def test_llm_client_config_prefers_gateway_default_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("USE_DATAROBOT_LLM_GATEWAY", "true")
    monkeypatch.setenv(
        "LLM_DEFAULT_MODEL",
        "datarobot/bedrock/anthropic.claude-sonnet-4-5-20250929-v1:0",
    )

    config = llm_client.LLMClientConfig.from_env()

    assert config.use_datarobot_llm_gateway is True
    assert config.default_model == (
        "datarobot/bedrock/anthropic.claude-sonnet-4-5-20250929-v1:0"
    )
    assert config.should_use_litellm is True


def test_async_llm_client_preserves_legacy_openai_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_llm_env(monkeypatch)
    created_clients: list[_FakeOpenAIClient] = []

    def fake_openai_client(**kwargs: Any) -> _FakeOpenAIClient:
        client = _FakeOpenAIClient(**kwargs)
        created_clients.append(client)
        return client

    monkeypatch.setattr(llm_client, "AsyncOpenAI", fake_openai_client)
    monkeypatch.setattr(
        llm_client.instructor,
        "from_openai",
        lambda *_args, **_kwargs: _FakeInstructorClient(_RecordingCompletions()),
    )

    async def run_client() -> None:
        async with AsyncLLMClient(
            dr_client=_FakeDataRobotClient(),
            deployment_base_url="https://example.test/deployments/abc/chat/completions",
        ):
            pass

    asyncio.run(run_client())

    assert created_clients[0].kwargs["timeout"] == 180
    assert created_clients[0].kwargs["max_retries"] == 2
    assert created_clients[0].closed is True


def test_async_llm_client_uses_litellm_gateway_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("USE_DATAROBOT_LLM_GATEWAY", "true")
    monkeypatch.setenv("LLM_DEFAULT_MODEL", "datarobot/bedrock/test-model")
    completions = _RecordingCompletions()
    litellm_calls: dict[str, Any] = {}

    async def fake_acompletion(**_kwargs: Any) -> Any:
        return "raw"

    def fake_patch(*_args: Any, **kwargs: Any) -> Any:
        litellm_calls["completion_fn"] = kwargs["create"]
        litellm_calls["kwargs"] = kwargs
        return completions.create

    monkeypatch.setattr(
        llm_client,
        "litellm",
        SimpleNamespace(acompletion=fake_acompletion),
        raising=False,
    )
    monkeypatch.setattr(
        llm_client.instructor,
        "patch",
        fake_patch,
    )
    monkeypatch.setattr(
        llm_client.instructor,
        "from_litellm",
        lambda *_args, **_kwargs: pytest.fail("from_litellm should not be used"),
        raising=False,
    )
    monkeypatch.setattr(
        llm_client.instructor,
        "from_openai",
        lambda *_args, **_kwargs: pytest.fail("OpenAI client should not be used"),
    )

    async def run_client() -> str:
        async with AsyncLLMClient(
            dr_client=_FakeDataRobotClient(),
            deployment_base_url="https://legacy.example.test/chat/completions",
        ) as client:
            return await client.chat.completions.create(
                messages=[],
                model="datarobot-deployed-llm",
                max_tokens=128,
                response_model=object,
            )

    result = asyncio.run(run_client())

    assert result == "created"
    assert litellm_calls["completion_fn"] is llm_client.litellm.acompletion
    assert litellm_calls["kwargs"]["mode"] is llm_client.instructor.Mode.MD_JSON
    assert completions.kwargs is not None
    assert completions.kwargs["model"] == "datarobot/bedrock/test-model"
    assert completions.kwargs["timeout"] == 180
    assert completions.kwargs["max_retries"] == 2
    assert "max_tokens" not in completions.kwargs
    assert completions.kwargs["max_completion_tokens"] == 128
    assert "api_base" not in completions.kwargs


def test_async_llm_client_litellm_create_with_completion_uses_async_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("USE_DATAROBOT_LLM_GATEWAY", "true")
    monkeypatch.setenv("LLM_DEFAULT_MODEL", "datarobot/bedrock/test-model")
    captured: dict[str, Any] = {}
    raw_response = object()
    structured_response = SimpleNamespace(_raw_response=raw_response)

    async def fake_acompletion(**kwargs: Any) -> Any:
        captured["acompletion_kwargs"] = kwargs
        return raw_response

    async def fake_create_fn(**kwargs: Any) -> Any:
        captured["create_fn_kwargs"] = kwargs
        return structured_response

    def fake_patch(*_args: Any, **kwargs: Any) -> Any:
        captured["patched_create"] = kwargs["create"]
        captured["patched_mode"] = kwargs["mode"]
        return fake_create_fn

    monkeypatch.setattr(
        llm_client,
        "litellm",
        SimpleNamespace(acompletion=fake_acompletion),
        raising=False,
    )
    monkeypatch.setattr(llm_client.instructor, "patch", fake_patch)
    monkeypatch.setattr(
        llm_client.instructor,
        "from_litellm",
        lambda *_args, **_kwargs: pytest.fail(
            "from_litellm treats coroutine functions as a sync client in instructor 1.3.4"
        ),
        raising=False,
    )

    async def run_client() -> tuple[Any, Any]:
        async with llm_client.AsyncLLMClient(
            dr_client=_FakeDataRobotClient(),
            deployment_base_url="https://legacy.example.test/chat/completions",
        ) as client:
            return await client.chat.completions.create_with_completion(
                messages=[],
                model="datarobot-deployed-llm",
                response_model=object,
            )

    response, raw = asyncio.run(run_client())

    assert response is structured_response
    assert raw is raw_response
    assert captured["patched_create"] is fake_acompletion
    assert captured["patched_mode"] is llm_client.instructor.Mode.MD_JSON
    assert captured["create_fn_kwargs"]["model"] == "datarobot/bedrock/test-model"
    assert captured["create_fn_kwargs"]["timeout"] == 180
    assert captured["create_fn_kwargs"]["max_retries"] == 2


def test_async_llm_client_injects_deployed_llm_api_base(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("DATAROBOT_ENDPOINT", "https://app.datarobot.example/api/v2")
    monkeypatch.setenv("TEXTGEN_DEPLOYMENT_ID", "deployment-123")
    monkeypatch.setenv("LLM_DEFAULT_MODEL", "datarobot/datarobot-deployed-llm")
    completions = _RecordingCompletions()

    async def fake_acompletion(**_kwargs: Any) -> Any:
        return "raw"

    def fake_patch(*_args: Any, **kwargs: Any) -> Any:
        assert kwargs["create"] is llm_client.litellm.acompletion
        assert kwargs["mode"] is llm_client.instructor.Mode.MD_JSON
        return completions.create

    monkeypatch.setattr(
        llm_client,
        "litellm",
        SimpleNamespace(acompletion=fake_acompletion),
        raising=False,
    )
    monkeypatch.setattr(
        llm_client.instructor,
        "patch",
        fake_patch,
    )
    monkeypatch.setattr(
        llm_client.instructor,
        "from_litellm",
        lambda *_args, **_kwargs: pytest.fail("from_litellm should not be used"),
        raising=False,
    )

    async def run_client() -> str:
        async with AsyncLLMClient(
            dr_client=_FakeDataRobotClient(),
            deployment_base_url="https://legacy.example.test/chat/completions",
        ) as client:
            return await client.chat.completions.create(
                messages=[],
                model="datarobot-deployed-llm",
                timeout=45,
                response_model=object,
            )

    result = asyncio.run(run_client())

    assert result == "created"
    assert completions.kwargs is not None
    assert completions.kwargs["api_base"] == (
        "https://app.datarobot.example/api/v2/deployments/"
        "deployment-123/chat/completions"
    )
    assert completions.kwargs["model"] == "datarobot/datarobot-deployed-llm"
    assert completions.kwargs["timeout"] == 45
