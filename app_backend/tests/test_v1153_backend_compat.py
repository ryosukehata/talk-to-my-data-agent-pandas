import logging
from io import StringIO
from types import SimpleNamespace

import datarobot
import pandas as pd
import pytest
from core.api_exceptions import ApplicationUsageException
from core.config import Config as CoreConfig
from datarobot_genai.core.utils import token_tracking as genai_token_tracking
from utils.data_connections.datarobot.helpers import RecipeError, handle_datarobot_error
from utils.datarobot_client import get_visitors_token, use_user_token
from utils.token_tracking import (
    ApiResponseCountingStrategy,
    HeuristicTokenCountingStrategy,
    TokenUsageTracker,
    count_messages_tokens,
    estimate_csv_rows_for_token_limit,
)

from app.config import Config
from app.telemetry import ReadableFormatter


def make_request(
    *,
    session_token: str | None = None,
    header_token: str | None = None,
) -> SimpleNamespace:
    headers = {}
    if header_token:
        headers["x-datarobot-api-key"] = header_token
    return SimpleNamespace(
        headers=headers,
        state=SimpleNamespace(
            session=SimpleNamespace(datarobot_api_scoped_token=session_token)
        ),
    )


def test_default_log_format_is_readable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LOG_FORMAT", raising=False)
    monkeypatch.delenv("MLOPS_RUNTIME_PARAM_LOG_FORMAT", raising=False)

    assert Config().log_format == "readable"


def test_readable_log_formatter_keeps_extra_fields() -> None:
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(ReadableFormatter())
    logger = logging.getLogger("v1153")
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.propagate = False
    logger.setLevel(logging.INFO)

    logger.info("hello", extra={"dataset": "sales"})

    output = stream.getvalue()

    assert "INFO:v1153:hello" in output
    assert "dataset=sales" in output


def test_builder_token_can_be_selected_when_allowed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("USE_BUILDER_API_TOKEN", "true")
    monkeypatch.setenv("DATAROBOT_ENDPOINT", "https://app.datarobot.com/api/v2")
    monkeypatch.setenv("DATAROBOT_API_TOKEN", "builder-token")
    request = make_request(session_token="session-token", header_token="header-token")

    assert get_visitors_token(request, allow_use_builder_token=True) == "builder-token"


def test_core_config_exposes_builder_token_toggle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("USE_BUILDER_API_TOKEN", "true")
    monkeypatch.setenv("DATAROBOT_ENDPOINT", "https://app.datarobot.com/api/v2")
    monkeypatch.setenv("DATAROBOT_API_TOKEN", "builder-token")

    config = CoreConfig()

    assert config.use_builder_api_token is True
    assert config.datarobot_api_token == "builder-token"


def test_core_config_reads_runtime_builder_token_toggle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("USE_BUILDER_API_TOKEN", raising=False)
    monkeypatch.setenv("MLOPS_RUNTIME_PARAM_USE_BUILDER_API_TOKEN", "true")
    monkeypatch.setenv("DATAROBOT_ENDPOINT", "https://app.datarobot.com/api/v2")
    monkeypatch.setenv("DATAROBOT_API_TOKEN", "builder-token")

    assert CoreConfig().use_builder_api_token is True


def test_builder_token_is_not_used_unless_allowed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("USE_BUILDER_API_TOKEN", "true")
    monkeypatch.setenv("DATAROBOT_API_TOKEN", "builder-token")
    request = make_request(session_token="session-token", header_token="header-token")

    assert get_visitors_token(request) == "session-token"


def test_use_user_token_clears_empty_local_default_use_case(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATAROBOT_ENDPOINT", "https://app.datarobot.com/api/v2")
    monkeypatch.setenv("DATAROBOT_API_TOKEN", "builder-token")
    monkeypatch.setenv("DATAROBOT_DEFAULT_USE_CASE", "")
    monkeypatch.delenv("DR_CUSTOM_APP_EXTERNAL_URL", raising=False)
    request = make_request()

    calls: list[dict[str, object]] = []

    class ClientConfiguration:
        def __init__(self, **kwargs: object) -> None:
            calls.append(kwargs)

        def __enter__(self) -> None:
            return None

        def __exit__(self, *args: object) -> None:
            return None

    monkeypatch.setattr(
        datarobot.client,
        "client_configuration",
        ClientConfiguration,
    )

    with use_user_token(request):
        pass

    assert calls == [{"default_use_case": []}]


def test_use_user_token_clears_empty_default_use_case_with_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATAROBOT_ENDPOINT", "https://app.datarobot.com/api/v2")
    monkeypatch.setenv("DATAROBOT_DEFAULT_USE_CASE", "")
    request = make_request(session_token="session-token")

    calls: list[dict[str, object]] = []

    class Client:
        def __init__(self, **kwargs: object) -> None:
            calls.append(kwargs)

        def __enter__(self) -> None:
            return None

        def __exit__(self, *args: object) -> None:
            return None

    monkeypatch.setattr(datarobot, "Client", Client)

    with use_user_token(request):
        pass

    assert calls == [
        {
            "token": "session-token",
            "endpoint": "https://app.datarobot.com/api/v2",
            "default_use_case": [],
        }
    ]


def test_handle_datarobot_error_maps_seat_license_403() -> None:
    error = datarobot.errors.ClientError("Access denied", 403)
    error.json = {"message": "Access denied due to seat license restrictions"}

    with pytest.raises(ApplicationUsageException, match="seat license restrictions"):
        with handle_datarobot_error("Dataset.iterate()"):
            raise error


def test_handle_datarobot_error_maps_wrapped_404() -> None:
    client_error = datarobot.errors.ClientError("Not found", 404)
    wrapped_error = ValueError("Current use case is invalid.", client_error)

    with pytest.raises(RecipeError, match="Dataset.iterate\\(\\) not found"):
        with handle_datarobot_error("Dataset.iterate()"):
            raise wrapped_error


def test_default_token_counting_uses_heuristic_strategy() -> None:
    tracker = TokenUsageTracker(strategy=ApiResponseCountingStrategy())
    assert isinstance(tracker.strategy.fallback_strategy, HeuristicTokenCountingStrategy)
    assert count_messages_tokens([{"role": "user", "content": "hello world"}]) > 0


def test_token_tracking_is_provided_by_datarobot_genai() -> None:
    assert TokenUsageTracker is genai_token_tracking.TokenUsageTracker
    assert (
        HeuristicTokenCountingStrategy
        is genai_token_tracking.HeuristicTokenCountingStrategy
    )
    assert ApiResponseCountingStrategy is genai_token_tracking.ApiResponseCountingStrategy
    assert count_messages_tokens is genai_token_tracking.count_messages_tokens


def test_csv_token_estimation_accepts_legacy_model_argument() -> None:
    csv_text, token_count = estimate_csv_rows_for_token_limit(
        pd.DataFrame({"name": ["sales"]}),
        100,
        1,
        "azure/gpt-4o",
    )

    assert "sales" in csv_text
    assert token_count > 0
