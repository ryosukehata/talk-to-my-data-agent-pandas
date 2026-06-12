"""
Report Builder - UseCase: レポート一覧取得

ユーザーのレポート一覧を取得するユースケース
"""

from __future__ import annotations

from core.customize.domain.report.domain import Report
from core.customize.domain.report.repository_interface import IReportRepository
from utils.logging_helper import get_logger

logger = get_logger("ListReportsUseCase")


class ListReportsUseCase:
    """レポート一覧取得ユースケース"""

    def __init__(self, repository: IReportRepository):
        """
        Args:
            repository: レポートリポジトリ
        """
        self._repository = repository

    async def run(self, user_id: str) -> list[Report]:
        """ユーザーのレポート一覧を取得

        Args:
            user_id: ユーザーID

        Returns:
            レポートのリスト（新しい順）
        """
        logger.info(f"Listing reports for user: {user_id}")

        reports = await self._repository.list_by_user(user_id)

        logger.info(f"Found {len(reports)} reports for user: {user_id}")
        return reports
