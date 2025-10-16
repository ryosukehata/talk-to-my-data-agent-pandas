import json
import os

from utils.logging_helper import get_logger
from utils.persistent_storage import PersistentStorage


class UserPrompts:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.filename = f"user_prompt_{self.user_id}"
        self.json_filename = self.filename + ".json"
        self._storage = PersistentStorage(self.user_id)

    def _write_prompts_safely(self, prompts: list[dict]) -> None:
        """プロンプトデータを原子的にファイルに書き込む

        Args:
            prompts: 書き込むプロンプトのリスト
        """
        temp_filename = self.json_filename + ".tmp"

        try:
            # 一時ファイルに書き込み
            with open(temp_filename, "w", encoding="utf-8") as f:
                json.dump(prompts, f, ensure_ascii=False, indent=4)

            # 原子的にファイルを置換
            os.replace(temp_filename, self.json_filename)

        except Exception:
            # 失敗時は一時ファイルをクリーンアップ
            if os.path.exists(temp_filename):
                os.remove(temp_filename)
            raise

    def save_prompt(self, name: str, prompt: str, description: str = None):
        """新しいプロンプトを保存する
        to do load_promptsを経ずにいきなり保存すると前のプロンプトが消えるので、loadしてから追加する
        """
        prompts = self.load_prompts()  # ← 永続ストレージと同期
        new_prompt = {
            "name": name,
            "category": "カスタム",
            "description": description,
            "prompt_text_template": prompt,
        }

        # 新しいプロンプトを追加
        prompts.append(new_prompt)

        # ファイルに安全に書き込む
        self._write_prompts_safely(prompts)

        # 永続ストレージに保存
        self._storage.save_to_storage(self.filename, self.json_filename)
        get_logger().info(f"User prompt saved for user_id: {self.user_id}")

    def load_prompts(self) -> list[dict]:
        # 永続ストレージから読み込む
        if not os.path.exists(self.json_filename):
            self._storage.fetch_from_storage(self.filename, self.json_filename)

        # ファイルからJSONデータを読み込む (load)
        try:
            with open(self.json_filename, "r", encoding="utf-8") as f:
                prompts = json.load(f)
                # リストでなければ空リストを返す
                if not isinstance(prompts, list):
                    get_logger().warning(
                        f"Invalid prompt format for user_id: {self.user_id}. "
                        f"Expected list, got {type(prompts).__name__}"
                    )
                    return []
                get_logger().info(f"User prompt loaded for user_id: {self.user_id}")
                return prompts
        except (FileNotFoundError, json.JSONDecodeError):
            get_logger().warning(f"No prompt file found for user_id: {self.user_id}")
            return []

    def delete_prompt(self, name: str) -> bool:
        """指定された名前のプロンプトを削除する

        Args:
            name: 削除するプロンプトの名前

        Returns:
            bool: 削除に成功した場合True、見つからなかった場合False
        """
        # 既存のプロンプトを読み込む
        prompts = self.load_prompts()

        # 指定された名前のプロンプトを検索して削除
        original_length = len(prompts)
        prompts = [p for p in prompts if p.get("name") != name]

        # 削除されたかどうかをチェック
        if len(prompts) == original_length:
            get_logger().warning(
                f"Prompt '{name}' not found for user_id: {self.user_id}"
            )
            return False

        # ファイルに安全に書き込む
        self._write_prompts_safely(prompts)

        # 永続ストレージに保存
        self._storage.save_to_storage(self.filename, self.json_filename)
        get_logger().info(f"User prompt '{name}' deleted for user_id: {self.user_id}")
        return True

    def list_prompt_names(self) -> list[str]:
        """保存されているプロンプトの名前一覧を取得する

        Returns:
            list[str]: プロンプト名のリスト
        """
        prompts = self.load_prompts()
        return [prompt.get("name", "") for prompt in prompts if prompt.get("name")]

    def get_prompt_by_name(self, name: str) -> dict | None:
        """指定された名前のプロンプトを取得する

        Args:
            name: 取得するプロンプトの名前

        Returns:
            dict | None: 見つかった場合はプロンプト辞書、見つからなければNone
        """
        prompts = self.load_prompts()
        for prompt in prompts:
            if prompt.get("name") == name:
                return prompt
        return None
