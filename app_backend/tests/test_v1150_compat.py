import asyncio
import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("APPLICATION_ID", "test-app")
os.environ.setdefault("DATAROBOT_API_TOKEN", "test-token")
os.environ.setdefault("DATAROBOT_ENDPOINT", "https://example.com")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")

from utils import prompts, rest_api
from utils.data_connections.datarobot.datarobot_dataset_handler import (
    BaseRecipe,
    DataSourceRecipe,
    format_spark_table,
)
from utils.datarobot_client import get_visitors_token
from utils.persistent_storage import PersistentStorage


def test_get_visitors_token_prefers_session_scoped_token() -> None:
    request = SimpleNamespace(
        headers={"x-datarobot-api-key": "header-token"},
        state=SimpleNamespace(
            session=SimpleNamespace(datarobot_api_scoped_token="session-token")
        ),
    )

    assert get_visitors_token(request) == "session-token"


def test_get_visitors_token_falls_back_to_header_token() -> None:
    request = SimpleNamespace(
        headers={"x-datarobot-api-key": "header-token"},
        state=SimpleNamespace(session=SimpleNamespace(datarobot_api_scoped_token=None)),
    )

    assert get_visitors_token(request) == "header-token"


def test_initialize_session_uses_scoped_token_name_in_local_dev(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    asyncio.run(_assert_initialize_session_uses_scoped_token_name(monkeypatch))


async def _assert_initialize_session_uses_scoped_token_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEV_MODE", "1")
    monkeypatch.setenv("DATAROBOT_API_TOKEN", "local-token")
    rest_api.session_store.clear()

    request = SimpleNamespace(cookies={}, headers={})

    session_state, session_id, user_id = await rest_api._initialize_session(request)

    assert session_id is None
    assert user_id is None
    assert session_state.datarobot_api_scoped_token == "local-token"
    assert not hasattr(session_state, "datarobot_api_skoped_token")


def test_datarobot_preview_schema_accepts_sdk_310_data_type_key() -> None:
    assert BaseRecipe.get_column_data_type(
        {"name": "amount", "data_type": "DOUBLE"}
    ) == ("DOUBLE")
    assert BaseRecipe.get_column_data_type(
        {"name": "amount", "dataType": "DOUBLE"}
    ) == ("DOUBLE")


def test_databricks_datasource_is_supported() -> None:
    assert "databricks-v1" in DataSourceRecipe.SUPPORTED_DRIVER_CLASS_TYPES
    assert DataSourceRecipe.PROMPTS["databricks-v1"] == prompts.SYSTEM_PROMPT_DATABRICKS
    assert DataSourceRecipe.WARMUP_QUERIES["databricks-v1"] == "SELECT 1"
    assert DataSourceRecipe.FORMAT_TABLE_NAME["databricks-v1"](
        ["catalog", "schema", "sales"]
    ) == format_spark_table(["catalog", "schema", "sales"])


def test_persistent_storage_validates_runtime_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APPLICATION_ID", "test-app")
    monkeypatch.delenv("DATAROBOT_ENDPOINT", raising=False)
    monkeypatch.delenv("DATAROBOT_API_TOKEN", raising=False)

    with pytest.raises(ValueError, match="DATAROBOT_ENDPOINT and DATAROBOT_API_TOKEN"):
        PersistentStorage("user-1")
