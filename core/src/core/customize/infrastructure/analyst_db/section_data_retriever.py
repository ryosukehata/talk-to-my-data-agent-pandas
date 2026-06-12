"""
Report Builder - Infrastructure Layer - Section Data Retriever

AnalystDBからセクションデータを取得するアダプター
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from core.customize.domain.report.domain import Report
from core.customize.domain.report.service_interface import (
    IReportSectionDataRetriever,
    ReportSectionData,
)
from core.customize.usecase.prompt.builder import ISummarySectionDataFactory
from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam
from openai.types.chat.chat_completion_user_message_param import (
    ChatCompletionUserMessageParam,
)

from utils.logging_helper import get_logger

if TYPE_CHECKING:
    from utils.analyst_db import AnalystDB

logger = get_logger("AnalystDBSectionDataRetriever")


class AnalystDBSectionDataRetriever(
    IReportSectionDataRetriever, ISummarySectionDataFactory
):
    """AnalystDBからセクションデータを取得するアダプター

    Infrastructure層の実装。AnalystDBからチャット結果を取得して
    セクションデータを構築する。

    以下のインターフェースを実装:
    - IReportSectionDataRetriever (Domain層)
    - ISummarySectionDataFactory (UseCase層 - プロンプトビルダー用)
    """

    def __init__(self, analyst_db: AnalystDB):
        """
        Args:
            analyst_db: AnalystDBインスタンス
        """
        self._analyst_db = analyst_db
        self._temp_chart_files: list[str] = []

    async def get_section_data(
        self,
        message_id: str,
        heading: str,
        question: str,
    ) -> ReportSectionData:
        """メッセージIDからセクションデータを取得

        IReportSectionDataRetrieverの実装。

        Args:
            message_id: チャットメッセージID
            heading: セクション見出し
            question: 質問文

        Returns:
            セクションデータ
        """
        return await self._fetch_section_data(message_id, heading, question)

    async def create_message(
        self,
        report: Report,
        sections: list[ReportSectionData] | None = None,
    ) -> list[ChatCompletionMessageParam]:
        """LLMに渡すユーザーメッセージを構築

        ISummarySectionDataFactoryの実装。

        Args:
            report: レポートドメインモデル
            sections: 事前取得済みのセクションデータ

        Returns:
            ユーザーメッセージのリスト
        """
        user_content = await self._build_user_content(report, sections)
        return [ChatCompletionUserMessageParam(role="user", content=user_content)]

    async def _fetch_section_data(
        self,
        message_id: str,
        heading: str,
        question: str,
    ) -> ReportSectionData:
        """セクションデータを取得する共通処理"""
        logger.info(f"Getting section data for message: {message_id}")

        content = ""
        answer = None
        bottom_line = None
        conversation: list[str] = []
        chart_paths: list[str] = []

        if message_id:
            message = await self._analyst_db.get_chat_message(message_id=message_id)
            print("*" * 25 + " Section Data Retrieved " + "*" * 25)
            print(message)
            print("*" * 25 + " Section Data Retrieved " + "*" * 25)

            if message:
                content = message.content
                answer = message.content
                conversation.append(f"assistant: {message.content}")
                # チャートパスを抽出（components から）
                for component in message.components:
                    chart_paths.extend(self._extract_chart_paths(component))
                    bottom_line_candidate = getattr(component, "bottom_line", None)
                    if bottom_line_candidate and not bottom_line:
                        bottom_line = bottom_line_candidate

                if message.chat_id:
                    chat_messages = await self._analyst_db.get_chat_messages(
                        chat_id=message.chat_id
                    )
                    for msg in chat_messages[-6:]:
                        conversation.append(f"{msg.role}: {msg.content}")

        return ReportSectionData(
            heading=heading,
            question=question,
            content=content,
            answer=answer,
            bottom_line=bottom_line,
            conversation=conversation,
            chart_paths=chart_paths,
        )

    def _extract_chart_paths(self, component: object) -> list[str]:
        """コンポーネントからチャート画像のパスを生成"""
        chart_paths: list[str] = []

        chart_path_attr = getattr(component, "chart_path", None)
        if chart_path_attr:
            path = Path(chart_path_attr)
            if path.exists():
                chart_paths.append(str(path))

        try:
            from utils.schema import RunChartsResult
        except ImportError:
            RunChartsResult = None  # type: ignore[assignment]

        if RunChartsResult and isinstance(component, RunChartsResult):
            for fig in (component.fig1, component.fig2):
                if fig is None:
                    continue
                try:
                    with tempfile.NamedTemporaryFile(
                        suffix=".png", delete=False
                    ) as tmpfile:
                        fig.write_image(tmpfile.name)
                        chart_paths.append(tmpfile.name)
                        self._temp_chart_files.append(tmpfile.name)
                except Exception as e:  # pylint: disable=broad-except
                    logger.warning(f"Failed to export chart image: {e}")

        return chart_paths

    def cleanup_generated_charts(self) -> None:
        """一時的に生成したチャート画像を削除"""
        for chart_file in self._temp_chart_files:
            try:
                path = Path(chart_file)
                if path.exists():
                    path.unlink()
            except Exception as exc:  # pylint: disable=broad-except
                logger.warning(f"Failed to cleanup chart image {chart_file}: {exc}")
        self._temp_chart_files.clear()

    async def _build_user_content(
        self,
        report: Report,
        sections: list[ReportSectionData] | None,
    ) -> str:
        """ユーザープロンプト用コンテンツを構築"""
        content_lines: list[str] = [
            "# レポートタイトル",
            report.title,
            "",
        ]

        if report.theme:
            content_lines.extend(
                [
                    "# レポートテーマ",
                    report.theme,
                    "",
                ]
            )

        content_lines.append("# 分析セクション")
        content_lines.append("")

        section_data_list: list[ReportSectionData]

        if sections is not None:
            section_data_list = sections
        else:
            section_data_list = []
            for index, question in enumerate(report.questions, 1):
                heading = f"分析 {index}: {question.original_direction}"
                section_data = await self.get_section_data(
                    message_id=question.message_id or "",
                    heading=heading,
                    question=question.refined_question,
                )
                section_data_list.append(section_data)

        for section_data in section_data_list:
            chart_info = (
                "".join(f"![チャート]({path})" for path in section_data.chart_paths)
                if section_data.chart_paths
                else ""
            )

            content_lines.extend(
                [
                    f"## {section_data.heading}",
                    f"**質問:** {section_data.question}",
                    "",
                    "**分析内容:**",
                    section_data.content,
                    "",
                    chart_info,
                    "",
                    "---",
                    "",
                ]
            )

        return "\n".join(content_lines)
