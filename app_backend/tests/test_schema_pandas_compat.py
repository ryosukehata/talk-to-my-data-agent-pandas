import asyncio
import io
from datetime import datetime, timezone

import pandas as pd
from openpyxl import load_workbook
from utils.analyst_db import DatasetMetadata, DatasetType, InternalDataSourceType
from utils.schema import (
    AnalystChatMessage,
    DataDictionary,
    RunAnalysisResult,
    RunAnalysisResultMetadata,
)


def test_data_dictionary_from_analyst_df_stringifies_tuple_columns() -> None:
    df = pd.DataFrame(
        [[100, 200]],
        columns=pd.Index(
            [
                ("black_friday", 0.0),
                ("holiday", 1.0),
            ]
        ),
    )

    dictionary = DataDictionary.from_analyst_df(df)

    assert [column.column for column in dictionary.column_descriptions] == [
        "('black_friday', 0.0)",
        "('holiday', 1.0)",
    ]
    assert [column.data_type for column in dictionary.column_descriptions] == [
        "int64",
        "int64",
    ]


def test_analysis_result_download_uses_pandas_csv_writer() -> None:
    asyncio.run(_assert_analysis_result_download_uses_pandas_csv_writer())


async def _assert_analysis_result_download_uses_pandas_csv_writer() -> None:
    from core.routers.datasets import download_dataset

    analyst_db = _FakeAnalystDB()

    response = await download_dataset(
        dataset_id="dataset-123456789",
        analyst_db=analyst_db,  # type: ignore[arg-type]
        bom=True,
    )

    csv_text = response.body.decode("utf-8")
    assert csv_text == "\ufeffamount,label\n10,A\n20,B\n"


def test_chat_excel_export_writes_pandas_analysis_result_sheet() -> None:
    asyncio.run(_assert_chat_excel_export_writes_pandas_analysis_result_sheet())


async def _assert_chat_excel_export_writes_pandas_analysis_result_sheet() -> None:
    from core.routers.chats import save_chat_messages

    analyst_db = _FakeAnalystDB()

    response = await save_chat_messages(
        request=None,  # type: ignore[arg-type]
        chat_id="chat-1",
        analyst_db=analyst_db,  # type: ignore[arg-type]
    )
    chunks: list[bytes] = []
    async for chunk in response.body_iterator:
        chunks.append(chunk if isinstance(chunk, bytes) else chunk.encode("utf-8"))
    body = b"".join(chunks)
    workbook = load_workbook(io.BytesIO(body), read_only=True)

    assert "Data" in workbook.sheetnames
    data_sheet = workbook["Data"]
    assert data_sheet["A1"].value == "amount"
    assert data_sheet["B1"].value == "label"
    assert data_sheet["A2"].value == 10
    assert data_sheet["B2"].value == "A"


class _FakeDatasetHandler:
    async def get_dataframe(
        self,
        dataset_id: str,
        expected_type: DatasetType,
        max_rows: int | None = None,
    ) -> pd.DataFrame:
        assert dataset_id == "dataset-123456789"
        assert expected_type is DatasetType.ANALYST_RESULT_DATASET
        assert max_rows is None
        return pd.DataFrame({"amount": [10, 20], "label": ["A", "B"]})

    async def get_dataset_metadata(self, dataset_id: str) -> DatasetMetadata:
        assert dataset_id == "dataset-123456789"
        return DatasetMetadata(
            name=dataset_id,
            external_id=dataset_id,
            dataset_type=DatasetType.ANALYST_RESULT_DATASET,
            original_name="analysis_result",
            created_at=datetime(2026, 6, 28, tzinfo=timezone.utc),
            columns=["amount", "label"],
            original_column_types=None,
            row_count=2,
            data_source=InternalDataSourceType.GENERATED,
        )


class _FakeAnalystDB:
    def __init__(self) -> None:
        self.dataset_handler = _FakeDatasetHandler()

    async def get_chat_messages(self, chat_id: str) -> list[AnalystChatMessage]:
        assert chat_id == "chat-1"
        return [
            AnalystChatMessage(
                id="user-1",
                role="user",
                content="sum amount",
                components=[],
                in_progress=False,
            ),
            AnalystChatMessage(
                id="assistant-1",
                role="assistant",
                content="analysis",
                components=[
                    RunAnalysisResult(
                        status="success",
                        dataset_id="dataset-123456789",
                        metadata=RunAnalysisResultMetadata(
                            duration=0,
                            attempts=1,
                            datasets_analyzed=1,
                        ),
                    )
                ],
                in_progress=False,
            ),
        ]
