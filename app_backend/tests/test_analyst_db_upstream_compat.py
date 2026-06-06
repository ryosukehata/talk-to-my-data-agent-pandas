import asyncio
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
)
from utils.schema import AnalystDataset


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


def test_analyst_db_dataset_roundtrip_preserves_pandas(tmp_path) -> None:
    asyncio.run(_assert_analyst_db_dataset_roundtrip_preserves_pandas(tmp_path))


async def _assert_analyst_db_dataset_roundtrip_preserves_pandas(tmp_path) -> None:
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
    restored = await analyst_db.get_dataset("sales")
    metadata = await analyst_db.get_dataset_metadata("sales")

    assert result == {"success": True, "msg": ""}
    assert isinstance(restored.to_df(), pd.DataFrame)
    pd.testing.assert_frame_equal(restored.to_df(), source_df)
    assert metadata.model_dump(mode="json")["data_source"] == "file"
