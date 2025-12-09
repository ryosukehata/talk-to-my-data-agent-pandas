"""
Question Refiner - LLM Service Interface

LLM による質問生成の抽象インターフェース（ポート）
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam

from utils.customize.domain.question_refiner.domain import (
    RefinedQuestion,
)


class IQuestionGenerationService(ABC):
    """質問生成サービスのインターフェース"""

    @abstractmethod
    async def get(
        self,
        messages: list[ChatCompletionMessageParam],
    ) -> list[RefinedQuestion]:
        """データセット概要から質問を生成

        Args:
            user_direction: ユーザーの質問の方向性
            dataset_summaries: データセット概要のリスト
            num_questions: 生成する質問の数

        Returns:
            生成された質問のリスト

        Raises:
            Exception: 質問生成に失敗した場合
        """
        pass
