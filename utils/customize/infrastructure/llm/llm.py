"""
Question Refiner - Infrastructure Layer (Adapters)

外部依存の具体的な実装（アダプター）
"""

from __future__ import annotations

from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam

from utils.constants import ALTERNATIVE_LLM_BIG
from utils.customize.domain.question_refiner.domain import (
    RefinedQuestion,
)
from utils.customize.domain.question_refiner.service_interface import (
    IQuestionGenerationService,
)
from utils.llm_client import AsyncLLMClient
from utils.logging_helper import get_logger
from utils.token_tracking import (
    TokenUsageTracker,
)

logger = get_logger(__name__)


class LLMQuestionGenerationService(IQuestionGenerationService):
    """
    Question Refiner - LLM Service Implementation

    LLM を使った質問生成サービスの実装
    """

    def __init__(self):
        self.model = ALTERNATIVE_LLM_BIG

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

        # LLM を使って質問生成
        async with AsyncLLMClient(token_tracker=token_tracker) as client:
            logger.info("🌐 Calling LLM API...")
            (
                response,
                response_org,
            ) = await client.chat.completions.create_with_completion(
                model=self.model,
                messages=messages,
                response_model=RefinedQuestion,
            )
            logger.info(f"✅ LLM response received: {response}")

        return response
