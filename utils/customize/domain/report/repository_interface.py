"""
Report Builder - Repository Interface

レポートリポジトリの抽象インターフェース（ポート）
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from utils.customize.domain.report.domain import Report


class IReportRepository(ABC):
    """レポートリポジトリのインターフェース"""

    @abstractmethod
    async def save(self, report: Report) -> None:
        """レポートを保存

        Args:
            report: 保存するレポートエンティティ
        """
        pass

    @abstractmethod
    async def get(self, report_id: str) -> Report | None:
        """レポートを取得

        Args:
            report_id: レポートID

        Returns:
            レポートエンティティ（存在しない場合はNone）
        """
        pass

    @abstractmethod
    async def list_by_user(self, user_id: str) -> list[Report]:
        """ユーザーのレポート一覧を取得

        Args:
            user_id: ユーザーID

        Returns:
            レポートのリスト（新しい順）
        """
        pass

    @abstractmethod
    async def delete(self, report_id: str) -> None:
        """レポートを削除

        Args:
            report_id: レポートID
        """
        pass

    @abstractmethod
    async def save_word_file(self, report_id: str, local_path: str) -> str:
        """Wordファイルを保存

        Args:
            report_id: レポートID
            local_path: ローカルのWordファイルパス

        Returns:
            保存先のパス/URL
        """
        pass

    @abstractmethod
    async def get_word_file(self, report_id: str, local_path: str) -> bool:
        """Wordファイルを取得

        Args:
            report_id: レポートID
            local_path: ダウンロード先のローカルパス

        Returns:
            取得成功したかどうか
        """
        pass
