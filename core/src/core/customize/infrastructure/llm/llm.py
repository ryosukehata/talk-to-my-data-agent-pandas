"""
Question Refiner - Infrastructure Layer (Adapters)

外部依存の具体的な実装（アダプター）
"""

from __future__ import annotations

import asyncio
from typing import cast

from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam

from core.customize.domain.question_refiner.domain import (
    RefinedQuestion,
)
from core.customize.domain.question_refiner.service_interface import (
    IQuestionGenerationService,
)
from core.customize.infrastructure.llm.timeout import get_llm_timeout_seconds
from utils.constants import ALTERNATIVE_LLM_BIG
from utils.llm_client import AsyncLLMClient
from utils.logging_helper import get_logger
from utils.token_tracking import (
    TokenUsageTracker,
)

logger = get_logger(__name__)
QUESTION_REFINER_TIMEOUT_ENV = "QUESTION_REFINER_LLM_TIMEOUT_SECONDS"


class LLMQuestionGenerationService(IQuestionGenerationService):
    """
    Question Refiner - LLM Service Implementation

    LLM を使った質問生成サービスの実装
    """

    def __init__(self, token_tracker: TokenUsageTracker | None = None) -> None:
        self.model = ALTERNATIVE_LLM_BIG
        self.token_tracker = token_tracker

    async def get(
        self,
        messages: list[ChatCompletionMessageParam],
        token_tracker: TokenUsageTracker | None = None,
    ) -> RefinedQuestion:
        """データセット概要から質問を生成

        Args:
            messages: LLMに送信するメッセージリスト
            token_tracker: トークン使用量トラッカー

        Returns:
            生成された洗練された質問

        Raises:
            Exception: 質問生成に失敗した場合
        """
        logger.info("🔄 LLMQuestionGenerationService.get() called")
        logger.info(f"📝 Using model: {self.model}")
        timeout_seconds = get_llm_timeout_seconds(QUESTION_REFINER_TIMEOUT_ENV)
        effective_token_tracker = token_tracker or self.token_tracker

        # LLM を使って質問生成
        async with AsyncLLMClient(token_tracker=effective_token_tracker) as client:
            logger.info("🌐 Calling LLM API...")
            try:
                response, _ = await asyncio.wait_for(
                    client.chat.completions.create_with_completion(
                        model=self.model,
                        messages=messages,
                        response_model=RefinedQuestion,
                    ),
                    timeout=timeout_seconds,
                )
            except asyncio.TimeoutError as exc:
                logger.error(
                    "Question refinement timed out after %.1f seconds",
                    timeout_seconds,
                )
                raise TimeoutError(
                    f"Question refinement timed out after {timeout_seconds:g} seconds"
                ) from exc

            if response is None:
                raise ValueError("Question refinement returned no response")

            response = cast(RefinedQuestion, response)
            logger.info(f"✅ LLM response received: {response}")

        return response
