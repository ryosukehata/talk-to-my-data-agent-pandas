from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class Item(BaseModel):
    id: str
    name: Optional[str] = None

    @classmethod
    def create_filtered_list(
        cls, items_data: List[Dict[str, Any]], exclude_user_prompt: bool = True
    ) -> List["Item"]:
        """
        items_dataからItemリストを作成し、条件に応じてフィルタリングする

        Args:
            items_data: 元データのリスト
            exclude_user_prompt: user_prompt_を含むアイテムを除外するかどうか

        Returns:
            フィルタリングされたItemのリスト
        """
        filtered_items = []

        for item in items_data:
            if "id" not in item:
                continue

            # user_prompt_を含むアイテムの除外判定
            if (
                exclude_user_prompt
                and item.get("name")
                and "user_prompt_" in item["name"]
            ):
                continue

            filtered_items.append(cls(id=item["id"], name=item.get("name")))

        return filtered_items
