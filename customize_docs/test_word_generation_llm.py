"""Word生成LLMフローの動作確認スクリプト"""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.absolute()))

# OpenTelemetryのエクスポートを無効化（テスト用）
os.environ["OTEL_SDK_DISABLED"] = "true"

from utils.customize.domain.report.domain import (
    QuestionStatus,
    Report,
    ReportQuestion,
    ReportStatus,
)
from utils.customize.domain.report.repository_interface import IReportRepository
from utils.customize.domain.report.service_interface import (
    IReportSectionDataRetriever,
    IReportSummaryService,
    ReportGeneratedSummary,
    ReportSectionData,
)
from utils.customize.infrastructure.word.word_generator import (
    ReportSectionContent,
    WordGenerator,
)
from utils.customize.usecase.prompt.builder import SummaryPromptBuilder
from utils.customize.usecase.report.generate_word import GenerateWordUseCase


class InMemoryReportRepository(IReportRepository):
    def __init__(self, report: Report):
        self._report = report
        self.saved_reports: list[Report] = []
        self.saved_files: dict[str, str] = {}

    async def save(self, report: Report) -> None:
        self.saved_reports.append(report.model_copy())
        self._report = report

    async def get(self, report_id: str) -> Report | None:
        return self._report if self._report.report_id == report_id else None

    async def list_by_user(self, user_id: str) -> list[Report]:  # pragma: no cover
        return [self._report] if self._report.user_id == user_id else []

    async def delete(self, report_id: str) -> None:  # pragma: no cover
        if self._report.report_id == report_id:
            self._report = None  # type: ignore[assignment]

    async def save_word_file(self, report_id: str, local_path: str) -> str:
        key = f"mock://storage/{report_id}.docx"
        self.saved_files[report_id] = key
        return key

    async def get_word_file(
        self, report_id: str, local_path: str
    ) -> bool:  # pragma: no cover
        return False


class DummySectionDataRetriever(IReportSectionDataRetriever):
    def __init__(self, sections: dict[str, ReportSectionData]):
        self.sections = sections
        self.called_with: list[tuple[str, str, str]] = []

    async def get_section_data(
        self,
        message_id: str,
        heading: str,
        question: str,
    ) -> ReportSectionData:
        self.called_with.append((message_id, heading, question))
        return self.sections[message_id]


class DummySummaryService(IReportSummaryService):
    def __init__(self, result: ReportGeneratedSummary):
        self.result = result
        self.received_messages: list[list[dict[str, Any]]] = []

    async def generate(
        self,
        messages: list[dict[str, Any]],
    ) -> ReportGeneratedSummary:
        self.received_messages.append(messages)
        return self.result


class DummySummaryFactory:
    def __init__(self, messages: list[dict[str, Any]]):
        self.messages = messages
        self.capture: list[tuple[Report, list[ReportSectionData] | None]] = []

    async def create_message(
        self,
        report: Report,
        sections: list[ReportSectionData] | None = None,
    ) -> list[dict[str, Any]]:
        self.capture.append((report, sections))
        return self.messages


class DummyWordGenerator(WordGenerator):
    def __init__(self) -> None:
        super().__init__()
        self.generated_args: dict[str, Any] | None = None
        self.output_path = Path("./tmp/test_report.docx")
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.output_path.write_bytes(b"dummy doc")

    def generate(
        self,
        title: str,
        summary: str,
        sections: list[ReportSectionContent],
        conclusion: str,
        author: str | None = None,
        created_at: datetime | None = None,
    ) -> str:
        self.generated_args = {
            "title": title,
            "summary": summary,
            "sections": sections,
            "conclusion": conclusion,
            "author": author,
            "created_at": created_at,
        }
        return str(self.output_path)


def _build_sample_report() -> Report:
    now = datetime.now()
    questions = [
        ReportQuestion(
            question_id="q1",
            original_direction="売上推移の把握",
            refined_question="直近12ヶ月の売上推移を教えてください",
            status=QuestionStatus.COMPLETED,
            chat_id="chat-1",
            message_id="msg-1",
            executed_at=now - timedelta(days=1),
        ),
        ReportQuestion(
            question_id="q2",
            original_direction="地域別比較",
            refined_question="主要地域の売上比較を可視化してください",
            status=QuestionStatus.COMPLETED,
            chat_id="chat-2",
            message_id="msg-2",
            executed_at=now - timedelta(hours=12),
        ),
    ]

    return Report(
        report_id="report-123",
        title="2024年 売上レポート",
        theme="売上トレンド分析",
        user_id="user-1",
        status=ReportStatus.COMPLETED,
        questions=questions,
        created_at=now - timedelta(days=2),
        updated_at=now - timedelta(days=1),
    )


async def test_usecase_with_llm() -> None:
    report = _build_sample_report()
    repo = InMemoryReportRepository(report)

    section_data_map = {
        "msg-1": ReportSectionData(
            heading="分析 1: 売上推移の把握",
            question=report.questions[0].refined_question,
            content="売上は安定して増加傾向にあります",
            chart_paths=["/tmp/chart1.png"],
        ),
        "msg-2": ReportSectionData(
            heading="分析 2: 地域別比較",
            question=report.questions[1].refined_question,
            content="地方都市が前年度比120%で推移",
            chart_paths=[],
        ),
    }

    section_retriever = DummySectionDataRetriever(section_data_map)
    summary_result = ReportGeneratedSummary(
        summary="売上は継続的に増加しており、主要地域が牽引しています。",
        conclusion="増加傾向を維持するため、重点地域への投資を継続してください。",
    )
    summary_service = DummySummaryService(summary_result)

    factory_messages = [{"role": "system", "content": "dummy message"}]
    summary_factory = DummySummaryFactory(factory_messages)
    prompt_builder = SummaryPromptBuilder(summary_factory)
    word_generator = DummyWordGenerator()

    usecase = GenerateWordUseCase(
        repository=repo,
        word_generator=word_generator,
        section_data_retriever=section_retriever,
        summary_service=summary_service,
        summary_prompt_builder=prompt_builder,
    )

    result = await usecase.run(report.report_id, author="tester@example.com")

    print("=== LLM利用シナリオ結果 ===")
    print("ステータス:", result.status)
    print("サマリー:", result.summary)
    print("結論:", result.conclusion)
    print("Word保存先:", repo.saved_files.get(report.report_id))


async def test_usecase_fallback() -> None:
    report = _build_sample_report()
    repo = InMemoryReportRepository(report)
    word_generator = DummyWordGenerator()
    prompt_builder = SummaryPromptBuilder()  # factoryなし

    usecase = GenerateWordUseCase(
        repository=repo,
        word_generator=word_generator,
        section_data_retriever=None,
        summary_service=None,
        summary_prompt_builder=prompt_builder,
    )

    result = await usecase.run(report.report_id, author="fallback@example.com")

    print("=== フォールバックシナリオ結果 ===")
    print("ステータス:", result.status)
    print("サマリー:", result.summary)
    print("結論:", result.conclusion)
    print("Word保存先:", repo.saved_files.get(report.report_id))


async def main() -> None:
    os.environ.setdefault("OTEL_SDK_DISABLED", "true")
    await test_usecase_with_llm()
    await test_usecase_fallback()


if __name__ == "__main__":
    asyncio.run(main())
