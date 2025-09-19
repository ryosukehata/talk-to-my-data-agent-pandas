from abc import ABC, abstractmethod


class IRebootManager(ABC):
    @abstractmethod
    async def stop_app(self, app_id: str) -> None:
        pass

    @abstractmethod
    async def start_app(self, app_id: str) -> None:
        pass
