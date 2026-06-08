import asyncio
import logging
import os
from datetime import datetime, timezone

import pandas as pd

os.environ.setdefault("DATAROBOT_API_TOKEN", "test-token")
os.environ.setdefault("DATAROBOT_ENDPOINT", "https://example.com")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")

from utils.analyst_db import (
    AnalystDB,
    DatasetMetadata,
    DatasetType,
    InternalDataSourceType,
    get_data_source_type,
)
from utils.schema import AnalystDataset


def test_get_data_source_type_accepts_internal_string_values() -> None:
    assert get_data_source_type("file") is InternalDataSourceType.FILE


def test_dataset_metadata_model_dump_serializes_public_fields() -> None:
    metadata = DatasetMetadata(
        name="sales",
        external_id="dataset-id",
        dataset_type=DatasetType.STANDARD,
        original_name="sales.csv",
        created_at=datetime(2026, 6, 6, 12, 0, tzinfo=timezone.utc),
        columns=["date", "amount"],
        original_column_types={"date": "DATE", "amount": "INTEGER"},
        row_count=2,
        data_source="file",
        file_size=128,
    )

    dumped = metadata.model_dump(mode="json")

    assert metadata.data_source is InternalDataSourceType.FILE
    assert dumped["created_at"] == "2026-06-06T12:00:00Z"
    assert dumped["dataset_type"] == "standard"
    assert dumped["data_source"] == "file"


def test_analyst_db_dataset_roundtrip_preserves_pandas(tmp_path, caplog) -> None:
    asyncio.run(_assert_analyst_db_dataset_roundtrip_preserves_pandas(tmp_path, caplog))


async def _assert_analyst_db_dataset_roundtrip_preserves_pandas(
    tmp_path,
    caplog,
) -> None:
    analyst_db = await AnalystDB.create(user_id="user-1", db_path=tmp_path)
    source_df = pd.DataFrame(
        {
            "date": pd.date_range("2026-01-01", periods=2),
            "amount": [100, 200],
        }
    )
    dataset = AnalystDataset(name="sales", data=source_df)

    result = await analyst_db.register_dataset(
        dataset,
        data_source=InternalDataSourceType.FILE,
    )
    with caplog.at_level(logging.DEBUG, logger="ApplicationDB"):
        restored = await analyst_db.get_dataset("sales")
    metadata = await analyst_db.get_dataset_metadata("sales")

    assert result == {"success": True, "msg": ""}
    assert isinstance(restored.to_df(), pd.DataFrame)
    pd.testing.assert_frame_equal(restored.to_df(), source_df)
    assert metadata.model_dump(mode="json")["data_source"] == "file"
    assert any(
        record.levelno == logging.DEBUG
        and record.getMessage() == "Retrieving dataframe sales"
        for record in caplog.records
    )


def test_register_dataset_failure_logs_exception_info(caplog) -> None:
    asyncio.run(_assert_register_dataset_failure_logs_exception_info(caplog))


async def _assert_register_dataset_failure_logs_exception_info(caplog) -> None:
    class FailingDatasetHandler:
        async def register_dataframe(self, *args, **kwargs) -> None:
            raise RuntimeError("boom")

    analyst_db = AnalystDB.__new__(AnalystDB)
    analyst_db.dataset_handler = FailingDatasetHandler()
    dataset = AnalystDataset(name="sales", data=pd.DataFrame({"amount": [100]}))

    with caplog.at_level(logging.ERROR, logger="ApplicationDB"):
        result = await analyst_db.register_dataset(
            dataset,
            data_source=InternalDataSourceType.FILE,
        )

    assert result == {
        "success": False,
        "msg": "Error registering dataset 'sales': boom",
    }
    records = [
        record
        for record in caplog.records
        if record.levelno == logging.ERROR
        and record.getMessage() == "Error registering dataset: boom"
    ]
    assert records
    assert records[-1].exc_info is not None


def test_get_data_dictionary_missing_dataset_logs_debug(caplog) -> None:
    asyncio.run(_assert_get_data_dictionary_missing_dataset_logs_debug(caplog))


async def _assert_get_data_dictionary_missing_dataset_logs_debug(caplog) -> None:
    class MissingDictionaryHandler:
        async def get_dataframe(self, *args, **kwargs) -> pd.DataFrame:
            raise ValueError("missing")

    analyst_db = AnalystDB.__new__(AnalystDB)
    analyst_db.dataset_handler = MissingDictionaryHandler()

    with caplog.at_level(logging.DEBUG, logger="ApplicationDB"):
        result = await analyst_db.get_data_dictionary("sales")

    assert result is None
    assert any(
        record.levelno == logging.DEBUG
        and record.getMessage() == "Data dictionary not defined sales"
        for record in caplog.records
    )
    assert not any(
        record.levelno >= logging.ERROR
        and "Failed to get data dictionary sales" in record.getMessage()
        for record in caplog.records
    )
