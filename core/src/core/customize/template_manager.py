"""
Prompt Template Manager

プロンプトテンプレートのCSV読み込みとカテゴリ別管理を行うモジュール。
Phase1 MVP: pandas読み込み + 基本的なフィルタリング機能を提供。
"""

import os
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from core.customize.api import download_registry_dataset_as_dataframe
from core.customize.cache import (
    NullPersistentStorage,
    PersistentCache,
    atomic_write_csv,
)
from core.logging_helper import get_logger
from core.persistent_storage import PersistentStorage
from core.resources import PromptsTemplateAICatalog


class TemplateManager:
    """プロンプトテンプレートの管理クラス

    CSV から pandas DataFrame でテンプレートを読み込み、
    カテゴリ別検索や個別取得機能を提供する。
    """

    def __init__(self, local: bool = True):
        """初期化

        Args:
            csv_path: CSVファイルのパス。None の場合はデフォルトパスを使用

        """
        self.logger = get_logger("TemplateManager")
        self.local = local
        # 永続ストレージ（テンプレートはグローバル扱い）
        self._storage: Optional[PersistentStorage] = None
        self._storage_key: str = "prompts_template"
        # レポジトリ直下にキャッシュCSVを用意（/tmpでも可）
        self._cache_csv_path = os.path.join(
            Path(__file__).resolve().parent.parent.parent.absolute(),
            f"{self._storage_key}.csv",
        )
        try:
            self._storage = PersistentStorage(user_id="global")
        except Exception as e:
            # DataRobot環境外などでAPPLICATION_IDが未設定の場合に備える
            self.logger.warning(
                f"Persistent storage unavailable, using Null storage. reason={e}"
            )
            self._storage = NullPersistentStorage(user_id="global")
        self._cache = PersistentCache(self._storage)
        self._load()

    def _load(self) -> None:
        """テンプレートを再読み込み"""
        self.df = None
        if self.local and os.getenv("PROMPTS_TEMPLATE_PATH") is not None:
            self.csv_path = os.path.join(
                Path(__file__).resolve().parent.parent.parent.absolute(),
                os.getenv("PROMPTS_TEMPLATE_PATH"),
            )
            self.logger.info(
                f"Loading prompt templates from local path: {self.csv_path}"
            )
            self._load_templates()
            # ローカル読み込みに成功したら永続ストレージにもキャッシュ
            try:
                os.makedirs(os.path.dirname(self._cache_csv_path), exist_ok=True)
                atomic_write_csv(self._cache_csv_path, self.df)
                self._cache.save_from_file(self._storage_key, self._cache_csv_path)
            except Exception as e:
                self.logger.warning(f"Failed to cache local templates: {e}")
        else:
            # キャッシュから読み込み、なければレジストリから取得してキャッシュ
            prompts_template = PromptsTemplateAICatalog()
            if prompts_template.id:

                def _loader() -> pd.DataFrame:
                    return download_registry_dataset_as_dataframe(prompts_template.id)

                try:
                    self.df = self._cache.get_or_load_csv(
                        key=self._storage_key,
                        local_path=self._cache_csv_path,
                        loader=_loader,
                    )
                    # もしキャッシュから読めた場合は self.csv_path を設定してログを揃える
                    if os.path.exists(self._cache_csv_path):
                        self.csv_path = self._cache_csv_path
                except Exception as e:
                    self.logger.error(f"Error loading templates via cache: {e}")

    def _load_templates(self) -> None:
        """CSVファイルからテンプレートを読み込み"""
        try:
            if not os.path.exists(self.csv_path):
                raise FileNotFoundError(f"Template CSV not found: {self.csv_path}")

            # CSVを読み込み（エンコーディング指定、空行削除）
            self.df = pd.read_csv(
                self.csv_path,
                encoding="utf-8",
                dtype=str,  # 全列を文字列として読み込み
            ).dropna(subset=["name", "category", "prompt_text_template"])

            # 必須列の存在確認
            required_columns = [
                "name",
                "category",
                "description",
                "prompt_text_template",
            ]
            missing_columns = [
                col for col in required_columns if col not in self.df.columns
            ]
            if missing_columns:
                raise ValueError(f"Missing required columns: {missing_columns}")

            self.logger.info(
                f"✅ Loaded {len(self.df)} prompt templates from {self.csv_path}"
            )

        except Exception as e:
            self.logger.error(f"❌ Failed to load templates: {e}")
            self.df = pd.DataFrame(
                columns=["name", "category", "description", "prompt_text_template"]
            )

    def _ensure_loaded(self) -> None:
        if self.df is None:
            self._load()

    def get_all_categories(self) -> List[str]:
        """全カテゴリのリストを取得

        Returns:
            カテゴリ名のリスト（重複なし、アルファベット順）
        """
        self._ensure_loaded()
        if self.df is None or self.df.empty:
            return []
        return sorted(self.df["category"].unique().tolist())

    def get_templates_by_category(self, category: str) -> List[Dict[str, str]]:
        """指定カテゴリのテンプレート一覧を取得

        Args:
            category: カテゴリ名

        Returns:
            テンプレート辞書のリスト
        """
        self._ensure_loaded()
        if self.df is None or self.df.empty:
            return []

        filtered_df = self.df[self.df["category"] == category]
        return filtered_df.to_dict("records")

    def get_all_templates(self) -> List[Dict[str, str]]:
        """全テンプレートを取得

        Returns:
            全テンプレート辞書のリスト
        """
        self._ensure_loaded()
        if self.df is None or self.df.empty:
            return []
        return self.df.to_dict("records")

    def get_template_by_name(self, name: str) -> Optional[Dict[str, str]]:
        """名前でテンプレートを検索

        Args:
            name: テンプレート名

        Returns:
            該当テンプレートの辞書、見つからない場合はNone
        """
        self._ensure_loaded()
        if self.df is None or self.df.empty:
            return None

        matches = self.df[self.df["name"] == name]
        if matches.empty:
            return None

        return matches.iloc[0].to_dict()

    def search_templates(self, keyword: str) -> List[Dict[str, str]]:
        """キーワードでテンプレートを検索

        名前、説明、プロンプト内容からキーワードを検索

        Args:
            keyword: 検索キーワード

        Returns:
            マッチしたテンプレート辞書のリスト
        """
        self._ensure_loaded()
        if self.df is None or self.df.empty or not keyword:
            return []

        # 名前、説明、プロンプト内容のいずれかにキーワードが含まれるものを検索
        mask = (
            self.df["name"].str.contains(keyword, na=False, case=False)
            | self.df["description"].str.contains(keyword, na=False, case=False)
            | self.df["prompt_text_template"].str.contains(
                keyword, na=False, case=False
            )
        )

        return self.df[mask].to_dict("records")

    def get_template_count(self) -> int:
        """テンプレート総数を取得"""
        self._ensure_loaded()
        if self.df is None or self.df.empty:
            return 0
        return len(self.df)

    def get_category_summary(self) -> Dict[str, int]:
        """カテゴリ別テンプレート数のサマリを取得

        Returns:
            {カテゴリ名: テンプレート数} の辞書
        """
        self._ensure_loaded()
        if self.df is None or self.df.empty:
            return {}

        return self.df["category"].value_counts().to_dict()


# シングルトンインスタンス（グローバルで使用）
_template_manager_instance: Optional[TemplateManager] = None


def get_template_manager() -> TemplateManager:
    """グローバルなTemplateManagerインスタンスを取得

    初回呼び出し時にインスタンスを作成し、以降は同じインスタンスを返却。
    アプリケーション全体で一つのインスタンスを共有する。

    Returns:
        TemplateManagerインスタンス
    """
    global _template_manager_instance
    if _template_manager_instance is None:
        _template_manager_instance = TemplateManager()
    return _template_manager_instance


def reload_templates() -> None:
    """グローバルテンプレートマネージャーの再読み込み"""
    global _template_manager_instance
    if _template_manager_instance is not None:
        _template_manager_instance._load()
    else:
        _template_manager_instance = TemplateManager()


if __name__ == "__main__":
    # テスト実行
    logger = get_logger("TemplateManagerTest")
    logger.info("=== Prompt Template Manager Test ===")

    manager = TemplateManager()

    logger.info(f"Total templates: {manager.get_template_count()}")
    logger.info(f"Categories: {manager.get_all_categories()}")
    logger.info(f"Category summary: {manager.get_category_summary()}")

    # 営業カテゴリのテンプレート表示
    sales_templates = manager.get_templates_by_category("営業")
    logger.info(f"営業カテゴリのテンプレート数: {len(sales_templates)}")
    for template in sales_templates:
        logger.info(f"- {template['name']}: {template['description']}")

    # キーワード検索テスト
    search_results = manager.search_templates("売上")
    logger.info(f"'売上'検索結果: {len(search_results)}件")
    for result in search_results:
        logger.info(f"- {result['name']}")
