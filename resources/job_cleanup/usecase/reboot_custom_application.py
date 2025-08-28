import logging

from domain.reboot_manager import IRebootManager

logger = logging.getLogger(__name__)
    
class RebootUsecase:
    def __init__(self, reboot_manager: IRebootManager):
        self.reboot_manager = reboot_manager

    async def run(self, app_id: str):
        await self.reboot_manager.stop_app(app_id)
        await self.reboot_manager.start_app(app_id)
