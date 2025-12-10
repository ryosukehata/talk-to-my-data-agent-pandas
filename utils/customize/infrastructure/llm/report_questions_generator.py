"""
Report Builder - Infrastructure Layer - LLM

レポート用質問生成のLLMサービス実装
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam

from utils.constants import ALTERNATIVE_LLM_BIG
from utils.customize.domain.report.domain import (
    ReportQuestionsGenerationResult,
)
from utils.llm_client import AsyncLLMClient
from utils.logging_helper import get_logger
from utils.token_tracking import TokenUsageTracker

logger = get_logger(__name__)


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

        async with AsyncLLMClient(token_tracker=token_tracker) as client:
            response, _ = await client.chat.completions.create_with_completion(
                model=self.model,
                messages=messages,
                response_model=ReportQuestionsGenerationResult,
            )

        logger.info(f"Generated {len(response.questions)} questions")
        return response
