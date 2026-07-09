import asyncio
import io
import os

import pandas as pd
import pytest
from fastapi import BackgroundTasks, UploadFile

os.environ.setdefault("DATAROBOT_API_TOKEN", "test-token")
os.environ.setdefault("DATAROBOT_ENDPOINT", "https://example.com")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")

from core.routers import database as database_router
from utils import rest_api
from utils.analyst_db import InternalDataSourceType
from utils.schema import AnalystDataset, LoadDatabaseRequest


def test_csv_helpers_decode_bom_and_load_pandas_dataframe() -> None:
    raw_bytes = "\ufeffdate;amount\r\n2026-01-01;100\r\n".encode()

    decoded = rest_api.detect_and_decode_csv(raw_bytes, "sales.csv")
    dataframe = rest_api.load_and_validate_csv(decoded, "sales.csv")

    assert decoded.startswith("date;amount")
    assert isinstance(dataframe, pd.DataFrame)
    assert dataframe.to_dict("records") == [
        {"date": "2026-01-01", "amount": 100},
    ]


def test_csv_loader_rejects_header_only_file() -> None:
    with pytest.raises(ValueError, match="contains only headers"):
        rest_api.load_and_validate_csv("date,amount\n", "empty.csv")


def test_upload_files_registers_csv_as_pandas_dataframe() -> None:
    asyncio.run(_assert_upload_files_registers_csv_as_pandas_dataframe())


async def _assert_upload_files_registers_csv_as_pandas_dataframe() -> None:
    class FakeAnalystDB:
        def __init__(self) -> None:
            self.registered: list[tuple[AnalystDataset, InternalDataSourceType]] = []

        async def register_dataset(
            self,
            dataset: AnalystDataset,
            data_source: InternalDataSourceType,
            file_size: int = 0,
        ) -> dict[str, object]:
            self.registered.append((dataset, data_source))
            return {"success": True, "msg": ""}

    raw_bytes = "\ufeffdate;amount\r\n2026-01-01;100\r\n".encode()
    upload_file = UploadFile(
        filename="sales.csv",
        file=io.BytesIO(raw_bytes),
        size=len(raw_bytes),
    )
    analyst_db = FakeAnalystDB()

    response = await rest_api.upload_files(
        request=object(),  # type: ignore[arg-type]
        background_tasks=BackgroundTasks(),
        analyst_db=analyst_db,  # type: ignore[arg-type]
        files=[upload_file],
        registry_ids=None,
    )

    assert response == [
        {
            "filename": "sales.csv",
            "content_type": None,
            "size": len(raw_bytes),
            "dataset_name": "sales",
        }
    ]
    registered_dataset, data_source = analyst_db.registered[0]
    assert data_source is InternalDataSourceType.FILE
    assert isinstance(registered_dataset.to_df(), pd.DataFrame)
    assert registered_dataset.to_df().to_dict("records") == [
        {"date": "2026-01-01", "amount": 100},
    ]


def test_load_from_database_registers_placeholders_and_defers_processing() -> None:
    asyncio.run(_assert_load_from_database_registers_placeholders())


async def _assert_load_from_database_registers_placeholders() -> None:
    class FakeAnalystDB:
        def __init__(self) -> None:
            self.registered: list[
                tuple[AnalystDataset, InternalDataSourceType, str | None]
            ] = []

        async def register_dataset(
            self,
            dataset: AnalystDataset,
            data_source: InternalDataSourceType,
            external_id: str | None = None,
        ) -> dict[str, object]:
            self.registered.append((dataset, data_source, external_id))
            return {"success": True, "msg": ""}

    analyst_db = FakeAnalystDB()
    background_tasks = BackgroundTasks()

    result = await rest_api.load_from_database(
        LoadDatabaseRequest(table_names=["sales", "customers"], schema_name="PUBLIC"),
        background_tasks,
        analyst_db,  # type: ignore[arg-type]
    )

    assert result == ["PUBLIC-sales", "PUBLIC-customers"]
    assert [
        (
            dataset.name,
            external_id,
            isinstance(dataset.to_df(), pd.DataFrame),
            dataset.to_df().empty,
        )
        for dataset, data_source, external_id in analyst_db.registered
        if data_source is InternalDataSourceType.DATABASE
    ] == [
        ("PUBLIC-sales", "PUBLIC.sales", True, True),
        ("PUBLIC-customers", "PUBLIC.customers", True, True),
    ]
    assert len(background_tasks.tasks) == 1
    background_task = background_tasks.tasks[0]
    assert background_task.func is rest_api.get_and_process_tables
    assert background_task.args == (
        ["sales", "customers"],
        analyst_db,
        1_000,
        "PUBLIC",
    )


def test_get_and_process_tables_uses_schema_and_processes_loaded_names(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    asyncio.run(_assert_get_and_process_tables_uses_schema(monkeypatch))


def test_get_database_tables_returns_mapping_and_uses_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    asyncio.run(
        _assert_get_database_tables_returns_mapping_and_uses_schema(monkeypatch)
    )


async def _assert_get_database_tables_returns_mapping_and_uses_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: dict[str, object] = {}

    class FakeDatabaseOperator:
        async def get_tables(self) -> list[str]:
            return ["ORDERS", "CUSTOMER"]

    def fake_get_external_database(schema: str | None = None) -> FakeDatabaseOperator:
        calls["schema"] = schema
        return FakeDatabaseOperator()

    monkeypatch.setattr(
        database_router, "get_external_database", fake_get_external_database
    )

    assert await rest_api.get_database_tables(schema="TPCDS_SF100TCL") == {
        "ORDERS": "ORDERS",
        "CUSTOMER": "CUSTOMER",
    }
    assert calls["schema"] == "TPCDS_SF100TCL"


async def _assert_get_and_process_tables_uses_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: dict[str, object] = {}
    analyst_db = object()

    class FakeDatabaseOperator:
        async def get_data(
            self,
            *table_names: str,
            analyst_db: object,
            sample_size: int,
        ) -> list[str]:
            calls["get_data"] = {
                "table_names": table_names,
                "analyst_db": analyst_db,
                "sample_size": sample_size,
            }
            return ["PUBLIC-sales", "PUBLIC-customers"]

    def fake_get_external_database(schema: str | None = None) -> FakeDatabaseOperator:
        calls["schema"] = schema
        return FakeDatabaseOperator()

    async def fake_process_and_update(
        dataset_names: list[str],
        analyst_db: object,
        datasource_type: InternalDataSourceType,
    ) -> None:
        calls["process"] = {
            "dataset_names": dataset_names,
            "analyst_db": analyst_db,
            "datasource_type": datasource_type,
        }

    monkeypatch.setattr(
        database_router, "get_external_database", fake_get_external_database
    )
    monkeypatch.setattr(database_router, "process_and_update", fake_process_and_update)

    await rest_api.get_and_process_tables(["raw_sales"], analyst_db, 25, "PUBLIC")

    assert calls["schema"] == "PUBLIC"
    assert calls["get_data"] == {
        "table_names": ("raw_sales",),
        "analyst_db": analyst_db,
        "sample_size": 25,
    }
    assert calls["process"] == {
        "dataset_names": ["PUBLIC-sales", "PUBLIC-customers"],
        "analyst_db": analyst_db,
        "datasource_type": InternalDataSourceType.DATABASE,
    }
