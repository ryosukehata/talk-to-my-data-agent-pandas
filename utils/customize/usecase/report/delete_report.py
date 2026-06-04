"""
Report Builder - UseCase: レポート削除

レポートを削除するユースケース
"""

from __future__ import annotations

from utils.customize.domain.report.repository_interface import IReportRepository
from utils.logging_helper import get_logger

logger = get_logger("DeleteReportUseCase")


class DeleteReportUseCase:
    """レポート削除ユースケース"""

    def __init__(self, repository: IReportRepository):
        """
        Args:
            repository: レポートリポジトリ
        """
        self._repository = repository

    async def run(self, report_id: str) -> bool:
        """レポートを削除

        Args:
            report_id: レポートID

        Returns:
            削除が成功したかどうか
        """
        logger.info(f"Deleting report: {report_id}")

        try:
            await self._repository.delete(report_id)
            logger.info(f"Report deleted: {report_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete report {report_id}: {e}")
            return False
