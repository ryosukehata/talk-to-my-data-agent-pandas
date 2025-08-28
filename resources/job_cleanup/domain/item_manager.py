from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class IItemManager(ABC):

    @abstractmethod
    async def fetch_items(self, app_id: str) -> Optional[List[Dict]]:
        pass
    
    @abstractmethod
    async def delete_item(self, item_id: str) -> None:
        pass