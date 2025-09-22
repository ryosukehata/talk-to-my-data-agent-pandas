from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class IItemManager(ABC):
    @abstractmethod
    async def fetch_items(self, app_id: str) -> Optional[List[Dict[str, Any]]]:
        pass

    @abstractmethod
    async def delete_item(self, item_id: str) -> None:
        pass
