"""
Report Builder - UseCase Layer

レポート作成のユースケース層
"""

from typing import TYPE_CHECKING, Any

from utils.customize.usecase.report.delete_report import DeleteReportUseCase
from utils.customize.usecase.report.execute_questions import ExecuteQuestionsUseCase
from utils.customize.usecase.report.generate_questions import GenerateQuestionsUseCase
from utils.customize.usecase.report.get_report import GetReportUseCase
from utils.customize.usecase.report.init_report import InitReportUseCase
from utils.customize.usecase.report.list_reports import ListReportsUseCase

if TYPE_CHECKING:
    from utils.customize.usecase.report.generate_word import GenerateWordUseCase

__all__ = [
    "InitReportUseCase",
    "ExecuteQuestionsUseCase",
    "GenerateQuestionsUseCase",
    "GenerateWordUseCase",
    "ListReportsUseCase",
    "GetReportUseCase",
    "DeleteReportUseCase",
]


def __getattr__(name: str) -> Any:
    if name == "GenerateWordUseCase":
        from utils.customize.usecase.report.generate_word import GenerateWordUseCase

        return GenerateWordUseCase

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
