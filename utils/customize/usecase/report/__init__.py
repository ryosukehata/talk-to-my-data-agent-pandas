from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from core.customize.usecase.report import (
        DeleteReportUseCase,
        ExecuteQuestionsUseCase,
        GenerateQuestionsUseCase,
        GenerateWordUseCase,
        GetReportUseCase,
        InitReportUseCase,
        ListReportsUseCase,
    )

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
    if name in __all__:
        from core.customize.usecase import report as core_report

        return getattr(core_report, name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
