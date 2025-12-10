"""
Report Builder - UseCase: レポート取得

特定のレポートを取得するユースケース
"""

from __future__ import annotations

from utils.customize.domain.report.domain import Report
from utils.customize.domain.report.repository_interface import IReportRepository
from utils.logging_helper import get_logger

logger = get_logger("GetReportUseCase")


class GetReportUseCase:
    """レポート取得ユースケース"""

    def __init__(self, repository: IReportRepository):
        """
        Args:
            repository: レポートリポジトリ
        """
        self._repository = repository

    async def run(self, report_id: str) -> Report | None:
        """レポートを取得

        Args:
            report_id: レポートID

        Returns:
            レポート（存在しない場合はNone）
        """
        logger.info(f"Getting report: {report_id}")

        report = await self._repository.get(report_id)

        if report is None:
            logger.info(f"Report not found: {report_id}")
        else:
            logger.info(f"Report found: {report_id}")

        return report
