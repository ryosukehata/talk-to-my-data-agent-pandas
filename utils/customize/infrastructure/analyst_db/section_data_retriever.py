"""
Report Builder - Infrastructure Layer - Section Data Retriever

AnalystDBからセクションデータを取得するアダプター
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam
from openai.types.chat.chat_completion_user_message_param import (
    ChatCompletionUserMessageParam,
)

from utils.customize.domain.report.domain import Report
from utils.customize.domain.report.service_interface import (
    IReportSectionDataRetriever,
    ReportSectionData,
)
from utils.customize.usecase.prompt.builder import ISummarySectionDataFactory
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
        chart_paths: list[str] = []

        if message_id:
            message = await self._analyst_db.get_chat_message(message_id=message_id)
            if message:
                content = message.content
                # チャートパスを抽出（components から）
                for component in message.components:
                    chart_path = getattr(component, "chart_path", None)
                    if chart_path:
                        path = Path(chart_path)
                        if path.exists():
                            chart_paths.append(str(path))

        return ReportSectionData(
            heading=heading,
            question=question,
            content=content,
            chart_paths=chart_paths,
        )

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
