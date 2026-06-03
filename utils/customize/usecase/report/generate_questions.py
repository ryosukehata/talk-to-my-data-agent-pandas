"""
Report Builder - UseCase: 質問生成

テーマから複数の質問を生成するユースケース
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam
from openai.types.chat.chat_completion_system_message_param import (
    ChatCompletionSystemMessageParam,
)
from openai.types.chat.chat_completion_user_message_param import (
    ChatCompletionUserMessageParam,
)

from utils.customize import prompts
from utils.customize.domain.report.domain import (
    GeneratedQuestion,
    ReportQuestionsGenerationRequest,
    ReportQuestionsGenerationResult,
)
from utils.customize.infrastructure.llm.report_questions_generator import (
    IReportQuestionsGenerationService,
)
from utils.customize.usecase.prompt.builder import IRefinerDataInfoMessageFactory
from utils.logging_helper import get_logger

if TYPE_CHECKING:
    pass

logger = get_logger("GenerateQuestionsUseCase")


FALLBACK_QUESTION_TEMPLATES = (
    "What are the most important trends related to {theme}?",
    "Which factors appear to contribute most to {theme}?",
    "Which segments show the largest differences in {theme}?",
    "Are there notable anomalies or outliers related to {theme}?",
    "What actions should decision makers consider based on {theme}?",
)

FALLBACK_REASONING = (
    "Generated from a deterministic fallback because LLM question generation "
    "did not return usable questions."
)


class GenerateQuestionsUseCase:
    """質問生成ユースケース

    テーマから複数の分析質問を生成する。
    """

    def __init__(
        self,
        data_info_factory: IRefinerDataInfoMessageFactory,
        questions_generation_service: IReportQuestionsGenerationService,
    ):
        """
        Args:
            data_info_factory: データ情報取得ファクトリ
            questions_generation_service: 質問生成サービス
        """
        self._data_info_factory = data_info_factory
        self._questions_generation_service = questions_generation_service

    async def run(
        self,
        request: ReportQuestionsGenerationRequest,
    ) -> ReportQuestionsGenerationResult:
        """テーマから質問を生成

        Args:
            request: 質問生成リクエスト

        Returns:
            生成された質問のリスト
        """
        logger.info(f"Generating questions for theme: {request.theme}")

        try:
            # 1. ユーザープロンプトを構築
            user_messages: list[ChatCompletionMessageParam] = [
                ChatCompletionUserMessageParam(
                    role="user",
                    content=f"Theme: {request.theme}\nNumber of Questions: {request.num_questions}",
                )
            ]

            # 2. データ情報を追加
            if self._data_info_factory:
                data_info_messages = await self._data_info_factory.create_message()
                user_messages.extend(data_info_messages)

            # 3. システムプロンプトと合わせてメッセージ配列を作成
            messages: list[ChatCompletionMessageParam] = [
                ChatCompletionSystemMessageParam(
                    role="system",
                    content=prompts.REPORT_QUESTIONS_GENERATOR_SYSTEM_PROMPT,
                ),
            ]
            messages.extend(user_messages)

            logger.info("*************************************")
            logger.info(f"🚀 Generating questions with messages: {messages}")
            logger.info("*************************************")

            # 4. LLMで質問を生成
            result = await self._questions_generation_service.generate(messages)

            if not result.questions:
                logger.warning(
                    "Question generation returned no questions; using fallback questions"
                )
                return self._build_fallback_questions(request)

            logger.info(f"✅ Generated {len(result.questions)} questions")
            return result

        except TimeoutError:
            logger.error("Timed out while generating questions", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Failed to generate questions: {e}", exc_info=True)
            return self._build_fallback_questions(request)

    def _build_fallback_questions(
        self,
        request: ReportQuestionsGenerationRequest,
    ) -> ReportQuestionsGenerationResult:
        theme = request.theme.strip() or "the selected dataset"
        questions = [
            GeneratedQuestion(
                question=template.format(theme=theme),
                reasoning=FALLBACK_REASONING,
                relevant_columns=[],
            )
            for template in FALLBACK_QUESTION_TEMPLATES[: request.num_questions]
        ]

        while len(questions) < request.num_questions:
            index = len(questions) + 1
            questions.append(
                GeneratedQuestion(
                    question=(
                        f"What additional insight #{index} should be reviewed "
                        f"for {theme}?"
                    ),
                    reasoning=FALLBACK_REASONING,
                    relevant_columns=[],
                )
            )

        return ReportQuestionsGenerationResult(questions=questions)
