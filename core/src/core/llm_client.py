# Copyright 2025 DataRobot, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from __future__ import annotations

import asyncio
import json
import logging
import os
from collections.abc import Mapping
from dataclasses import dataclass, replace
from types import TracebackType
from typing import Any, Type

import httpx
import instructor
from datarobot_genai.core.utils.token_tracking import TokenUsageTracker
from openai import (
    APIConnectionError,
    APIError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    InternalServerError,
    NotFoundError,
    RateLimitError,
)
from opentelemetry import trace

from core.config import Config
from core.constants import get_llm_model

try:
    import litellm
except ImportError:  # pragma: no cover - exercised only when dependency is absent
    litellm = None  # type: ignore[assignment]


_TRUE_ENV_VALUES = {"1", "true", "yes", "y", "on"}
_MODEL_ALIASES_FOR_CONFIG_DEFAULT = {
    "custom-model",
    "datarobot-deployed-llm",
    "unknown",
    "",
}
_DEFAULT_REQUEST_TIMEOUT_SECONDS = 900.0
_DEFAULT_MAX_RETRIES = 2
_CAPTURE_CONTENT_ENV = "LLM_CAPTURE_CONTENT"

log = logging.getLogger(__name__)
_tracer = trace.get_tracer(__name__)


def _env_bool(env: Mapping[str, str], name: str, default: bool = False) -> bool:
    raw_value = env.get(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in _TRUE_ENV_VALUES


def _env_float(
    env: Mapping[str, str],
    name: str,
    default: float,
) -> float:
    raw_value = env.get(name)
    if raw_value is None:
        return default
    try:
        parsed_value = float(raw_value)
    except ValueError:
        return default
    if parsed_value <= 0:
        return default
    return parsed_value


def _env_int(
    env: Mapping[str, str],
    name: str,
    default: int,
) -> int:
    raw_value = env.get(name)
    if raw_value is None:
        return default
    try:
        parsed_value = int(raw_value)
    except ValueError:
        return default
    if parsed_value < 0:
        return default
    return parsed_value


@dataclass(frozen=True)
class LLMClientConfig:
    """Runtime LLM settings resolved without opening external connections."""

    default_model: str | None = None
    use_datarobot_llm_gateway: bool = False
    llm_deployment_id: str | None = None
    datarobot_endpoint: str | None = None
    datarobot_api_token: str | None = None
    timeout: float = _DEFAULT_REQUEST_TIMEOUT_SECONDS
    max_retries: int = _DEFAULT_MAX_RETRIES

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "LLMClientConfig":
        """Create config from environment variables and upstream Config defaults."""
        env = os.environ if env is None else env
        try:
            config = Config()
        except Exception:
            config = None

        return cls(
            default_model=env.get("LLM_DEFAULT_MODEL")
            or getattr(config, "llm_default_model", None),
            use_datarobot_llm_gateway=_env_bool(
                env,
                "USE_DATAROBOT_LLM_GATEWAY",
                bool(getattr(config, "use_datarobot_llm_gateway", False)),
            ),
            llm_deployment_id=(
                env.get("LLM_DEPLOYMENT_ID")
                or env.get("TEXTGEN_DEPLOYMENT_ID")
                or getattr(config, "llm_deployment_id", None)
            ),
            datarobot_endpoint=env.get("DATAROBOT_ENDPOINT")
            or getattr(config, "datarobot_endpoint", None),
            datarobot_api_token=env.get("DATAROBOT_API_TOKEN")
            or getattr(config, "datarobot_api_token", None),
            timeout=_env_float(
                env,
                "LLM_REQUEST_TIMEOUT_SECONDS",
                _DEFAULT_REQUEST_TIMEOUT_SECONDS,
            ),
            max_retries=_env_int(
                env,
                "LLM_MAX_RETRIES",
                _DEFAULT_MAX_RETRIES,
            ),
        )

    @property
    def deployment_api_base(self) -> str | None:
        """Return the OpenAI-compatible DataRobot deployment chat endpoint."""
        if not self.llm_deployment_id or not self.datarobot_endpoint:
            return None
        return (
            f"{self.datarobot_endpoint.rstrip('/')}/deployments/"
            f"{self.llm_deployment_id}/chat/completions"
        )

    def resolve_model(self, requested_model: str | None) -> str | None:
        """Map generic model aliases to the configured runtime model."""
        if requested_model is None:
            if self.default_model:
                return get_llm_model(self.default_model)
            if self.deployment_api_base:
                return get_llm_model()
            return None
        if self.default_model and requested_model in _MODEL_ALIASES_FOR_CONFIG_DEFAULT:
            return get_llm_model(self.default_model)
        if (
            self.deployment_api_base
            and requested_model in _MODEL_ALIASES_FOR_CONFIG_DEFAULT
        ):
            return get_llm_model(requested_model)
        if (
            self.use_datarobot_llm_gateway
            and "/" not in requested_model
            and requested_model
        ):
            return get_llm_model(requested_model)
        return requested_model


def _normalize_completion_token_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    normalized_kwargs = dict(kwargs)
    max_tokens = normalized_kwargs.pop("max_tokens", None)
    if max_tokens is not None and "max_completion_tokens" not in normalized_kwargs:
        normalized_kwargs["max_completion_tokens"] = max_tokens
    return normalized_kwargs


def _create_litellm_instructor() -> instructor.AsyncInstructor:
    litellm_instructor = instructor.from_litellm(
        litellm.acompletion,
        mode=instructor.Mode.MD_JSON,
    )
    if isinstance(litellm_instructor, instructor.AsyncInstructor):
        return litellm_instructor

    # instructor 1.3.4 checks inspect.isawaitable() in from_litellm(), which
    # misclassifies coroutine functions such as litellm.acompletion as sync.
    # Prefer upstream from_litellm(), then keep the async fallback required for
    # create_with_completion.
    return instructor.AsyncInstructor(
        client=None,
        create=instructor.patch(
            create=litellm.acompletion,
            mode=instructor.Mode.MD_JSON,
        ),
        mode=instructor.Mode.MD_JSON,
    )


def _usage_value(response: Any, *names: str) -> int | None:
    usage = getattr(response, "usage", None)
    if usage is None and isinstance(response, Mapping):
        usage = response.get("usage")
    if usage is None:
        return None

    for name in names:
        value = (
            usage.get(name)
            if isinstance(usage, Mapping)
            else getattr(usage, name, None)
        )
        if value is not None:
            try:
                return int(value)
            except (TypeError, ValueError):
                return None
    return None


def _provider_name(
    model: str,
    llm_config: LLMClientConfig | None,
    api_base: str | None,
) -> str:
    if api_base or llm_config and llm_config.deployment_api_base:
        return "datarobot"
    if model.startswith("datarobot/"):
        return "datarobot"
    if "/" in model:
        return model.split("/", 1)[0]
    return "openai"


def _set_llm_span_attributes(
    *,
    span: trace.Span,
    model: str,
    messages: Any,
    llm_config: LLMClientConfig | None,
    api_base: str | None,
    response: Any | None = None,
) -> None:
    provider = _provider_name(model, llm_config, api_base)
    span.set_attribute("gen_ai.operation.name", "chat")
    span.set_attribute("gen_ai.request.model", model)
    span.set_attribute("gen_ai.provider.name", provider)
    span.set_attribute("gen_ai.system", provider)

    if response is not None:
        input_tokens = _usage_value(response, "prompt_tokens", "input_tokens")
        output_tokens = _usage_value(response, "completion_tokens", "output_tokens")
        if input_tokens is not None:
            span.set_attribute("gen_ai.usage.input_tokens", input_tokens)
        if output_tokens is not None:
            span.set_attribute("gen_ai.usage.output_tokens", output_tokens)

    if _env_bool(os.environ, _CAPTURE_CONTENT_ENV):
        span.set_attribute(
            "gen_ai.input.messages",
            json.dumps(messages, default=str, ensure_ascii=False),
        )
        if response is not None:
            span.set_attribute("gen_ai.output.messages", str(response))


class TokenTrackingProxy:
    """
    Proxy that intercepts instructor client calls and tracks tokens.
    """

    def __init__(
        self,
        client: instructor.AsyncInstructor,
        tracker: TokenUsageTracker | None = None,
        llm_config: LLMClientConfig | None = None,
        api_base: str | None = None,
    ):
        self._client = client
        self._tracker = tracker
        self._llm_config = llm_config
        self._api_base = api_base

    @property
    def chat(self) -> ChatProxy:
        """Return wrapped chat interface."""
        return ChatProxy(
            self._client.chat,
            self._tracker,
            self._llm_config,
            self._api_base,
        )

    def __getattr__(self, name: str) -> Any:
        """Delegate other attributes to underlying client."""
        return getattr(self._client, name)


class ChatProxy:
    """Proxy for chat interface."""

    def __init__(
        self,
        chat: Any,
        tracker: TokenUsageTracker | None,
        llm_config: LLMClientConfig | None = None,
        api_base: str | None = None,
    ):
        self._chat = chat
        self._tracker = tracker
        self._llm_config = llm_config
        self._api_base = api_base

    @property
    def completions(self) -> CompletionsProxy:
        """Return wrapped completions interface."""
        return CompletionsProxy(
            self._chat.completions,
            self._tracker,
            self._llm_config,
            self._api_base,
        )


class CompletionsProxy:
    """Proxy for completions interface with token tracking and verbose error handling."""

    def __init__(
        self,
        completions: Any,
        tracker: TokenUsageTracker | None,
        llm_config: LLMClientConfig | None = None,
        api_base: str | None = None,
    ):
        self._completions = completions
        self._tracker = tracker
        self._llm_config = llm_config
        self._api_base = api_base

    def _prepare_kwargs(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        prepared_kwargs = _normalize_completion_token_kwargs(kwargs)
        if self._llm_config is None:
            return prepared_kwargs

        requested_model = prepared_kwargs.get("model")
        requested_model_name = (
            str(requested_model) if requested_model is not None else None
        )
        resolved_model = self._llm_config.resolve_model(requested_model_name)
        if resolved_model:
            prepared_kwargs["model"] = resolved_model

        if self._api_base and "api_base" not in prepared_kwargs:
            prepared_kwargs["api_base"] = self._api_base
            if (
                self._llm_config.datarobot_api_token
                and "api_key" not in prepared_kwargs
            ):
                prepared_kwargs["api_key"] = self._llm_config.datarobot_api_token

        prepared_kwargs.setdefault("timeout", self._llm_config.timeout)
        prepared_kwargs.setdefault("max_retries", self._llm_config.max_retries)
        return prepared_kwargs

    async def create(self, *args: Any, **kwargs: Any) -> Any:
        """Intercept create calls to track tokens."""
        kwargs = self._prepare_kwargs(kwargs)
        messages = kwargs.get("messages", [])
        model = kwargs.get("model", "unknown")

        log.debug(
            f"LLM API call starting - model: {model}, "
            f"api_base: {kwargs.get('api_base', 'default')}, "
            f"messages_count: {len(messages)}, timeout: {kwargs.get('timeout')}s"
        )

        try:
            with _tracer.start_as_current_span(f"gen_ai.chat {model}") as span:
                _set_llm_span_attributes(
                    span=span,
                    model=str(model),
                    messages=messages,
                    llm_config=self._llm_config,
                    api_base=self._api_base,
                )
                # Call underlying implementation
                result = await self._completions.create(*args, **kwargs)
                _set_llm_span_attributes(
                    span=span,
                    model=str(model),
                    messages=messages,
                    llm_config=self._llm_config,
                    api_base=self._api_base,
                    response=result,
                )

            # Track tokens if tracker is available
            if self._tracker:
                self._tracker.track_call(messages, result, model)

            log.debug(f"LLM API call completed successfully - model: {model}")
            return result
        except Exception as e:
            self._log_llm_error(e, model, kwargs)
            raise

    async def create_with_completion(self, *args: Any, **kwargs: Any) -> Any:
        """Intercept create calls to track tokens."""
        kwargs = self._prepare_kwargs(kwargs)
        messages = kwargs.get("messages", [])
        model = kwargs.get("model", "unknown")

        log.debug(
            f"LLM API call starting - model: {model}, "
            f"api_base: {kwargs.get('api_base', 'default')}, "
            f"messages_count: {len(messages)}, timeout: {kwargs.get('timeout')}s"
        )

        try:
            with _tracer.start_as_current_span(f"gen_ai.chat {model}") as span:
                _set_llm_span_attributes(
                    span=span,
                    model=str(model),
                    messages=messages,
                    llm_config=self._llm_config,
                    api_base=self._api_base,
                )
                # Call underlying implementation
                result, org = await self._completions.create_with_completion(
                    *args, **kwargs
                )
                _set_llm_span_attributes(
                    span=span,
                    model=str(model),
                    messages=messages,
                    llm_config=self._llm_config,
                    api_base=self._api_base,
                    response=org,
                )

            # Track tokens if tracker is available
            if self._tracker:
                self._tracker.track_call(messages, org, model)

            log.debug(f"LLM API call completed successfully - model: {model}")
            return result, org
        except Exception as e:
            self._log_llm_error(e, model, kwargs)
            raise

    def _log_llm_error(self, e: Exception, model: str, kwargs: dict[str, Any]) -> None:
        """Log detailed error information for LLM API failures."""
        api_base = kwargs.get("api_base", "default")
        timeout = kwargs.get("timeout", "unknown")
        error_type = type(e).__name__
        error_message = str(e)

        # Extract status code if available
        status_code = None
        if hasattr(e, "status_code"):
            status_code = e.status_code
        elif hasattr(e, "response") and hasattr(e.response, "status_code"):
            status_code = e.response.status_code

        # Map exception types to error descriptions
        error_descriptions: dict[type[BaseException], tuple[str, str]] = {
            APITimeoutError: (
                "TIMEOUT",
                f"Request timed out after {timeout}s. Check if the deployment is responsive.",
            ),
            AuthenticationError: (
                "AUTH ERROR (401)",
                "Unauthorized access. Check API token and permissions.",
            ),
            NotFoundError: (
                "NOT FOUND (404)",
                "Resource not found. The deployment ID may be incorrect or deleted.",
            ),
            RateLimitError: (
                "RATE LIMIT (429)",
                "Rate limit exceeded. Too many requests, please slow down.",
            ),
            InternalServerError: (
                "SERVER ERROR (500)",
                "Internal server error. The LLM deployment may be misconfigured or down. "
                "Often caused by: incorrect model name, deployment issues, or unavailable target model.",
            ),
            BadRequestError: (
                "BAD REQUEST (400)",
                "Invalid request. Check request parameters and model name.",
            ),
            APIConnectionError: (
                "CONNECTION ERROR",
                "Failed to connect. Check network connectivity and firewall rules.",
            ),
            APIStatusError: (
                f"STATUS ERROR ({status_code or 'unknown'})",
                "HTTP error from server.",
            ),
            APIError: (
                "ERROR",
                "API error occurred.",
            ),
        }

        # Find matching error type
        label, description = "ERROR", "Unexpected error occurred."
        for exc_type, (exc_label, exc_desc) in error_descriptions.items():
            if isinstance(e, exc_type):
                label, description = exc_label, exc_desc
                break
        else:
            # Also check for asyncio.TimeoutError and httpx.ConnectError
            if isinstance(e, asyncio.TimeoutError):
                label = "TIMEOUT"
                description = (
                    f"Request timed out after {timeout}s. "
                    "Check if the deployment is responsive."
                )
            elif isinstance(e, httpx.ConnectError):
                label = "CONNECTION ERROR"
                description = (
                    "Failed to connect. Check network connectivity and firewall rules."
                )

        log.error(
            f"LLM API {label}: {description} "
            f"Endpoint: {api_base}, Model: {model}. "
            f"Error: {error_type}: {error_message}"
        )


class AsyncLLMClient:
    """
    Async LLM client with token tracking.

    Usage:
        from datarobot_genai.core.utils.token_tracking import (
            HeuristicTokenCountingStrategy,
            TokenUsageTracker,
        )

        tracker = TokenUsageTracker(strategy=HeuristicTokenCountingStrategy())
        async with AsyncLLMClient(token_tracker=tracker) as client:
            result = await client.chat.completions.create(...)

        usage_info = TokenUsageInfo(**tracker.to_dict())

        # To use API response strategy:
        from datarobot_genai.core.utils.token_tracking import ApiResponseCountingStrategy

        tracker = TokenUsageTracker(strategy=ApiResponseCountingStrategy())
        async with AsyncLLMClient(token_tracker=tracker) as client:
            result = await client.chat.completions.create(...)
    """

    def __init__(
        self,
        token_tracker: TokenUsageTracker | None = None,
        dr_client: Any | None = None,
        deployment_base_url: str | None = None,
        llm_config: LLMClientConfig | None = None,
    ):
        """
        Initialize AsyncLLMClient.

        Args:
            token_tracker: Optional token usage tracker
            dr_client: Optional DataRobot client used to fill the LiteLLM API token
            deployment_base_url: Deprecated compatibility argument; LiteLLM routing
                uses LLMClientConfig instead.
        """
        self.token_tracker = token_tracker
        self._dr_client = dr_client
        del deployment_base_url
        self._llm_config = llm_config or LLMClientConfig.from_env()
        self._instructor_client: instructor.AsyncInstructor | None = None

    async def __aenter__(self) -> TokenTrackingProxy:
        """Initialize clients on context entry."""
        return self._create_litellm_client()

    def _create_litellm_client(self) -> TokenTrackingProxy:
        if litellm is None:
            raise RuntimeError(
                "LiteLLM is required for configured LLM gateway/deployment usage."
            )

        llm_config = self._llm_config
        if self._dr_client is not None and llm_config.datarobot_api_token is None:
            dr_token = getattr(self._dr_client, "token", None)
            if dr_token:
                llm_config = replace(llm_config, datarobot_api_token=dr_token)

        self._instructor_client = _create_litellm_instructor()
        return TokenTrackingProxy(
            self._instructor_client,
            self.token_tracker,
            llm_config,
            llm_config.deployment_api_base,
        )

    async def __aexit__(
        self,
        exc_type: Type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Clean up clients on context exit."""
        return None
