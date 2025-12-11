"""
Report Builder - Domain Layer - Service Interfaces

サマリー生成とセクションデータ取得のインターフェース定義
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field


@dataclass
class ReportSectionData:
    """レポートセクションのデータ"""

    heading: str
    question: str
    content: str
    answer: str | None = None
    bottom_line: str | None = None
    conversation: list[str] = field(default_factory=list)
    chart_paths: list[str] = field(default_factory=list)


class ReportGeneratedSummary(BaseModel):
    """サマリーと結論の生成結果"""

    summary: str = Field(description="エグゼクティブサマリー")
    conclusion: str = Field(description="結論")


class IReportSummaryService(ABC):
    """サマリー生成サービスのインターフェース"""

    @abstractmethod
    async def generate(
        self,
        messages: list[dict[str, Any]],
    ) -> ReportGeneratedSummary:
        pass


class IReportSectionDataRetriever(ABC):
    """セクションデータ取得のインターフェース"""

    @abstractmethod
    async def get_section_data(
        self,
        message_id: str,
        heading: str,
        question: str,
    ) -> ReportSectionData:
        pass
