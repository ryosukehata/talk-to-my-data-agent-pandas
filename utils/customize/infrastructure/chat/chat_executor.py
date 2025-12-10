"""
Report Builder - Infrastructure Layer - Chat

チャット実行の実装（run_complete_analysis_taskを利用）
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from utils.logging_helper import get_logger
from utils.rest_api import run_complete_analysis_task
from utils.schema import AnalystChatMessage, ChatRequest

if TYPE_CHECKING:
    from starlette.requests import Request

    from utils.analyst_db import AnalystDB

logger = get_logger("ChatExecutor")


@dataclass
class ChatResult:
    """チャット実行結果"""

    success: bool
    message: AnalystChatMessage | None = None
    chat_id: str | None = None
    error_message: str | None = None


class ChatExecutor:
    """チャット実行を担当するインフラストラクチャ

    run_complete_analysis_taskを呼び出し、質問をチャットシステムに投げて結果を取得する。
    """

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
        """質問をチャットシステムに投げて結果を取得

        Args:
            question: 質問文
            analyst_db: AnalystDBインスタンス
            chat_id: チャットID
            message_id: メッセージID
            data_source: データソース種別
            request: HTTPリクエスト
            enable_chart_generation: グラフ生成を有効にするか
            enable_business_insights: ビジネスインサイトを有効にするか

        Returns:
            ChatResult: 実行結果
        """
        logger.info(f"Executing chat for question: {question[:50]}...")

        try:
            # 1. チャットを作成
            created_chat_id = await analyst_db.create_chat(
                chat_name=f"Report Question: {question[:30]}...",
                data_source=data_source,
            )
            # chat_idが渡された場合はそれを使用、なければ作成したものを使用
            actual_chat_id = chat_id if chat_id else created_chat_id

            # 2. ユーザーメッセージを作成して保存
            user_message = AnalystChatMessage(
                role="user",
                content=question,
                components=[],
            )
            actual_message_id = await analyst_db.add_chat_message(
                chat_id=actual_chat_id,
                message=user_message,
            )

            logger.info(f"Created chat: {actual_chat_id}, message: {actual_message_id}")

            # 3. ChatRequestを作成
            chat_request = ChatRequest(messages=[{"role": "user", "content": question}])

            # 4. 分析を実行
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

            # 5. 結果をanalyst_dbから取得（アシスタントメッセージ）
            messages = await analyst_db.get_chat_messages(chat_id=actual_chat_id)
            assistant_messages = [m for m in messages if m.role == "assistant"]

            if not assistant_messages:
                logger.error(f"No assistant message found for chat: {actual_chat_id}")
                return ChatResult(
                    success=False,
                    error_message="No assistant response generated",
                )

            # 最新のアシスタントメッセージを返す
            latest_message = assistant_messages[-1]
            logger.info(f"Chat execution completed: {actual_message_id}")
            return ChatResult(
                success=True,
                message=latest_message,
                chat_id=actual_chat_id,
            )

        except Exception as e:
            logger.error(f"Chat execution failed: {e}")
            return ChatResult(success=False, error_message=str(e))
