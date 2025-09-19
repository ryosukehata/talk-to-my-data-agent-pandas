import asyncio
import logging
import os

from external.datarobot.datarobot_api import (
    DataRobotItemManager,
    DataRobotRebootManager,
)
from usecase.delete_items import DeleteItemsUsecase
from usecase.reboot_custom_application import RebootUsecase

logging.basicConfig(level=logging.INFO)


def main():
    app_id = os.environ.get("DATAROBOT_APPLICATION_ID")
    endpoint = os.environ["DATAROBOT_ENDPOINT"]
    token = os.environ["DATAROBOT_API_TOKEN"]

    datarobot_item_api = DataRobotItemManager(endpoint, token)
    delete_usecase = DeleteItemsUsecase(datarobot_item_api)
    asyncio.run(delete_usecase.run(app_id))

    datarobot_reboot_api = DataRobotRebootManager(endpoint, token)
    reboot_usecase = RebootUsecase(datarobot_reboot_api)
    asyncio.run(reboot_usecase.run(app_id))


if __name__ == "__main__":
    main()
