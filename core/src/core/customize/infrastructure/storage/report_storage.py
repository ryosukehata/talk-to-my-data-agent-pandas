"""
Report Builder - Infrastructure Layer - Storage

レポートリポジトリの実装（PersistentStorageを利用）
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

from core.customize.cache import NullPersistentStorage, atomic_write_json
from core.customize.domain.report.domain import Report
from core.customize.domain.report.repository_interface import IReportRepository
from utils.logging_helper import get_logger
from utils.persistent_storage import PersistentStorage

logger = get_logger("ReportStorage")


class ReportStorage(IReportRepository):
    """レポートリポジトリの実装

    PersistentStorageを使用して、レポートのメタデータとWordファイルを
    DataRobot Catalogに永続化する。
    """

    # ファイル命名規則
    METADATA_PREFIX = "report_metadata_"
    WORD_PREFIX = "report_word_"
    INDEX_KEY_TEMPLATE = "report_index_{user_id}"

    def __init__(self, user_id: str):
        self._user_id = user_id
        try:
            self._storage = PersistentStorage(user_id)
        except Exception as e:  # pragma: no cover
            logger.warning(
                "PersistentStorage initialization failed. Using NullPersistentStorage. "
                f"reason={type(e).__name__}: {e}"
            )
            self._storage = NullPersistentStorage(user_id)

        self._base_dir = Path(__file__).resolve().parent / "data" / self._user_id
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def _index_key(self) -> str:
        return self.INDEX_KEY_TEMPLATE.format(user_id=self._user_id)

    def _metadata_path(self, report_id: str) -> Path:
        return self._base_dir / f"{report_id}.json"

    def _word_path(self, report_id: str) -> Path:
        return self._base_dir / f"{report_id}.docx"

    def _index_path(self) -> Path:
        return self._base_dir / "report_index.json"

    def _metadata_key(self, report_id: str) -> str:
        """メタデータのストレージキーを生成"""
        return f"{self.METADATA_PREFIX}{report_id}.json"

    def _word_key(self, report_id: str) -> str:
        """Wordファイルのストレージキーを生成"""
        return f"{self.WORD_PREFIX}{report_id}.docx"

    async def save(self, report: Report) -> None:
        """レポートを保存"""
        logger.info(f"Saving report: {report.report_id}")

        # 更新日時を更新
        report.updated_at = datetime.now()

        local_path = self._metadata_path(report.report_id)

        try:
            # 1) まずローカルを原子的に更新（ローカルを常に正とする）
            atomic_write_json(str(local_path), report.to_dict())

            # 2) リモート保存は非同期でスケジュール（読み込みの体感速度を優先）
            asyncio.create_task(
                self._storage.save_to_storage(
                    self._metadata_key(report.report_id), str(local_path)
                )
            )
            logger.info(
                f"Report saved locally and scheduled remote persist: {report.report_id}"
            )
        except Exception as e:
            logger.error(
                f"Failed to save report {report.report_id}: {type(e).__name__}: {e}",
                exc_info=True,
            )
            raise

        # インデックスを更新
        await self._update_index(report.report_id, add=True)

    async def get(self, report_id: str, max_retries: int = 3) -> Report | None:
        """レポートを取得（リトライ付き）"""
        logger.info(f"Getting report: {report_id}")

        for attempt in range(max_retries):
            result = await self._get_once(report_id)
            if result is not None:
                return result

            # ストレージエラーの場合、少し待ってリトライ
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 1.0  # 1秒、2秒とリトライ間隔を増やす
                logger.info(
                    f"Retrying get report {report_id} in {wait_time}s (attempt {attempt + 2}/{max_retries})"
                )
                await asyncio.sleep(wait_time)

        return None

    async def _get_once(self, report_id: str) -> Report | None:
        """レポートを1回取得（内部用）"""
        local_path = self._metadata_path(report_id)

        # ローカル優先。なければストレージから取得してローカルに反映
        if not (local_path.exists() and local_path.stat().st_size > 0):
            try:
                await self._storage.fetch_from_storage(
                    self._metadata_key(report_id), str(local_path)
                )
            except Exception as e:
                logger.info(
                    f"Report fetch failed for {report_id}: {type(e).__name__}: {e}"
                )

        if not local_path.exists() or local_path.stat().st_size == 0:
            logger.info(f"Report not found or empty: {report_id}")
            return None

        try:
            with local_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON for report {report_id}: {e}")
            return None

        if isinstance(data, dict) and "report_id" not in data:
            logger.info(f"Report data invalid for {report_id}")
            return None

        return Report.from_dict(data)

    async def list_by_user(self, user_id: str) -> list[Report]:
        """ユーザーのレポート一覧を取得"""
        logger.info(f"Listing reports for user: {user_id}")

        # インデックスを取得
        report_ids = await self._get_index()

        # 各レポートを取得
        reports: list[Report] = []
        for report_id in report_ids:
            report = await self.get(report_id)
            if report and report.user_id == user_id:
                reports.append(report)

        # 新しい順にソート
        reports.sort(key=lambda r: r.created_at, reverse=True)
        return reports

    async def delete(self, report_id: str) -> None:
        """レポートを削除"""
        logger.info(f"Deleting report: {report_id}")

        # 1) まずローカルを削除（ローカルを正とする）
        local_metadata = self._metadata_path(report_id)
        if local_metadata.exists():
            local_metadata.unlink(missing_ok=True)

        local_word = self._word_path(report_id)
        if local_word.exists():
            local_word.unlink(missing_ok=True)

        # 2) リモート削除は非同期でスケジュール
        asyncio.create_task(self._storage.delete_file(self._metadata_key(report_id)))
        asyncio.create_task(self._storage.delete_file(self._word_key(report_id)))

        # インデックスを更新
        await self._update_index(report_id, add=False)

    async def save_word_file(self, report_id: str, local_path: str) -> str:
        """Wordファイルを保存"""
        logger.info(f"Saving Word file for report: {report_id}")
        word_copy_path = self._word_path(report_id)

        try:
            shutil.copy2(local_path, word_copy_path)
        except Exception as e:
            logger.warning(
                f"Failed to keep local copy of Word file for {report_id}: {e}"
            )
            word_copy_path = Path(local_path)

        # リモート保存は非同期でスケジュール（ローカル優先）
        asyncio.create_task(
            self._storage.save_to_storage(
                self._word_key(report_id), str(word_copy_path)
            )
        )

        return self._word_key(report_id)

    async def get_word_file(self, report_id: str, local_path: str) -> bool:
        """Wordファイルを取得"""
        logger.info(f"Getting Word file for report: {report_id}")

        # 1) まずローカルコピーを優先して返す
        local_copy = self._word_path(report_id)
        try:
            if local_copy.exists() and local_copy.stat().st_size > 0:
                shutil.copy2(local_copy, local_path)
                return os.path.exists(local_path) and os.path.getsize(local_path) > 0
        except Exception:
            # ローカルコピーが壊れている場合は後段でストレージから取得
            pass

        # 2) ローカルが無い場合のみストレージから取得
        try:
            await self._storage.fetch_from_storage(
                self._word_key(report_id), local_path
            )
            return os.path.exists(local_path) and os.path.getsize(local_path) > 0
        except Exception as e:
            logger.error(f"Failed to get Word file for {report_id}: {e}")
            return False

    # ========================================
    # インデックス管理（レポートID一覧）
    # ========================================

    async def _get_index(self) -> list[str]:
        """レポートIDのインデックスを取得"""
        index_path = self._index_path()

        # ローカル優先。なければストレージから取得してローカルに反映
        if not (index_path.exists() and index_path.stat().st_size > 0):
            try:
                await self._storage.fetch_from_storage(
                    self._index_key(), str(index_path)
                )
            except Exception:
                pass

        if not index_path.exists() or index_path.stat().st_size == 0:
            return []

        try:
            with index_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("report_ids", [])
        except Exception:
            return []

    async def _update_index(self, report_id: str, add: bool) -> None:
        """インデックスを更新"""
        current_ids = await self._get_index()

        if add:
            if report_id in current_ids:
                return

            # 新しいIDを追加（完全更新ではなく追記）
            current_ids.append(report_id)

            # 古い内容を保持したまま保存するため、一時ファイルを使って差分保存
            with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tmp:
                tmp_path = tmp.name

            try:
                atomic_write_json(tmp_path, {"report_ids": current_ids})
                # リモート保存は非同期でスケジュール
                asyncio.create_task(
                    self._storage.save_to_storage(self._index_key(), tmp_path)
                )
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

            # ローカルキャッシュも更新
            atomic_write_json(str(self._index_path()), {"report_ids": current_ids})

        else:
            if report_id not in current_ids:
                return

            # IDを削除
            current_ids.remove(report_id)

            # 空になった場合は「空を永続化しない」ポリシーに従い、
            # ストレージキーを削除しローカルキャッシュも削除する
            if not current_ids:
                try:
                    # リモート削除は非同期でスケジュール
                    asyncio.create_task(self._storage.delete_file(self._index_key()))
                except Exception as e:  # pragma: no cover
                    logger.warning(
                        f"Failed to schedule index delete: {type(e).__name__}: {e}"
                    )

                index_path = self._index_path()
                try:
                    if index_path.exists():
                        index_path.unlink(missing_ok=True)
                except Exception as e:  # pragma: no cover
                    logger.warning(
                        f"Failed to delete local empty index: {type(e).__name__}: {e}"
                    )
                return

            # 空でない場合のみ保存（原子的に書き込み→永続化[非同期]）
            index_path = self._index_path()
            atomic_write_json(str(index_path), {"report_ids": current_ids})
            asyncio.create_task(
                self._storage.save_to_storage(self._index_key(), str(index_path))
            )
