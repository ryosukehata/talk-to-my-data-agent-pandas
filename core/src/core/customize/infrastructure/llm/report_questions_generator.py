"""
Report Builder - Infrastructure Layer - LLM

レポート用質問生成のLLMサービス実装
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import cast

from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam

from core.constants import ALTERNATIVE_LLM_BIG
from core.customize.domain.report.domain import (
    ReportQuestionsGenerationResult,
)
from core.customize.infrastructure.llm.timeout import get_llm_timeout_seconds
from core.llm_client import AsyncLLMClient
from core.logging_helper import get_logger
from core.token_tracking import TokenUsageTracker

logger = get_logger(__name__)
REPORT_BUILDER_TIMEOUT_ENV = "REPORT_BUILDER_LLM_TIMEOUT_SECONDS"


class IReportQuestionsGenerationService(ABC):
    """レポート用質問生成サービスのインターフェース"""

    @abstractmethod
    async def generate(
        self,
        messages: list[ChatCompletionMessageParam],
        token_tracker: TokenUsageTracker | None = None,
    ) -> ReportQuestionsGenerationResult:
        """テーマから複数の質問を生成

        Args:
            messages: LLMに送るメッセージ
            token_tracker: トークン使用量トラッカー

        Returns:
            生成された質問のリスト

        Raises:
            Exception: 質問生成に失敗した場合
        """
        pass


class LLMReportQuestionsGenerationService(IReportQuestionsGenerationService):
    """
    Report Questions Generator - LLM Service Implementation

    LLM を使ったレポート用質問生成サービスの実装
    """

    def __init__(self) -> None:
        self.model = ALTERNATIVE_LLM_BIG

    async def generate(
        self,
        messages: list[ChatCompletionMessageParam],
        token_tracker: TokenUsageTracker | None = None,
    ) -> ReportQuestionsGenerationResult:
        """テーマから複数の質問を生成"""
        logger.info("Generating report questions via LLM...")
        timeout_seconds = get_llm_timeout_seconds(REPORT_BUILDER_TIMEOUT_ENV)

        async with AsyncLLMClient(token_tracker=token_tracker) as client:
            try:
                response, _ = await asyncio.wait_for(
                    client.chat.completions.create_with_completion(
                        model=self.model,
                        messages=messages,
                        response_model=ReportQuestionsGenerationResult,
                    ),
                    timeout=timeout_seconds,
                )
            except asyncio.TimeoutError as exc:
                logger.error(
                    "Report question generation timed out after %.1f seconds",
                    timeout_seconds,
                )
                raise TimeoutError(
                    f"Report question generation timed out after {timeout_seconds:g} seconds"
                ) from exc

        if response is None:
            raise ValueError("Report question generation returned no response")

        response = cast(ReportQuestionsGenerationResult, response)
        logger.info(f"Generated {len(response.questions)} questions")
        return response
