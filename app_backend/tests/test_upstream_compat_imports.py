import importlib
import inspect

import pytest


def _set_required_import_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATAROBOT_API_TOKEN", "test-token")
    monkeypatch.setenv("DATAROBOT_ENDPOINT", "https://example.com")
    monkeypatch.setenv("OTEL_SDK_DISABLED", "true")


def test_database_helper_import_paths_remain_compatible(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_required_import_env(monkeypatch)

    legacy = importlib.import_module("utils.database_helpers")
    upstream_path = importlib.import_module(
        "utils.data_connections.database.database_implementations"
    )
    schema = importlib.import_module("utils.schema")

    assert upstream_path.DatabaseOperator is legacy.DatabaseOperator
    assert upstream_path.NoDatabaseOperator is legacy.NoDatabaseOperator
    assert "schema" in inspect.signature(upstream_path.get_external_database).parameters
    assert "schema" in inspect.signature(upstream_path.get_database_operator).parameters

    app_infra = schema.AppInfra(llm="no_llm", database="no_database")
    operator = upstream_path.get_database_operator(app_infra)

    assert isinstance(operator, legacy.NoDatabaseOperator)


def test_datarobot_dataset_handler_import_paths_remain_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_required_import_env(monkeypatch)

    legacy = importlib.import_module("utils.datarobot_dataset_handler")
    upstream_path = importlib.import_module(
        "utils.data_connections.datarobot.datarobot_dataset_handler"
    )

    for exported_name in (
        "DataRobotOperator",
        "DataSourceRecipe",
        "DatasetSparkRecipe",
    ):
        assert hasattr(legacy, exported_name)
        assert hasattr(upstream_path, exported_name)
