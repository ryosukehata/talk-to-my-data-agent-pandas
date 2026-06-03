import asyncio
from types import TracebackType
from typing import Any

import pytest
from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam
from openai.types.chat.chat_completion_user_message_param import (
    ChatCompletionUserMessageParam,
)
from utils.customize.domain.report.domain import (
    ReportQuestionsGenerationRequest,
    ReportQuestionsGenerationResult,
)
from utils.customize.infrastructure.llm import llm as refiner_llm
from utils.customize.infrastructure.llm import report_questions_generator
from utils.customize.usecase.prompt.builder import IRefinerDataInfoMessageFactory
from utils.customize.usecase.report.generate_questions import GenerateQuestionsUseCase
from utils.token_tracking import TokenUsageTracker


class _SlowCompletions:
    async def create_with_completion(self, **_: Any) -> tuple[Any, None]:
        await asyncio.sleep(1)
        return None, None


class _SlowLLMClient:
    def __init__(self, **_: Any) -> None:
        self.chat = type("Chat", (), {"completions": _SlowCompletions()})()

    async def __aenter__(self) -> "_SlowLLMClient":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None


class _EmptyDataInfoFactory(IRefinerDataInfoMessageFactory):
    async def build_dictionary_data(self) -> ChatCompletionMessageParam:
        return ChatCompletionUserMessageParam(role="user", content="")

    async def build_data_shape_info(self) -> ChatCompletionMessageParam:
        return ChatCompletionUserMessageParam(role="user", content="")

    async def build_sample_data_info(self) -> ChatCompletionMessageParam:
        return ChatCompletionUserMessageParam(role="user", content="")


class _TimeoutQuestionsService(
    report_questions_generator.IReportQuestionsGenerationService
):
    async def generate(
        self,
        messages: list[ChatCompletionMessageParam],
        token_tracker: TokenUsageTracker | None = None,
    ) -> ReportQuestionsGenerationResult:
        raise TimeoutError("timed out")


class _FailingQuestionsService(
    report_questions_generator.IReportQuestionsGenerationService
):
    async def generate(
        self,
        messages: list[ChatCompletionMessageParam],
        token_tracker: TokenUsageTracker | None = None,
    ) -> ReportQuestionsGenerationResult:
        raise RuntimeError("LLM request failed")


class _EmptyQuestionsService(
    report_questions_generator.IReportQuestionsGenerationService
):
    async def generate(
        self,
        messages: list[ChatCompletionMessageParam],
        token_tracker: TokenUsageTracker | None = None,
    ) -> ReportQuestionsGenerationResult:
        return ReportQuestionsGenerationResult(questions=[])


def test_report_question_generation_times_out(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CUSTOMIZE_LLM_TIMEOUT_SECONDS", "0.01")
    monkeypatch.setattr(
        report_questions_generator,
        "AsyncLLMClient",
        _SlowLLMClient,
    )

    service = report_questions_generator.LLMReportQuestionsGenerationService()

    with pytest.raises(TimeoutError, match="timed out"):
        asyncio.run(service.generate([]))


def test_question_refiner_times_out(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CUSTOMIZE_LLM_TIMEOUT_SECONDS", "0.01")
    monkeypatch.setattr(refiner_llm, "AsyncLLMClient", _SlowLLMClient)

    service = refiner_llm.LLMQuestionGenerationService()

    with pytest.raises(TimeoutError, match="timed out"):
        asyncio.run(service.get([]))


def test_generate_questions_usecase_preserves_timeout() -> None:
    usecase = GenerateQuestionsUseCase(
        data_info_factory=_EmptyDataInfoFactory(),
        questions_generation_service=_TimeoutQuestionsService(),
    )

    with pytest.raises(TimeoutError, match="timed out"):
        asyncio.run(
            usecase.run(
                ReportQuestionsGenerationRequest(
                    theme="sales analysis",
                    data_source="file",
                    num_questions=3,
                )
            )
        )


def test_generate_questions_usecase_returns_fallback_questions_on_llm_error() -> None:
    usecase = GenerateQuestionsUseCase(
        data_info_factory=_EmptyDataInfoFactory(),
        questions_generation_service=_FailingQuestionsService(),
    )

    result = asyncio.run(
        usecase.run(
            ReportQuestionsGenerationRequest(
                theme="sales analysis",
                data_source="file",
                num_questions=3,
            )
        )
    )

    assert len(result.questions) == 3
    assert all("sales analysis" in question.question for question in result.questions)
    assert all(question.reasoning for question in result.questions)


def test_generate_questions_usecase_returns_fallback_questions_on_empty_result() -> (
    None
):
    usecase = GenerateQuestionsUseCase(
        data_info_factory=_EmptyDataInfoFactory(),
        questions_generation_service=_EmptyQuestionsService(),
    )

    result = asyncio.run(
        usecase.run(
            ReportQuestionsGenerationRequest(
                theme="sales analysis",
                data_source="file",
                num_questions=2,
            )
        )
    )

    assert len(result.questions) == 2
