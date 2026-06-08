import asyncio
import os
from types import SimpleNamespace
from typing import Any

import pandas as pd
from openai.types.chat.chat_completion_system_message_param import (
    ChatCompletionSystemMessageParam,
)
from pydantic import BaseModel, ValidationError

os.environ.setdefault("DATAROBOT_API_TOKEN", "test-token")
os.environ.setdefault("DATAROBOT_ENDPOINT", "https://example.com")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")

from utils import api
from utils.schema import (
    AnalystDataset,
    DataDictionary,
    GetBusinessAnalysisRequest,
    RunAnalysisRequest,
    RunChartsRequest,
    RunDatabaseAnalysisRequest,
)


class _RequiredCode(BaseModel):
    code: str


def _validation_error() -> ValidationError:
    try:
        _RequiredCode.model_validate({})
    except ValidationError as error:
        return error
    raise AssertionError("Expected pydantic validation to fail")


def _exception_stderr(result: Any) -> str:
    assert result.metadata is not None
    assert result.metadata.exception is not None
    assert result.metadata.exception.exception_history is not None
    exception = result.metadata.exception.exception_history[0]
    assert exception.stderr is not None
    return exception.stderr


def test_run_analysis_converts_llm_validation_error(monkeypatch) -> None:
    asyncio.run(_assert_run_analysis_converts_llm_validation_error(monkeypatch))


async def _assert_run_analysis_converts_llm_validation_error(monkeypatch) -> None:
    async def fake_run_analysis(*args, **kwargs) -> api.RunAnalysisResult:
        raise _validation_error()

    monkeypatch.setattr(api, "_run_analysis", fake_run_analysis)

    result = await api.run_analysis(
        RunAnalysisRequest(dataset_names=["sales"], question="sum amount"),
        analyst_db=object(),  # type: ignore[arg-type]
    )

    assert result.status == "error"
    assert "Unable to complete the analysis" in _exception_stderr(result)


def test_run_charts_converts_llm_validation_error(monkeypatch) -> None:
    asyncio.run(_assert_run_charts_converts_llm_validation_error(monkeypatch))


async def _assert_run_charts_converts_llm_validation_error(monkeypatch) -> None:
    async def fake_run_charts(*args, **kwargs) -> api.RunChartsResult:
        raise _validation_error()

    monkeypatch.setattr(api, "_run_charts", fake_run_charts)

    result = await api.run_charts(
        RunChartsRequest(
            dataset=AnalystDataset(data=pd.DataFrame({"amount": [100, 200]})),
            question="chart amount",
        )
    )

    assert result.status == "error"
    assert "Unable to generate charts" in _exception_stderr(result)


def test_get_business_analysis_converts_llm_validation_error(monkeypatch) -> None:
    asyncio.run(
        _assert_get_business_analysis_converts_llm_validation_error(monkeypatch)
    )


async def _assert_get_business_analysis_converts_llm_validation_error(
    monkeypatch,
) -> None:
    class FakeCompletions:
        async def create_with_completion(self, **kwargs) -> tuple[Any, Any]:
            raise _validation_error()

    class FakeLLMClient:
        def __init__(self, *args, **kwargs) -> None:
            self.chat = SimpleNamespace(completions=FakeCompletions())

        async def __aenter__(self) -> "FakeLLMClient":
            return self

        async def __aexit__(self, *args) -> None:
            return None

    monkeypatch.setattr(api, "AsyncLLMClient", FakeLLMClient)

    dataset = AnalystDataset(data=pd.DataFrame({"amount": [100, 200]}))
    result = await api.get_business_analysis(
        GetBusinessAnalysisRequest(
            dataset=dataset,
            dictionary=DataDictionary.from_analyst_df(dataset.to_df()),
            question="summarize amount",
        )
    )

    assert result.status == "error"
    assert "Unable to generate business insights" in _exception_stderr(result)


def test_generate_database_analysis_code_converts_llm_validation_error(
    monkeypatch,
) -> None:
    asyncio.run(
        _assert_generate_database_analysis_code_converts_llm_validation_error(
            monkeypatch
        )
    )


async def _assert_generate_database_analysis_code_converts_llm_validation_error(
    monkeypatch,
) -> None:
    class FakeAnalystDB:
        async def get_data_dictionary(self, name: str) -> DataDictionary:
            return DataDictionary.from_analyst_df(
                pd.DataFrame({"amount": [100]}),
                name=name,
            )

        async def get_dataset_metadata(self, name: str) -> SimpleNamespace:
            return SimpleNamespace(original_column_types={"amount": "INTEGER"})

        async def get_dataset(self, name: str) -> AnalystDataset:
            return AnalystDataset(
                name=name,
                data=pd.DataFrame({"amount": [100]}),
            )

    class FakeDatabase:
        def query_friendly_name(self, dataset_name: str) -> str:
            return dataset_name

        def get_system_prompt(self) -> ChatCompletionSystemMessageParam:
            return ChatCompletionSystemMessageParam(
                role="system",
                content="Generate SQL",
            )

    class FakeCompletions:
        async def create_with_completion(self, **kwargs) -> tuple[Any, Any]:
            raise _validation_error()

    class FakeLLMClient:
        def __init__(self, *args, **kwargs) -> None:
            self.chat = SimpleNamespace(completions=FakeCompletions())

        async def __aenter__(self) -> "FakeLLMClient":
            return self

        async def __aexit__(self, *args) -> None:
            return None

    monkeypatch.setattr(api, "AsyncLLMClient", FakeLLMClient)

    try:
        await api._generate_database_analysis_code(
            FakeDatabase(),  # type: ignore[arg-type]
            RunDatabaseAnalysisRequest(
                dataset_names=["PUBLIC.sales"],
                question="sum amount",
            ),
            FakeAnalystDB(),  # type: ignore[arg-type]
        )
    except ValueError as error:
        assert "Unable to analyze your data" in str(error)
    else:
        raise AssertionError("Expected database analysis generation to fail")
