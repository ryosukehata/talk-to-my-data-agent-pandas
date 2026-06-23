import ast
import asyncio
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
from datarobot_genai.core.utils.token_tracking import (
    TiktokenCountingStrategy,
    TokenUsageTracker,
)

os.environ.setdefault("DATAROBOT_API_TOKEN", "test-token")
os.environ.setdefault("DATAROBOT_ENDPOINT", "https://example.com")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")

from utils import api
from utils.analyst_db import (
    DatasetMetadata,
    DatasetType,
    ExternalDataStoreNameDataSourceType,
    InternalDataSourceType,
)
from utils.credentials import NoDatabaseCredentials
from utils.database_helpers import NoDatabaseOperator
from utils.schema import (
    AnalystChatMessage,
    AnalystDataset,
    ChatRequest,
    RunAnalysisRequest,
    RunAnalysisResult,
    RunAnalysisResultMetadata,
    RunDatabaseAnalysisResult,
    RunDatabaseAnalysisResultMetadata,
)


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


def _dataset_metadata_for_source(
    name: str,
    data_source: InternalDataSourceType | ExternalDataStoreNameDataSourceType,
    external_id: str | None = None,
) -> DatasetMetadata:
    metadata = _dataset_metadata(name)
    metadata.data_source = data_source
    metadata.external_id = external_id
    return metadata


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


def test_summarize_conversation_uses_upstream_create_call(monkeypatch) -> None:
    asyncio.run(_assert_summarize_conversation_uses_upstream_create_call(monkeypatch))


async def _assert_summarize_conversation_uses_upstream_create_call(monkeypatch):
    class FakeCompletion:
        def __init__(self) -> None:
            self.kwargs = None
            self.create_with_completion_called = False

        async def create(self, **kwargs):
            self.kwargs = kwargs
            response_model = kwargs["response_model"]
            return response_model(summary="要約しました")

        async def create_with_completion(self, **kwargs):
            self.create_with_completion_called = True
            raise AssertionError(
                "summarize_conversation should match upstream create()"
            )

    fake_completion = FakeCompletion()

    class FakeChat:
        completions = fake_completion

    class FakeLLMClient:
        async def __aenter__(self):
            return type("Client", (), {"chat": FakeChat()})()

        async def __aexit__(self, *args):
            return None

    monkeypatch.setattr(api, "AsyncLLMClient", lambda **_: FakeLLMClient())

    summary = await api.summarize_conversation(
        [
            {"role": "user", "content": "売上を集計して"},
            {"role": "assistant", "content": "集計しました"},
        ]
    )

    assert summary == "要約しました"
    assert fake_completion.kwargs is not None
    assert fake_completion.kwargs["timeout"] == 900
    assert fake_completion.create_with_completion_called is False


def test_core_api_create_with_completion_calls_unpack_response_and_raw() -> None:
    tree = ast.parse(Path(api.__file__).read_text(encoding="utf-8"))
    parents: dict[ast.AST, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent

    targets: list[tuple[int, ast.AST | None]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Await):
            continue
        call = node.value
        if not isinstance(call, ast.Call):
            continue
        if not (
            isinstance(call.func, ast.Attribute)
            and call.func.attr == "create_with_completion"
        ):
            continue

        current = node
        while current in parents and isinstance(
            parents[current], ast.Tuple | ast.Expr | ast.Await | ast.Call
        ):
            current = parents[current]
        parent = parents.get(current, parents.get(node))
        target = None
        if isinstance(parent, ast.Assign):
            target = parent.targets[0]
        elif isinstance(parent, ast.AnnAssign):
            target = parent.target
        targets.append((node.lineno, target))

    assert targets
    assert all(
        isinstance(target, ast.Tuple) and len(target.elts) == 2 for _, target in targets
    ), [
        (line_number, ast.unparse(target) if target is not None else None)
        for line_number, target in targets
    ]


def test_run_complete_analysis_passes_tracker_and_telemetry_to_run_analysis(
    monkeypatch,
) -> None:
    asyncio.run(
        _assert_run_complete_analysis_passes_tracker_and_telemetry_to_run_analysis(
            monkeypatch
        )
    )


async def _assert_run_complete_analysis_passes_tracker_and_telemetry_to_run_analysis(
    monkeypatch,
) -> None:
    class FakeAnalystDB:
        def __init__(self) -> None:
            self.user_message = AnalystChatMessage(
                id="user-1",
                role="user",
                content="sum amount",
                components=[],
                in_progress=True,
            )
            self.updates: list[AnalystChatMessage] = []

        async def get_chat_message(self, message_id: str) -> AnalystChatMessage | None:
            if message_id == "user-1":
                return self.user_message
            return None

        async def add_chat_message(
            self, chat_id: str, message: AnalystChatMessage
        ) -> str:
            assert chat_id == "chat-1"
            message.id = "assistant-1"
            return message.id

        async def update_chat_message(
            self, message_id: str, message: AnalystChatMessage
        ) -> None:
            self.updates.append(message.model_copy(deep=True))

    telemetry_json = {"request_id": "telemetry-1"}
    run_analysis_kwargs: dict[str, Any] = {}

    async def fake_rephrase_message(*args, **kwargs) -> str:
        return "enhanced question"

    async def fake_run_analysis(*args, **kwargs) -> RunAnalysisResult:
        run_analysis_kwargs.update(kwargs)
        return RunAnalysisResult(
            status="success",
            dataset=AnalystDataset(
                name="analysis_result",
                data=pd.DataFrame({"total_amount": [300]}),
            ),
            metadata=RunAnalysisResultMetadata(
                duration=0,
                attempts=1,
                datasets_analyzed=1,
            ),
        )

    async def fake_extract_and_store_datasets(
        analyst_db: FakeAnalystDB,
        assistant_message: AnalystChatMessage,
    ) -> AnalystChatMessage:
        return assistant_message

    monkeypatch.setattr(api, "rephrase_message", fake_rephrase_message)
    monkeypatch.setattr(api, "run_analysis", fake_run_analysis)
    monkeypatch.setattr(
        api, "extract_and_store_datasets", fake_extract_and_store_datasets
    )

    results = [
        component
        async for component in api.run_complete_analysis(
            chat_request=ChatRequest(
                messages=[{"role": "user", "content": "sum amount"}]
            ),
            data_source=InternalDataSourceType.FILE,
            dataset_metadata=[_dataset_metadata("sales")],
            analyst_db=FakeAnalystDB(),  # type: ignore[arg-type]
            chat_id="chat-1",
            message_id="user-1",
            request=None,
            enable_chart_generation=False,
            enable_business_insights=False,
            telemetry_json=telemetry_json,
        )
    ]

    assert results[0] == "enhanced question"
    assert isinstance(results[1], RunAnalysisResult)
    assert run_analysis_kwargs["telemetry_json"] is telemetry_json
    assert run_analysis_kwargs["token_tracker"] is not None
    assert (
        run_analysis_kwargs["token_tracker"]
        is run_analysis_kwargs["analysis_context"].token_tracker
    )


@pytest.mark.parametrize(
    "case_name",
    ["database", "external_data_store", "remote_registry"],
)
def test_run_complete_analysis_passes_telemetry_to_database_analysis_paths(
    monkeypatch,
    case_name: str,
) -> None:
    asyncio.run(
        _assert_run_complete_analysis_passes_telemetry_to_database_analysis_paths(
            monkeypatch,
            case_name,
        )
    )


async def _assert_run_complete_analysis_passes_telemetry_to_database_analysis_paths(
    monkeypatch,
    case_name: str,
) -> None:
    class FakeAnalystDB:
        def __init__(self) -> None:
            self.user_message = AnalystChatMessage(
                id="user-1",
                role="user",
                content="sum amount",
                components=[],
                in_progress=True,
            )

        async def get_chat_message(self, message_id: str) -> AnalystChatMessage | None:
            if message_id == "user-1":
                return self.user_message
            return None

        async def add_chat_message(
            self, chat_id: str, message: AnalystChatMessage
        ) -> str:
            message.id = "assistant-1"
            return message.id

        async def update_chat_message(
            self, message_id: str, message: AnalystChatMessage
        ) -> None:
            return None

    class FakeRecipe:
        async def refresh(self) -> bool:
            return False

        def as_database_operator(self) -> object:
            return object()

    async def fake_rephrase_message(*args, **kwargs) -> str:
        return "enhanced question"

    async def fake_extract_and_store_datasets(
        analyst_db: FakeAnalystDB,
        assistant_message: AnalystChatMessage,
    ) -> AnalystChatMessage:
        return assistant_message

    run_database_analysis_kwargs: dict[str, Any] = {}

    async def fake_run_database_analysis(*args, **kwargs) -> RunDatabaseAnalysisResult:
        run_database_analysis_kwargs.update(kwargs)
        return RunDatabaseAnalysisResult(
            status="success",
            dataset=AnalystDataset(
                name="database_result",
                data=pd.DataFrame({"total_amount": [300]}),
            ),
            metadata=RunDatabaseAnalysisResultMetadata(
                duration=0,
                attempts=1,
                datasets_analyzed=1,
            ),
        )

    monkeypatch.setattr(api, "rephrase_message", fake_rephrase_message)
    monkeypatch.setattr(api, "run_database_analysis", fake_run_database_analysis)
    monkeypatch.setattr(
        api,
        "extract_and_store_datasets",
        fake_extract_and_store_datasets,
    )

    if case_name == "database":
        data_source = InternalDataSourceType.DATABASE
        dataset_metadata = [
            _dataset_metadata_for_source("sales", InternalDataSourceType.DATABASE)
        ]
    elif case_name == "external_data_store":
        data_source = ExternalDataStoreNameDataSourceType.from_name("warehouse")
        dataset_metadata = [_dataset_metadata_for_source("sales", data_source)]

        async def fake_get_data_store_id(name: str) -> str:
            assert name == "warehouse"
            return "data-store-id"

        async def fake_load_or_create(*args, **kwargs) -> FakeRecipe:
            return FakeRecipe()

        monkeypatch.setattr(
            api.DataSourceRecipe,
            "get_id_for_data_store_canonical_name",
            staticmethod(fake_get_data_store_id),
        )
        monkeypatch.setattr(
            api.DataSourceRecipe,
            "load_or_create",
            staticmethod(fake_load_or_create),
        )
    elif case_name == "remote_registry":
        data_source = InternalDataSourceType.REMOTE_REGISTRY
        dataset_metadata = [
            _dataset_metadata_for_source(
                "sales",
                InternalDataSourceType.REMOTE_REGISTRY,
                external_id="remote-dataset-id",
            )
        ]

        monkeypatch.setattr(
            api.DatasetSparkRecipe,
            "should_use_spark_recipe",
            staticmethod(lambda: True),
        )

        async def fake_load_or_create_spark_recipe(*args, **kwargs) -> FakeRecipe:
            return FakeRecipe()

        monkeypatch.setattr(
            api,
            "load_or_create_spark_recipe",
            fake_load_or_create_spark_recipe,
        )
    else:
        raise AssertionError(f"Unexpected case: {case_name}")

    telemetry_json = {"request_id": f"telemetry-{case_name}"}

    results = [
        component
        async for component in api.run_complete_analysis(
            chat_request=ChatRequest(
                messages=[{"role": "user", "content": "sum amount"}]
            ),
            data_source=data_source,
            dataset_metadata=dataset_metadata,
            analyst_db=FakeAnalystDB(),  # type: ignore[arg-type]
            chat_id="chat-1",
            message_id="user-1",
            request=None,
            enable_chart_generation=False,
            enable_business_insights=False,
            telemetry_json=telemetry_json,
        )
    ]

    assert results[0] == "enhanced question"
    assert isinstance(results[1], RunDatabaseAnalysisResult)
    assert run_database_analysis_kwargs["telemetry_json"] is telemetry_json
    assert run_database_analysis_kwargs["token_tracker"] is not None


def test_all_database_analysis_calls_pass_telemetry_json() -> None:
    assert api.__file__ is not None
    api_tree = ast.parse(Path(api.__file__).read_text())
    database_analysis_functions = {
        "run_database_analysis",
        "_run_database_analysis",
        "_generate_database_analysis_code",
    }
    missing_telemetry_lines: dict[str, list[int]] = {
        function_name: [] for function_name in database_analysis_functions
    }

    for node in ast.walk(api_tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Name):
            continue
        if node.func.id not in database_analysis_functions:
            continue
        if not any(keyword.arg == "telemetry_json" for keyword in node.keywords):
            missing_telemetry_lines[node.func.id].append(node.lineno)

    assert missing_telemetry_lines == {
        function_name: [] for function_name in database_analysis_functions
    }


def test_run_database_analysis_passes_generator_context_without_argument_shift(
    monkeypatch,
) -> None:
    asyncio.run(
        _assert_run_database_analysis_passes_generator_context_without_argument_shift(
            monkeypatch
        )
    )


async def _assert_run_database_analysis_passes_generator_context_without_argument_shift(
    monkeypatch,
) -> None:
    class FakeDatabase:
        async def execute_query(self, query: str) -> list[dict[str, int]]:
            assert query == "select 300 as total_amount"
            return [{"total_amount": 300}]

    async def fake_generate_database_analysis_code(
        database: FakeDatabase,
        request: api.RunDatabaseAnalysisRequest,
        analyst_db: object,
        validation_error: object | None = None,
        token_tracker: TokenUsageTracker | None = None,
        telemetry_json: dict[str, Any] | None = None,
    ) -> str:
        call_context.update(
            {
                "database": database,
                "request": request,
                "analyst_db": analyst_db,
                "validation_error": validation_error,
                "token_tracker": token_tracker,
                "telemetry_json": telemetry_json,
            }
        )
        return "select 300 as total_amount"

    call_context: dict[str, object | None] = {}
    fake_database = FakeDatabase()
    fake_analyst_db = object()
    token_tracker = TokenUsageTracker(strategy=TiktokenCountingStrategy())
    telemetry_json = {"request_id": "database-telemetry"}
    request = api.RunDatabaseAnalysisRequest(
        dataset_names=["PUBLIC.sales"],
        question="sum amount",
    )

    monkeypatch.setattr(
        api,
        "_generate_database_analysis_code",
        fake_generate_database_analysis_code,
    )

    result = await api.run_database_analysis(
        request=request,
        analyst_db=fake_analyst_db,  # type: ignore[arg-type]
        database_override=fake_database,  # type: ignore[arg-type]
        token_tracker=token_tracker,
        telemetry_json=telemetry_json,
    )

    assert result.status == "success"
    assert result.dataset is not None
    assert result.dataset.to_df().to_dict("records") == [{"total_amount": 300}]
    assert call_context == {
        "database": fake_database,
        "request": request,
        "analyst_db": fake_analyst_db,
        "validation_error": None,
        "token_tracker": token_tracker,
        "telemetry_json": telemetry_json,
    }
