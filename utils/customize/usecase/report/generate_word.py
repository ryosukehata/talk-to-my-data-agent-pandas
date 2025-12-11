"""
Report Builder - UseCase: Word生成

レポートをWord文書として生成するユースケース
"""

from __future__ import annotations

from datetime import datetime

from utils.customize.domain.report.domain import (
    QuestionStatus,
    Report,
    ReportStatus,
)
from utils.customize.domain.report.repository_interface import IReportRepository
from utils.customize.domain.report.service_interface import (
    IReportSectionDataRetriever,
    IReportSummaryService,
    ReportSectionData,
)
from utils.customize.infrastructure.word.word_generator import (
    ReportSectionContent,
    WordGenerator,
)
from utils.customize.usecase.prompt.builder import SummaryPromptBuilder
from utils.logging_helper import get_logger

logger = get_logger("GenerateWordUseCase")


class GenerateWordUseCase:
    def __init__(
        self,
        repository: IReportRepository,
        word_generator: WordGenerator,
        section_data_retriever: IReportSectionDataRetriever | None = None,
        summary_service: IReportSummaryService | None = None,
        summary_prompt_builder: SummaryPromptBuilder | None = None,
    ):
        self._repository = repository
        self._word_generator = word_generator
        self._section_data_retriever = section_data_retriever
        self._summary_service = summary_service
        self._summary_prompt_builder = summary_prompt_builder

    async def run(
        self,
        report_id: str,
        author: str | None = None,
    ) -> Report:
        logger.info(f"Generating Word document for report: {report_id}")

        report = await self._repository.get(report_id)
        if report is None:
            raise ValueError(f"Report not found: {report_id}")

        if not report.is_all_questions_completed():
            incomplete = [
                q.question_id
                for q in report.questions
                if q.status != QuestionStatus.COMPLETED
            ]
            raise ValueError(f"Not all questions completed. Incomplete: {incomplete}")

        report.status = ReportStatus.GENERATING_WORD
        await self._repository.save(report)

        try:
            sections: list[ReportSectionContent] = []
            section_data_list: list[ReportSectionData] = []

            for i, question in enumerate(report.questions, 1):
                heading = f"分析 {i}: {question.original_direction}"

                if self._section_data_retriever and question.message_id:
                    section_data = await self._section_data_retriever.get_section_data(
                        message_id=question.message_id,
                        heading=heading,
                        question=question.refined_question,
                    )
                else:
                    section_data = ReportSectionData(
                        heading=heading,
                        question=question.refined_question,
                        content="",
                        answer=question.answer,
                        bottom_line=question.bottom_line,
                        chart_paths=[],
                    )

                section_data_list.append(section_data)

                sections.append(
                    ReportSectionContent(
                        heading=section_data.heading,
                        question=section_data.question,
                        content=self._build_section_content(section_data),
                        chart_paths=section_data.chart_paths,
                    )
                )

            if self._summary_service and self._summary_prompt_builder:
                messages = await self._summary_prompt_builder.build(
                    report,
                    section_data_list,
                )
                summary_result = await self._summary_service.generate(messages)
                summary = summary_result.summary
                conclusion = summary_result.conclusion
            else:
                all_contents = [s.content for s in section_data_list]
                summary = self._generate_summary_fallback(report.title, all_contents)
                conclusion = self._generate_conclusion_fallback(all_contents)

            local_path = self._word_generator.generate(
                title=report.title,
                summary=summary,
                sections=sections,
                conclusion=conclusion,
                author=author,
                created_at=report.created_at,
            )

            storage_path = await self._repository.save_word_file(report_id, local_path)

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
        finally:
            if self._section_data_retriever:
                cleanup = getattr(
                    self._section_data_retriever, "cleanup_generated_charts", None
                )
                if callable(cleanup):
                    cleanup()

        return report

    def _generate_summary_fallback(self, title: str, contents: list[str]) -> str:
        if not contents:
            return f"本レポートは「{title}」に関するデータ分析結果をまとめたものです。"

        return (
            f"本レポートは「{title}」に関するデータ分析結果をまとめたものです。\n\n"
            f"全{len(contents)}件の分析を実施し、データに基づいた知見を得ることができました。"
        )

    def _generate_conclusion_fallback(self, contents: list[str]) -> str:
        if not contents:
            return "分析結果に基づき、今後の意思決定に活用いただければ幸いです。"

        return (
            f"以上、{len(contents)}件の分析結果をまとめました。\n\n"
            "各分析結果は、データに基づいた客観的な知見を提供しています。"
            "これらの結果を踏まえ、今後の意思決定や戦略立案にお役立てください。"
        )

    def _build_section_content(self, section: ReportSectionData) -> str:
        lines: list[str] = []
        if section.content:
            lines.append(section.content)
        if section.answer:
            lines.extend(["", "【回答】", section.answer])
        if section.bottom_line:
            lines.extend(["", "【ボトムライン】", section.bottom_line])
        if section.conversation:
            lines.extend(["", "【会話ログ】", *section.conversation])
        return "\n".join(lines) if lines else "(結果が記録されていません)"
