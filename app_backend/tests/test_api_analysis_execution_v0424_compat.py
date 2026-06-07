import asyncio
import os
from datetime import datetime, timezone
from typing import Any

import pandas as pd

os.environ.setdefault("DATAROBOT_API_TOKEN", "test-token")
os.environ.setdefault("DATAROBOT_ENDPOINT", "https://example.com")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")

from utils import api
from utils.analyst_db import DatasetMetadata, DatasetType, InternalDataSourceType
from utils.credentials import NoDatabaseCredentials
from utils.database_helpers import NoDatabaseOperator
from utils.schema import (
    AnalystChatMessage,
    AnalystDataset,
    ChatRequest,
    RunAnalysisRequest,
)
from utils.token_tracking import TiktokenCountingStrategy, TokenUsageTracker


def _dataset_metadata(name: str) -> DatasetMetadata:
    return DatasetMetadata(
        name=name,
        external_id=None,
        dataset_type=DatasetType.STANDARD,
        original_name=name,
        created_at=datetime(2026, 6, 7, tzinfo=timezone.utc),
        columns=["amount"],
        original_column_types=None,
        row_count=2,
        data_source=InternalDataSourceType.FILE,
    )


def _analysis_context(analyst_db: Any) -> api.RunCompleteAnalysisRequestContext:
    context = api.RunCompleteAnalysisRequestContext(
        chat_request=ChatRequest(messages=[{"role": "user", "content": "sum amount"}]),
        request=None,
        data_source=InternalDataSourceType.FILE,
        dataset_metadata=[_dataset_metadata("sales")],
        analyst_db=analyst_db,
        chat_id="chat-1",
        user_message_id="user-1",
        enable_chart_generation=False,
        enable_business_insights=False,
        token_tracker=TokenUsageTracker(strategy=TiktokenCountingStrategy()),
    )
    context.assistant_message_id = "assistant-1"
    context.assistant_message = AnalystChatMessage(
        role="assistant",
        content="",
        components=[],
        in_progress=True,
    )
    return context


def test_stage_message_update_persists_ordered_message_snapshots() -> None:
    asyncio.run(_assert_stage_message_update_persists_ordered_snapshots())


async def _assert_stage_message_update_persists_ordered_snapshots() -> None:
    class FakeAnalystDB:
        def __init__(self) -> None:
            self.updates: list[AnalystChatMessage] = []

        async def update_chat_message(
            self, message_id: str, message: AnalystChatMessage
        ) -> None:
            await asyncio.sleep(0)
            assert message_id == "assistant-1"
            self.updates.append(message.model_copy(deep=True))

    analyst_db = FakeAnalystDB()
    context = _analysis_context(analyst_db)

    assert context.assistant_message is not None
    context.assistant_message.step_value = "GENERATING_QUERY"
    context.stage_message_update()
    context.assistant_message.step_value = "RUNNING_QUERY"
    context.stage_message_update()

    await context.await_message_update()

    assert [message.step_value for message in analyst_db.updates] == [
        "GENERATING_QUERY",
        "RUNNING_QUERY",
    ]


def test_run_analysis_updates_execution_steps_and_preserves_pandas(
    monkeypatch,
) -> None:
    asyncio.run(_assert_run_analysis_updates_steps_and_preserves_pandas(monkeypatch))


async def _assert_run_analysis_updates_steps_and_preserves_pandas(monkeypatch) -> None:
    class FakeAnalystDB:
        def __init__(self) -> None:
            self.updates: list[AnalystChatMessage] = []

        async def update_chat_message(
            self, message_id: str, message: AnalystChatMessage
        ) -> None:
            assert message_id == "assistant-1"
            self.updates.append(message.model_copy(deep=True))

        async def get_cleansed_dataset(
            self, dataset_name: str, max_rows: int | None = None
        ) -> AnalystDataset:
            raise ValueError("no cleansed dataset")

        async def get_dataset(
            self, dataset_name: str, max_rows: int | None = None
        ) -> AnalystDataset:
            assert dataset_name == "sales"
            assert max_rows is None
            return AnalystDataset(
                name="sales",
                data=pd.DataFrame({"amount": [100, 200]}),
            )

    async def fake_generate_run_analysis_python_code(*args, **kwargs) -> str:
        return "def analyze_data(datasets): ..."

    def fake_execute_python(**kwargs) -> AnalystDataset:
        assert "pl" not in kwargs["modules"]
        assert "polars" not in kwargs["allowed_modules"]
        input_data = kwargs["input_data"]
        assert isinstance(input_data["sales"], pd.DataFrame)
        return AnalystDataset(
            name="analysis_result",
            data=pd.DataFrame({"total_amount": [300]}),
        )

    monkeypatch.setattr(
        api,
        "_generate_run_analysis_python_code",
        fake_generate_run_analysis_python_code,
    )
    monkeypatch.setattr(api, "execute_python", fake_execute_python)

    analyst_db = FakeAnalystDB()
    context = _analysis_context(analyst_db)

    result = await api.run_analysis(
        RunAnalysisRequest(dataset_names=["sales"], question="sum amount"),
        analysis_context=context,
    )

    await context.await_message_update()

    assert result.status == "success"
    assert result.dataset is not None
    assert isinstance(result.dataset.to_df(), pd.DataFrame)
    assert result.dataset.to_df().to_dict("records") == [{"total_amount": 300}]
    assert [message.step_value for message in analyst_db.updates] == [
        "GENERATING_QUERY",
        "RUNNING_QUERY",
    ]


def test_no_database_operator_supports_noop_warmup() -> None:
    operator = NoDatabaseOperator(NoDatabaseCredentials())

    assert operator.warmup_query() is None
    assert asyncio.run(operator.warmup()) is None
