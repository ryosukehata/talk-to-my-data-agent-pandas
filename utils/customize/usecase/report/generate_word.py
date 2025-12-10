"""
Report Builder - UseCase: Word生成

レポートをWord文書として生成するユースケース
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from utils.customize.domain.report.domain import (
    QuestionStatus,
    Report,
    ReportStatus,
)
from utils.customize.domain.report.repository_interface import IReportRepository
from utils.customize.infrastructure.word.word_generator import (
    ReportSectionContent,
    WordGenerator,
)
from utils.logging_helper import get_logger

if TYPE_CHECKING:
    from utils.analyst_db import AnalystDB

logger = get_logger("GenerateWordUseCase")


class GenerateWordUseCase:
    """Word生成ユースケース

    レポートの実行結果をWord文書として生成する。
    """

    def __init__(
        self,
        repository: IReportRepository,
        word_generator: WordGenerator,
    ):
        """
        Args:
            repository: レポートリポジトリ
            word_generator: Word生成インフラ
        """
        self._repository = repository
        self._word_generator = word_generator

    async def run(
        self,
        report_id: str,
        analyst_db: AnalystDB,
        author: str | None = None,
    ) -> Report:
        """Word文書を生成

        Args:
            report_id: レポートID
            analyst_db: AnalystDBインスタンス
            author: 作成者名

        Returns:
            更新されたレポート

        Raises:
            ValueError: レポートが見つからない、または質問が未完了の場合
        """
        logger.info(f"Generating Word document for report: {report_id}")

        # レポートを取得
        report = await self._repository.get(report_id)
        if report is None:
            raise ValueError(f"Report not found: {report_id}")

        # 全質問が完了しているか確認
        if not report.is_all_questions_completed():
            incomplete = [
                q.question_id
                for q in report.questions
                if q.status != QuestionStatus.COMPLETED
            ]
            raise ValueError(f"Not all questions completed. Incomplete: {incomplete}")

        # ステータスを更新
        report.status = ReportStatus.GENERATING_WORD
        await self._repository.save(report)

        try:
            # 各質問の結果を取得してセクションを構築
            sections: list[ReportSectionContent] = []
            all_contents: list[str] = []

            for i, question in enumerate(report.questions, 1):
                # チャット結果を取得
                content = ""
                chart_paths: list[str] = []

                if question.message_id:
                    message = await analyst_db.get_chat_message(
                        message_id=question.message_id
                    )
                    if message:
                        content = message.content
                        # チャートパスを抽出（components から）
                        for component in message.components:
                            chart_path = getattr(component, "chart_path", None)
                            if chart_path:
                                chart_paths.append(chart_path)

                all_contents.append(content)

                sections.append(
                    ReportSectionContent(
                        heading=f"分析 {i}: {question.original_direction}",
                        question=question.refined_question,
                        content=content,
                        chart_paths=chart_paths,
                    )
                )

            # サマリーと結論を生成（簡易版：全コンテンツの要約）
            summary = self._generate_summary(report.title, all_contents)
            conclusion = self._generate_conclusion(all_contents)

            # Word文書を生成
            local_path = self._word_generator.generate(
                title=report.title,
                summary=summary,
                sections=sections,
                conclusion=conclusion,
                author=author,
                created_at=report.created_at,
            )

            # Wordファイルを永続化
            storage_path = await self._repository.save_word_file(report_id, local_path)

            # レポートを更新
            report.summary = summary
            report.conclusion = conclusion
            report.word_file_path = storage_path
            report.status = ReportStatus.DONE
            report.updated_at = datetime.now()

            await self._repository.save(report)
            logger.info(f"Word document generated: {report_id}")

        except Exception as e:
            logger.error(f"Failed to generate Word document: {e}")
            report.status = ReportStatus.ERROR
            report.error_message = str(e)
            await self._repository.save(report)
            raise

        return report

    def _generate_summary(self, title: str, contents: list[str]) -> str:
        """エグゼクティブサマリーを生成（簡易版）

        TODO: LLMを使った高品質なサマリー生成に置き換え
        """
        if not contents:
            return f"本レポートは「{title}」に関するデータ分析結果をまとめたものです。"

        return (
            f"本レポートは「{title}」に関するデータ分析結果をまとめたものです。\n\n"
            f"全{len(contents)}件の分析を実施し、データに基づいた知見を得ることができました。"
        )

    def _generate_conclusion(self, contents: list[str]) -> str:
        """結論を生成（簡易版）

        TODO: LLMを使った高品質な結論生成に置き換え
        """
        if not contents:
            return "分析結果に基づき、今後の意思決定に活用いただければ幸いです。"

        return (
            f"以上、{len(contents)}件の分析結果をまとめました。\n\n"
            "各分析結果は、データに基づいた客観的な知見を提供しています。"
            "これらの結果を踏まえ、今後の意思決定や戦略立案にお役立てください。"
        )
