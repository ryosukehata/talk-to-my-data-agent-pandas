"""
Report Builder - UseCase: 質問実行

レポートの質問を順次実行するユースケース
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from core.customize.domain.report.domain import (
    QuestionStatus,
    Report,
    ReportStatus,
)
from core.customize.domain.report.repository_interface import IReportRepository
from core.customize.infrastructure.chat.chat_executor import ChatExecutor
from core.logging_helper import get_logger

if TYPE_CHECKING:
    from core.analyst_db import AnalystDB
    from starlette.requests import Request

logger = get_logger("ExecuteQuestionsUseCase")


class ExecuteQuestionsUseCase:
    """質問実行ユースケース

    レポートの質問を順次実行し、結果を保存する。
    """

    def __init__(
        self,
        repository: IReportRepository,
        chat_executor: ChatExecutor,
    ):
        """
        Args:
            repository: レポートリポジトリ
            chat_executor: チャット実行インフラ
        """
        self._repository = repository
        self._chat_executor = chat_executor

    async def run(
        self,
        report_id: str,
        analyst_db: AnalystDB,
        request: Request,
    ) -> Report:
        """レポートの全質問を実行

        Args:
            report_id: レポートID
            analyst_db: AnalystDBインスタンス
            request: HTTPリクエスト

        Returns:
            更新されたレポート

        Raises:
            ValueError: レポートが見つからない場合
        """
        logger.info(f"Executing questions for report: {report_id}")

        # レポートを取得
        report = await self._repository.get(report_id)
        if report is None:
            raise ValueError(f"Report not found: {report_id}")

        # ステータスを処理中に更新
        report.status = ReportStatus.CHAT_PROCESSING
        await self._repository.save(report)

        try:
            # 各質問を順次実行
            for question in report.questions:
                if (
                    question.status == QuestionStatus.PENDING
                    and question.refined_question == question.original_direction
                ):
                    logger.info(f"Question not refined yet: {question.question_id}")
                    continue
                if question.status == QuestionStatus.COMPLETED:
                    logger.info(f"Question already completed: {question.question_id}")
                    continue

                await self._execute_single_question(
                    report=report,
                    question_id=question.question_id,
                    analyst_db=analyst_db,
                    request=request,
                )

            # 全質問が完了したらステータスを更新
            if report.is_all_questions_completed():
                report.status = ReportStatus.COMPLETED
            else:
                # エラーがあった場合
                has_error = any(
                    q.status == QuestionStatus.ERROR for q in report.questions
                )
                if has_error:
                    report.status = ReportStatus.ERROR

            await self._repository.save(report)
            logger.info(f"All questions executed for report: {report_id}")

        except Exception as e:
            logger.error(f"Failed to execute questions: {e}")
            report.status = ReportStatus.ERROR
            report.error_message = str(e)
            await self._repository.save(report)
            raise

        return report

    async def execute_single(
        self,
        report_id: str,
        question_id: str,
        analyst_db: AnalystDB,
        request: Request,
    ) -> Report:
        """単一の質問を実行

        Args:
            report_id: レポートID
            question_id: 質問ID
            analyst_db: AnalystDBインスタンス
            request: HTTPリクエスト

        Returns:
            更新されたレポート
        """
        logger.info(f"Executing single question: {question_id}")

        # レポートを取得
        report = await self._repository.get(report_id)
        if report is None:
            raise ValueError(f"Report not found: {report_id}")

        await self._execute_single_question(
            report=report,
            question_id=question_id,
            analyst_db=analyst_db,
            request=request,
        )

        return report

    async def _execute_single_question(
        self,
        report: Report,
        question_id: str,
        analyst_db: AnalystDB,
        request: Request,
    ) -> None:
        """単一の質問を実行（内部メソッド）"""
        # 質問を取得
        question = next(
            (q for q in report.questions if q.question_id == question_id), None
        )
        if question is None:
            raise ValueError(f"Question not found: {question_id}")

        # ステータスを実行中に更新
        question.status = QuestionStatus.RUNNING
        await self._repository.save(report)

        try:
            # チャットを実行（ChatExecutor内でチャットとメッセージが作成される）
            result = await self._chat_executor.execute(
                question=question.refined_question,
                analyst_db=analyst_db,
                chat_id="",  # ChatExecutor内で生成される
                message_id="",  # ChatExecutor内で生成される
                data_source=report.data_source,
                request=request,
            )

            if result.success and result.message:
                question.status = QuestionStatus.COMPLETED
                # ChatExecutorから返されたchat_idとメッセージIDを使用
                question.chat_id = result.chat_id
                question.message_id = result.message.id
                question.answer = result.message.content
                if result.message.components:
                    bottom_line_component = next(
                        (
                            component
                            for component in result.message.components
                            if getattr(component, "bottom_line", None)
                        ),
                        None,
                    )
                    if bottom_line_component:
                        question.bottom_line = getattr(
                            bottom_line_component, "bottom_line", None
                        )
                question.executed_at = datetime.now()
                logger.info(f"Question completed: {question_id}")
            else:
                question.status = QuestionStatus.ERROR
                question.error_message = result.error_message or "Chat execution failed"
                logger.error(f"Question failed: {question_id} - {result.error_message}")

        except Exception as e:
            question.status = QuestionStatus.ERROR
            question.error_message = str(e)
            logger.error(f"Question execution error: {question_id} - {e}")

        await self._repository.save(report)
