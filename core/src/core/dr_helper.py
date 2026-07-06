import asyncio
import json
from datetime import datetime
from typing import Any

import datarobot as dr
import httpx
from datarobot.client import RESTClientObject
from pydantic import ValidationError

from core.logging_helper import get_logger
from core.resources import LLMDeployment

logger = get_logger()
_ACTUALS_POST_DELAY_SECONDS = 60
_ACTUALS_RESPONSE_BODY_LOG_LIMIT = 1000


def initialize_deployment() -> tuple[RESTClientObject, str]:
    try:
        dr_client = dr.Client()
        chat_agent_deployment_id = LLMDeployment().id
        deployment_chat_base_url = (
            dr_client.endpoint + f"/deployments/{chat_agent_deployment_id}/"
        )
        return dr_client, deployment_chat_base_url
    except ValidationError as e:
        raise ValueError(
            "Unable to load Deployment ID."
            "If running locally, verify you have selected the correct "
            "stack and that it is active using `pulumi stack output`. "
            "If running in DataRobot, verify your runtime parameters have been set correctly."
        ) from e


async def async_submit_actuals_to_datarobot(
    association_id: str, telemetry_json: dict[str, Any] | None = None
) -> None:
    telemetry_payload = dict(telemetry_json or {})
    logger.info(
        "Delaying actuals post to DataRobot: "
        f"delay_seconds={_ACTUALS_POST_DELAY_SECONDS} "
        f"association_id={association_id} "
        f"query_type={telemetry_payload.get('query_type')}"
    )
    await asyncio.sleep(_ACTUALS_POST_DELAY_SECONDS)

    dr_client, deployment_chat_base_url = initialize_deployment()
    deployment_chat_actuals_url = deployment_chat_base_url + "actuals/fromJSON/"
    telemetry_payload["endTimestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    payload = {
        "data": [
            {
                "associationId": association_id,
                "actualValue": json.dumps(telemetry_payload, ensure_ascii=False),
            }
        ]
    }
    headers = dr_client.headers
    async with httpx.AsyncClient() as client:
        try:
            logger.info(
                "Posting actuals to DataRobot: "
                f"url={deployment_chat_actuals_url} "
                f"association_id={association_id} "
                f"query_type={telemetry_payload.get('query_type')}"
            )
            response = await client.post(
                deployment_chat_actuals_url, json=payload, headers=headers, timeout=5
            )
            status_code = getattr(response, "status_code", None)
            location = getattr(response, "headers", {}).get("Location") or getattr(
                response, "headers", {}
            ).get("location")
            response_text = getattr(response, "text", "")
            response_body = response_text[:_ACTUALS_RESPONSE_BODY_LOG_LIMIT]
            log_message = (
                "Actuals post response: "
                f"url={deployment_chat_actuals_url} "
                f"association_id={association_id} "
                f"status_code={status_code} "
                f"location={location} "
                f"response_body={response_body!r}"
            )
            if status_code is not None and 200 <= status_code < 300:
                logger.info(log_message)
            else:
                logger.error(f"Actuals post failed: {log_message}")
        except Exception as e:
            logger.error(
                "Failed posting actuals: "
                f"url={deployment_chat_actuals_url} "
                f"association_id={association_id} "
                f"error={e}"
            )
