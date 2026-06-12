"""
Report Builder - UseCase: レポート初期化

新しいレポートを作成し、テーマから方向性レベルの質問を生成する。
洗練（Refine）と実行（Execute）は別のAPIで行う。
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from core.customize.domain.report.domain import (
    QuestionStatus,
    Report,
    ReportQuestion,
    ReportQuestionsGenerationRequest,
    ReportStatus,
)
from core.customize.domain.report.repository_interface import IReportRepository
from core.customize.usecase.report.generate_questions import GenerateQuestionsUseCase
from utils.logging_helper import get_logger

if TYPE_CHECKING:
    pass

logger = get_logger("InitReportUseCase")


class InitReportUseCase:
    """レポート初期化ユースケース

    レポートを新規作成し、テーマから方向性レベルの質問を自動生成する。

    責務:
    - テーマから方向性レベルの質問を生成
    - レポートをDRAFT状態で保存

    責務外:
    - 質問の洗練（Refine API経由で行う）
    - 質問の実行（Execute API経由で行う）
    """

    def __init__(
        self,
        repository: IReportRepository,
        questions_generator: GenerateQuestionsUseCase,
    ):
        """
        Args:
            repository: レポートリポジトリ
            questions_generator: 質問生成ユースケース（方向性レベル）
        """
        self._repository = repository
        self._questions_generator = questions_generator

    async def run(
        self,
        request: ReportQuestionsGenerationRequest,
        user_id: str,
        title: str | None = None,
    ) -> Report:
        """レポートを初期化（方向性レベルの質問を生成）

        Args:
            request: 質問生成リクエスト（テーマと生成数を含む）
            user_id: ユーザーID
            title: レポートタイトル（省略時はテーマを使用）

        Returns:
            作成されたレポート（DRAFT状態、洗練前の質問）

        Raises:
            ValueError: 質問生成に失敗した場合
        """
        report_title = title or request.theme
        logger.info(f"Initializing report: {report_title}")

        # レポートIDを生成
        report_id = str(uuid.uuid4())

        # 質問生成（方向性レベル）
        result = await self._questions_generator.run(request)

        if not result.questions:
            raise ValueError("Failed to generate questions from theme")

        logger.info(f"Generated {len(result.questions)} direction-level questions")

        # 質問リストを作成
        questions: list[ReportQuestion] = []
        for gen_question in result.questions:
            question_id = str(uuid.uuid4())
            questions.append(
                ReportQuestion(
                    question_id=question_id,
                    original_direction=gen_question.question,
                    refined_question="",  # 洗練前は空
                    status=QuestionStatus.PENDING,
                )
            )

        # レポート作成・保存
        report = Report(
            report_id=report_id,
            title=report_title,
            user_id=user_id,
            data_source=request.data_source,
            theme=request.theme,
            status=ReportStatus.PENDING,
            questions=questions,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        await self._repository.save(report)
        logger.info(f"Report created: {report_id} with {len(questions)} questions")

        return report
