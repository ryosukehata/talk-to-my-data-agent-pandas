import logging
from typing import Dict, List, Optional

import aiohttp
from domain.item_manager import IItemManager
from domain.reboot_manager import IRebootManager

logger = logging.getLogger(__name__)

class DataRobotItemManager(IItemManager):
    def __init__(self, endpoint: str, token: str):
        self.endpoint = endpoint
        self.headers = {"Authorization": f"Bearer {token}"}

    async def fetch_items(self, app_id: str) -> Optional[List[Dict]]:
        url = f"{self.endpoint}/keyValues/?entityType=customApplication&entityId={app_id}"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            try:
                async with session.get(url) as resp:
                    resp.raise_for_status()
                    data = await resp.json()
                    return data.get("data", [])
            except Exception as e:
                logger.error(f"❌ fetch_items失敗: {e}")
                return None

    async def delete_item(self, item_id: str):
        url = f"{self.endpoint}/keyValues/{item_id}/"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            try:
                async with session.delete(url) as resp:
                    resp.raise_for_status()
                    logger.info(f"🗑️ {item_id} を削除しました")
            except Exception as e:
                logger.error(f"❌ delete_item失敗: {e} for {item_id}")
                raise


class DataRobotRebootManager(IRebootManager):
    def __init__(self, endpoint: str, token: str):
        self.endpoint = endpoint
        self.headers = {"Authorization": f"Bearer {token}"}

    async def stop_app(self, app_id: str) -> None:
        url = f"{self.endpoint}/customApplications/{app_id}/stop"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            try:
                async with session.post(url) as resp:
                    resp.raise_for_status()
                    logger.info(f"🛑 {app_id} を停止しました")
            except Exception as e:
                logger.error(f"❌ stop_app失敗: {e} for {app_id}")
                raise

    async def start_app(self, app_id: str) -> None:
        url = f"{self.endpoint}/customApplications/{app_id}/start"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            try:
                async with session.post(url) as resp:
                    resp.raise_for_status()
                    logger.info(f"▶️ {app_id} を起動しました")
            except Exception as e:
                logger.error(f"❌ start_app失敗: {e} for {app_id}")
                raise
