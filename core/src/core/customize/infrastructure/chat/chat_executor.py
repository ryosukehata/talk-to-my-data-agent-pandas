"""
Report Builder - Infrastructure Layer - Chat Executor

run_complete_analysis_taskを呼び出してチャットを実行する
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from core.logging_helper import get_logger
from core.schema import AnalystChatMessage, ChatRequest

if TYPE_CHECKING:
    from starlette.requests import Request

    from core.analyst_db import AnalystDB

logger = get_logger("ChatExecutor")


@dataclass
class ChatResult:
    success: bool
    message: AnalystChatMessage | None = None
    chat_id: str | None = None
    error_message: str | None = None


class ChatExecutor:
    async def execute(
        self,
        question: str,
        analyst_db: AnalystDB,
        chat_id: str,
        message_id: str,
        data_source: str,
        request: Request,
        enable_chart_generation: bool = True,
        enable_business_insights: bool = True,
    ) -> ChatResult:
        logger.info(f"Executing chat for question: {question[:50]}...")

        try:
            from core.rest_api import run_complete_analysis_task

            created_chat_id = await analyst_db.create_chat(
                chat_name=f"Report Question: {question[:30]}...",
                data_source=data_source,
            )
            actual_chat_id = chat_id or created_chat_id

            user_message = AnalystChatMessage(
                role="user",
                content=question,
                components=[],
            )
            actual_message_id = await analyst_db.add_chat_message(
                chat_id=actual_chat_id,
                message=user_message,
            )

            chat_request = ChatRequest(messages=[{"role": "user", "content": question}])

            await run_complete_analysis_task(
                chat_request=chat_request,
                data_source=data_source,
                analyst_db=analyst_db,
                chat_id=actual_chat_id,
                message_id=actual_message_id,
                enable_chart_generation=enable_chart_generation,
                enable_business_insights=enable_business_insights,
                request=request,
            )

            messages = await analyst_db.get_chat_messages(chat_id=actual_chat_id)
            assistant_messages = [m for m in messages if m.role == "assistant"]

            if not assistant_messages:
                logger.error(f"No assistant message found for chat: {actual_chat_id}")
                return ChatResult(
                    success=False, error_message="No assistant response generated"
                )

            latest_message = assistant_messages[-1]
            return ChatResult(
                success=True, message=latest_message, chat_id=actual_chat_id
            )

        except Exception as exc:
            logger.error(f"Chat execution failed: {exc}")
            return ChatResult(success=False, error_message=str(exc))
