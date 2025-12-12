"""
Report Builder - Domain Layer

レポート作成機能のドメイン層
"""

from utils.customize.domain.report.domain import (
    GeneratedQuestion,
    QuestionStatus,
    Report,
    ReportGenerateWordRequest,
    ReportQuestion,
    ReportQuestionsGenerationRequest,
    ReportQuestionsGenerationResult,
    ReportSection,
    ReportStatus,
)
from utils.customize.domain.report.repository_interface import IReportRepository

__all__ = [
    "Report",
    "ReportQuestion",
    "ReportSection",
    "ReportStatus",
    "QuestionStatus",
    "ReportCreateRequest",
    "ReportGenerateWordRequest",
    "GeneratedQuestion",
    "ReportQuestionsGenerationRequest",
    "ReportQuestionsGenerationResult",
    "IReportRepository",
]
