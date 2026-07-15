from pathlib import Path
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

_SNOWFLAKE_ENV_VARS = (
    "SNOWFLAKE_USER",
    "SNOWFLAKE_PASSWORD",
    "SNOWFLAKE_ACCOUNT",
    "SNOWFLAKE_WAREHOUSE",
    "SNOWFLAKE_DATABASE",
    "SNOWFLAKE_SCHEMA",
    "SNOWFLAKE_ROLE",
    "SNOWFLAKE_KEY_PATH",
)


def _clear_snowflake_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for env_var in _SNOWFLAKE_ENV_VARS:
        monkeypatch.delenv(env_var, raising=False)


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


def test_jdbc_preview_query_name_supports_schema_prefixed_dataset_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "JDBC_URI",
        "jdbc:snowflake://account.snowflakecomputing.com/?db=ANALYTICS&schema=PUBLIC",
    )

    operator = get_database_operator(
        AppInfra(llm="llm", database="snowflake"), schema="SALES"
    )

    assert operator.query_friendly_name("SALES-orders") == '"SALES"."orders"'
    assert operator.query_friendly_name("SALES.orders") == '"SALES"."orders"'


def test_snowflake_jdbc_system_prompt_requires_derived_table_safe_sql(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "JDBC_URI",
        "jdbc:snowflake://account.snowflakecomputing.com/?db=ANALYTICS&schema=PUBLIC",
    )

    prompt = JdbcPreviewOperator(JDBCCredentials()).get_system_prompt()["content"]

    assert "exactly one SELECT statement or one WITH/CTE statement" in prompt
    assert "MUST NOT have a trailing semicolon" in prompt
    assert "Return valid JSON only" in prompt
    assert "Do not wrap the JSON or SQL in Markdown code fences" in prompt
    assert "Do not use SHOW, DESCRIBE, EXPLAIN, CALL" in prompt
    assert "Never use placeholders, template variables" in prompt
    assert "Use only the exact table references" in prompt
    assert (
        "ARRAY_AGG(DISTINCT expression) WITHIN GROUP (ORDER BY expression)" in prompt
    )
    assert "ORDER BY expression must be the same expression" in prompt
    assert "Do not repeat an invalid placeholder, table reference" in prompt
    assert "Warehouse: {warehouse}" not in prompt
    assert "Database: {database}" not in prompt
    assert "{database}" not in prompt
    assert "{schema}" not in prompt


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
    _clear_snowflake_env(monkeypatch)

    with pytest.raises(ValueError, match="JDBC_URI"):
        get_database_operator(AppInfra(llm="llm", database=database))


def test_snowflake_legacy_env_values_build_jdbc_preview_operator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("JDBC_URI", raising=False)
    monkeypatch.delenv("JDBC_CONNECTION_PARAMETERS", raising=False)
    _clear_snowflake_env(monkeypatch)
    monkeypatch.setenv("SNOWFLAKE_USER", "snowflake_user")
    monkeypatch.setenv("SNOWFLAKE_PASSWORD", "snowflake_password")
    monkeypatch.setenv("SNOWFLAKE_ACCOUNT", "account")
    monkeypatch.setenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH")
    monkeypatch.setenv("SNOWFLAKE_DATABASE", "ANALYTICS")
    monkeypatch.setenv("SNOWFLAKE_SCHEMA", "PUBLIC")
    monkeypatch.setenv("SNOWFLAKE_ROLE", "ANALYST")

    operator = get_database_operator(AppInfra(llm="llm", database="snowflake"))

    assert isinstance(operator, JdbcPreviewOperator)
    assert (
        operator._credentials.jdbc_uri
        == "jdbc:snowflake://account.snowflakecomputing.com/"
        "?warehouse=COMPUTE_WH&db=ANALYTICS&schema=PUBLIC&role=ANALYST"
    )
    assert operator._parameters() == {
        "user": "snowflake_user",
        "password": "snowflake_password",
    }


def test_snowflake_legacy_key_file_uses_base64_private_key_parameter(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("JDBC_URI", raising=False)
    monkeypatch.delenv("JDBC_CONNECTION_PARAMETERS", raising=False)
    _clear_snowflake_env(monkeypatch)
    monkeypatch.chdir(tmp_path)
    tmp_path.joinpath("rsa_key.p8").write_bytes(b"private-key-pem")
    monkeypatch.setenv("SNOWFLAKE_USER", "snowflake_user")
    monkeypatch.setenv("SNOWFLAKE_KEY_PATH", "rsa_key.p8")
    monkeypatch.setenv("SNOWFLAKE_ACCOUNT", "account")
    monkeypatch.setenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH")
    monkeypatch.setenv("SNOWFLAKE_DATABASE", "ANALYTICS")
    monkeypatch.setenv("SNOWFLAKE_SCHEMA", "PUBLIC")
    monkeypatch.setenv("SNOWFLAKE_ROLE", "ANALYST")

    operator = get_database_operator(AppInfra(llm="llm", database="snowflake"))

    assert operator._parameters() == {
        "user": "snowflake_user",
        "private_key_base64": "cHJpdmF0ZS1rZXktcGVt",
    }


def test_snowflake_legacy_env_does_not_hide_invalid_explicit_jdbc_uri(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("JDBC_URI", "jdbc:oracle://example.test/db")
    monkeypatch.delenv("JDBC_CONNECTION_PARAMETERS", raising=False)
    _clear_snowflake_env(monkeypatch)
    monkeypatch.setenv("SNOWFLAKE_USER", "snowflake_user")
    monkeypatch.setenv("SNOWFLAKE_PASSWORD", "snowflake_password")
    monkeypatch.setenv("SNOWFLAKE_ACCOUNT", "account")
    monkeypatch.setenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH")
    monkeypatch.setenv("SNOWFLAKE_DATABASE", "ANALYTICS")
    monkeypatch.setenv("SNOWFLAKE_SCHEMA", "PUBLIC")
    monkeypatch.setenv("SNOWFLAKE_ROLE", "ANALYST")

    with pytest.raises(ValueError, match="JDBC_URI"):
        get_database_operator(AppInfra(llm="llm", database="snowflake"))


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


@pytest.mark.asyncio
async def test_jdbc_preview_registers_schema_prefixed_display_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "JDBC_URI",
        "jdbc:snowflake://account.snowflakecomputing.com/?db=ANALYTICS&schema=PUBLIC",
    )
    captured_sql: list[str] = []
    registered: list[dict[str, Any]] = []

    class FakePreview:
        @staticmethod
        def preview(**kwargs: Any) -> Mock:
            captured_sql.append(kwargs["sql"])
            return Mock(
                records=[(1,)],
                result_schema=[{"name": "ORDER_ID", "data_type": "NUMBER"}],
            )

    class FakeAnalystDB:
        async def register_dataset(
            self, dataset: Any, data_source: Any, **kwargs: Any
        ) -> dict[str, Any]:
            registered.append(
                {"dataset": dataset, "data_source": data_source, **kwargs}
            )
            return {"success": True, "msg": ""}

    monkeypatch.setattr(
        JdbcPreviewOperator, "_preview", staticmethod(lambda: FakePreview)
    )

    operator = get_database_operator(
        AppInfra(llm="llm", database="snowflake"), schema="SALES"
    )

    names = await operator.get_data("ORDERS", analyst_db=FakeAnalystDB())

    assert names == ["SALES-ORDERS"]
    assert captured_sql[0] == 'SELECT * FROM "SALES"."ORDERS"'
    assert registered[0]["dataset"].name == "SALES-ORDERS"
    assert registered[0]["external_id"] == "SALES.ORDERS"
    assert registered[0]["clobber"] is True


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
