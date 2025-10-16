import asyncio
import logging

from domain.entities import Item
from domain.item_manager import IItemManager

logger = logging.getLogger(__name__)


class DeleteItemsUsecase:
    def __init__(self, item_manager: IItemManager, max_concurrent: int = 5):
        self.item_manager = item_manager
        self.sem = asyncio.Semaphore(max_concurrent)

    async def run(self, app_id: str, exclude_user_prompt: bool = True):
        items_data = await self.item_manager.fetch_items(app_id)
        logger.info(f"Fetched items: {len(items_data)}")
        if not items_data:
            logger.warning("⚠️ 削除対象なし")
            return

        items = Item.create_filtered_list(
            items_data, exclude_user_prompt=exclude_user_prompt
        )
        logger.info(f"⚡️ {len(items)}件を削除開始")

        tasks = [self._delete_with_limit(item) for item in items]
        await asyncio.gather(*tasks)

    async def _delete_with_limit(self, item: Item):
        async with self.sem:
            try:
                await self.item_manager.delete_item(item.id)
            except Exception:
                logger.error(f"失敗: {item.id}")
