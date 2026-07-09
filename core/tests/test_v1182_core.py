from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest
from pydantic import ValidationError

from core.credentials import JDBCCredentials
from core.database_helpers import JdbcPreviewOperator, get_database_operator
from core.persistent_storage import AsyncDataRobotClient
from core.schema import (
    AppInfra,
    CodeGeneration,
    DatabaseConnectionType,
    RunAnalysisResult,
    RunAnalysisResultMetadata,
)
from core.telemetry.otel import OTel, OTLPConnectionErrorFilter


@pytest.fixture(autouse=True)
def reset_otel_singleton() -> None:
    OTel._instance = None
    OTel._initialized = False
    OTel._auto_instrumentation_setup = False
    yield
    OTel._instance = None
    OTel._initialized = False
    OTel._auto_instrumentation_setup = False


@pytest.mark.asyncio
async def test_async_datarobot_client_uses_timeout_and_does_not_reapply_params() -> (
    None
):
    with patch("httpx.AsyncClient", autospec=httpx.AsyncClient) as async_client:
        async_client.return_value = async_client

        def response(payload: dict[str, Any]) -> Mock:
            mock = Mock()
            mock.json.return_value = payload
            return mock

        async def get(path: str, **kwargs: Any) -> Mock:
            if path == "keyValues/":
                assert kwargs["params"] == {"entityId": "app-id"}
                return response({"data": [{"id": 1}], "next": "keyValues/?page=2"})
            if path == "keyValues/?page=2":
                assert "params" not in kwargs or kwargs["params"] is None
                return response({"data": [{"id": 2}], "next": None})
            raise AssertionError(f"unexpected path: {path}")

        async_client.get = AsyncMock(side_effect=get)

        client = AsyncDataRobotClient(token="token", endpoint="https://example.test")
        values = [
            value
            async for value in client.unpaginate("keyValues/", {"entityId": "app-id"})
        ]

    assert values == [{"id": 1}, {"id": 2}]
    _, kwargs = async_client.call_args
    assert isinstance(kwargs["timeout"], httpx.Timeout)


def test_otel_does_not_auto_instrument_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DISABLE_TELEMETRY", "true")

    with patch.object(OTel, "_setup_auto_instrumentation") as setup_auto:
        otel = OTel()

    assert otel.telemetry_enabled is False
    setup_auto.assert_not_called()


def test_code_generation_and_result_expose_used_datasets() -> None:
    completion = CodeGeneration(
        code="def analyze_data(dfs): return dfs['sales']",
        description="analysis",
        used_datasets=["sales"],
    )
    result = RunAnalysisResult(
        status="success",
        metadata=RunAnalysisResultMetadata(duration=0, attempts=1),
        used_datasets=completion.used_datasets,
    )

    assert completion.used_datasets == ["sales"]
    assert result.used_datasets == ["sales"]
    assert (
        CodeGeneration(
            code="x = 1", description="analysis", used_datasets="sales"
        ).used_datasets
        == []
    )


def test_database_connection_type_includes_datarobot_jdbc() -> None:
    assert "datarobot_jdbc" in DatabaseConnectionType.__args__


def test_jdbc_credentials_validate_supported_uri(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("JDBC_URI", "jdbc:postgresql://example.test:5432/db")
    monkeypatch.setenv(
        "JDBC_CONNECTION_PARAMETERS", '{"user": "dbuser", "password": "secret"}'
    )

    credentials = JDBCCredentials()

    assert credentials.jdbc_uri == "jdbc:postgresql://example.test:5432/db"
    assert credentials.jdbc_connection_parameters == {
        "user": "dbuser",
        "password": "secret",
    }

    monkeypatch.setenv("JDBC_URI", "jdbc:oracle://example.test/db")
    with pytest.raises(ValidationError):
        JDBCCredentials()


@pytest.mark.parametrize(
    "jdbc_uri",
    [
        "jdbc:snowflake://account.snowflakecomputing.com/",
        "jdbc:sap://host:443",
        "jdbc:bigquery://https://www.googleapis.com/bigquery/v2:443",
    ],
)
def test_jdbc_credentials_validate_platform_jdbc_uris(
    monkeypatch: pytest.MonkeyPatch, jdbc_uri: str
) -> None:
    monkeypatch.setenv("JDBC_URI", jdbc_uri)

    assert JDBCCredentials().jdbc_uri == jdbc_uri


def test_get_database_operator_returns_jdbc_preview_operator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("JDBC_URI", "jdbc:mysql://example.test:3306/db")

    operator = get_database_operator(AppInfra(llm="llm", database="datarobot_jdbc"))

    assert isinstance(operator, JdbcPreviewOperator)
    assert operator.query_friendly_name("sales") == "`sales`"


@pytest.mark.parametrize(
    ("database", "jdbc_uri", "quoted_name"),
    [
        ("snowflake", "jdbc:snowflake://account.snowflakecomputing.com/", '"sales"'),
        ("sap", "jdbc:sap://host:443", '"sales"'),
        (
            "bigquery",
            "jdbc:bigquery://https://www.googleapis.com/bigquery/v2:443",
            "`sales`",
        ),
    ],
)
def test_platform_database_types_use_jdbc_preview_operator(
    monkeypatch: pytest.MonkeyPatch,
    database: str,
    jdbc_uri: str,
    quoted_name: str,
) -> None:
    monkeypatch.setenv("JDBC_URI", jdbc_uri)

    operator = get_database_operator(AppInfra(llm="llm", database=database))

    assert isinstance(operator, JdbcPreviewOperator)
    assert operator.query_friendly_name("sales") == quoted_name


@pytest.mark.parametrize("database", ["snowflake", "sap", "bigquery", "datarobot_jdbc"])
def test_platform_database_types_require_jdbc_uri(
    monkeypatch: pytest.MonkeyPatch,
    database: str,
) -> None:
    monkeypatch.delenv("JDBC_URI", raising=False)
    monkeypatch.delenv("JDBC_CONNECTION_PARAMETERS", raising=False)

    with pytest.raises(ValueError, match="JDBC_URI"):
        get_database_operator(AppInfra(llm="llm", database=database))


def test_jdbc_preview_get_schemas_uses_data_preview(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "JDBC_URI",
        "jdbc:snowflake://account.snowflakecomputing.com/?db=ANALYTICS&schema=PUBLIC",
    )
    captured_sql: list[str] = []

    class FakePreview:
        @staticmethod
        def preview(**kwargs: Any) -> Mock:
            captured_sql.append(kwargs["sql"])
            return Mock(records=[("PUBLIC",), {"SCHEMA_NAME": "SALES"}])

    monkeypatch.setattr(
        JdbcPreviewOperator, "_preview", staticmethod(lambda: FakePreview)
    )

    schemas = JdbcPreviewOperator(JDBCCredentials()).get_schemas()

    assert schemas == ["PUBLIC", "SALES"]
    assert "INFORMATION_SCHEMA.SCHEMATA" in captured_sql[0]


@pytest.mark.asyncio
async def test_jdbc_preview_selected_schema_filters_table_discovery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "JDBC_URI",
        "jdbc:snowflake://account.snowflakecomputing.com/?db=ANALYTICS&schema=PUBLIC",
    )
    captured_sql: list[str] = []

    class FakePreview:
        @staticmethod
        def preview(**kwargs: Any) -> Mock:
            captured_sql.append(kwargs["sql"])
            return Mock(records=[("ORDERS",)])

    monkeypatch.setattr(
        JdbcPreviewOperator, "_preview", staticmethod(lambda: FakePreview)
    )

    operator = get_database_operator(
        AppInfra(llm="llm", database="snowflake"), schema="SALES"
    )

    tables = await operator.get_tables()

    assert tables == ["ORDERS"]
    assert "TABLE_SCHEMA = 'SALES'" in captured_sql[0]


def test_otlp_filter_suppresses_metrics_read_timeout() -> None:
    warnings: list[str] = []
    filter_ = OTLPConnectionErrorFilter(lambda: warnings.append("warned"))
    exc = TimeoutError("The read operation timed out")
    record = Mock(
        name="opentelemetry.sdk.metrics._internal.export",
        levelno=40,
        exc_info=(TimeoutError, exc, None),
    )
    record.getMessage.return_value = "Exception while exporting metrics"

    assert filter_.filter(record) is False
    assert warnings == ["warned"]
