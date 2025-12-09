"""
Question Refiner - Use Case (Application Layer)

ビジネスロジックを実装するユースケース層
"""

from __future__ import annotations

from utils.customize import prompts
from utils.customize.domain.question_refiner.domain import (
    QuestionRefinementRequest,
    QuestionRefinementResult,
)
from utils.customize.domain.question_refiner.service_interface import (
    IQuestionGenerationService,
)
from utils.customize.usecase.prompt.builder import (
    MessageFactory,
    RefineUserPromptBuilder,
)
from utils.logging_helper import get_logger

logger = get_logger(__name__)


class RefineQuestionUseCase:
    """質問を洗練するユースケース"""

    def __init__(
        self,
        prompt_builder: RefineUserPromptBuilder,
        message_factory: MessageFactory,
        question_generation_service: IQuestionGenerationService,
    ):
        """
        Args:
            dataset_repository: データセット情報を取得するリポジトリ
            question_generation_service: 質問生成サービス
        """
        self.prompt_builder = prompt_builder
        self.message_factory = message_factory
        self.question_generation_service = question_generation_service

    async def run(self, request: QuestionRefinementRequest) -> QuestionRefinementResult:
        """質問洗練のユースケースを実行

        Args:
            request: 質問洗練リクエスト

        Returns:
            QuestionRefinementResult: 質問生成結果
        """
        try:
            logger.info("*************************************")
            logger.info(f"🚀Received input for Evaluation: {request}")
            logger.info("*************************************")
            # 1. プロンプト構築
            user_prompt = await self.prompt_builder.build(request)

            # 2. メッセージ配列生成
            messages = self.message_factory.create_message(
                system_prompt=prompts.QUESTION_REFINER_SYSTEM_PROMPT,
                user_prompt=user_prompt,
            )
            logger.info("*************************************")
            logger.info(f"🍀Generated messages for Evaluation: {messages}")
            logger.info("*************************************")

            # 3. リポジトリ経由でLLM実行
            refined_question = await self.question_generation_service.get(messages)

            # 4. QuestionRefinementResultに変換
            return QuestionRefinementResult(
                success=True,
                refined_questions=[refined_question],
                error=None,
            )

        except Exception as e:
            logger.error(f"質問の生成に失敗しました: {e}", exc_info=True)
            return QuestionRefinementResult(
                success=False,
                refined_questions=[],
                error=str(e),
            )
