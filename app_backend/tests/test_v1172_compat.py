import asyncio
from pathlib import Path
from unittest.mock import AsyncMock

import pandas as pd
import pytest
from core.analyst_db import AnalystDB, InternalDataSourceType
from core.schema import AnalystChatMessage, AnalystDataset, UserFeedbackUpdate
from fastapi import HTTPException
from pydantic import ValidationError


def test_user_feedback_update_accepts_only_binary_rating() -> None:
    assert UserFeedbackUpdate(user_rating=1).user_rating == 1
    assert (
        UserFeedbackUpdate(user_rating=-1, user_feedback="bad").user_feedback == "bad"
    )

    with pytest.raises(ValidationError):
        UserFeedbackUpdate(user_rating=0)


def test_message_feedback_round_trip_and_cleanup(tmp_path: Path) -> None:
    asyncio.run(_assert_message_feedback_round_trip_and_cleanup(tmp_path))


async def _assert_message_feedback_round_trip_and_cleanup(tmp_path: Path) -> None:
    db = await AnalystDB.create(user_id="feedback", db_path=tmp_path)
    chat_id = await db.create_chat("feedback chat")
    message_id = await db.add_chat_message(
        chat_id,
        AnalystChatMessage(role="assistant", content="answer", components=[]),
    )

    assert await db.update_message_feedback(message_id, 1, "useful") is True

    single_message = await db.get_chat_message(message_id)
    assert single_message is not None
    assert single_message.user_rating == 1
    assert single_message.user_feedback == "useful"

    listed_message = (await db.get_chat_messages(chat_id=chat_id))[0]
    assert listed_message.user_rating == 1
    assert listed_message.user_feedback == "useful"

    await db.update_chat_message(
        message_id,
        AnalystChatMessage(role="assistant", content="updated", components=[]),
    )
    updated_message = await db.get_chat_message(message_id)
    assert updated_message is not None
    assert updated_message.content == "updated"
    assert updated_message.user_rating == 1
    assert updated_message.user_feedback == "useful"

    assert await db.delete_chat_message(message_id) is True
    assert await db.get_chat_message(message_id) is None


def test_feedback_endpoint_returns_updated_message() -> None:
    asyncio.run(_assert_feedback_endpoint_returns_updated_message())


async def _assert_feedback_endpoint_returns_updated_message() -> None:
    from core.routers.chats import update_message_feedback

    analyst_db = AsyncMock()
    analyst_db.update_message_feedback.return_value = True
    analyst_db.get_chat_message.return_value = AnalystChatMessage(
        role="assistant",
        content="answer",
        components=[],
        id="msg-1",
        chat_id="chat-1",
        user_rating=-1,
        user_feedback="missed detail",
    )

    response = await update_message_feedback(
        message_id="msg-1",
        feedback=UserFeedbackUpdate(user_rating=-1, user_feedback="missed detail"),
        analyst_db=analyst_db,
    )

    assert response.user_rating == -1
    assert response.user_feedback == "missed detail"
    analyst_db.update_message_feedback.assert_awaited_once_with(
        message_id="msg-1",
        user_rating=-1,
        user_feedback="missed detail",
    )


def test_feedback_endpoint_returns_404_for_missing_message() -> None:
    asyncio.run(_assert_feedback_endpoint_returns_404_for_missing_message())


async def _assert_feedback_endpoint_returns_404_for_missing_message() -> None:
    from core.routers.chats import update_message_feedback

    analyst_db = AsyncMock()
    analyst_db.update_message_feedback.return_value = False

    with pytest.raises(HTTPException) as exc_info:
        await update_message_feedback(
            message_id="missing",
            feedback=UserFeedbackUpdate(user_rating=1),
            analyst_db=analyst_db,
        )

    assert exc_info.value.status_code == 404


def test_dictionary_error_is_persisted_and_cleared(tmp_path: Path) -> None:
    asyncio.run(_assert_dictionary_error_is_persisted_and_cleared(tmp_path))


async def _assert_dictionary_error_is_persisted_and_cleared(tmp_path: Path) -> None:
    db = await AnalystDB.create(user_id="dict-error", db_path=tmp_path)
    dataset = AnalystDataset(
        name="sales",
        data=pd.DataFrame({"revenue": [10, 20]}),
    )
    await db.register_dataset(dataset, data_source=InternalDataSourceType.FILE)

    assert await db.get_dictionary_error("sales") is None
    await db.mark_dictionary_failed("sales", "LLM service unavailable")
    assert await db.get_dictionary_error("sales") == "LLM service unavailable"

    reopened = await AnalystDB.create(user_id="dict-error", db_path=tmp_path)
    assert await reopened.get_dictionary_error("sales") == "LLM service unavailable"

    await reopened.clear_dictionary_error("sales")
    assert await reopened.get_dictionary_error("sales") is None


def test_dictionaries_response_exposes_failed_dictionary_error() -> None:
    asyncio.run(_assert_dictionaries_response_exposes_failed_dictionary_error())


async def _assert_dictionaries_response_exposes_failed_dictionary_error() -> None:
    from core.routers.dictionaries import get_dictionaries

    analyst_db = AsyncMock()
    analyst_db.list_analyst_datasets.return_value = ["sales"]
    analyst_db.get_data_dictionary.return_value = None
    analyst_db.get_dictionary_error.return_value = "LLM service unavailable"

    response = await get_dictionaries(analyst_db=analyst_db)

    assert response[0].name == "sales"
    assert response[0].in_progress is False
    assert response[0].error == "LLM service unavailable"


def test_build_app_skips_dependency_install_when_prebundled_marker_exists() -> None:
    script = Path("app_backend/build-app.sh").read_text()

    assert "/.datarobot-pre-bundled" in script
    assert "uv sync" in script


def test_infra_allows_custom_execution_environment_ids() -> None:
    source = Path("infra/infra/app_backend.py").read_text()

    assert "APPLICATION_EXECUTION_ENVIRONMENT_ID" in source
    assert "APPLICATION_EXECUTION_ENVIRONMENT_VERSION_ID" in source
    assert "base_environment_version_id" in source


def test_llm_client_uses_genai_semantic_attributes() -> None:
    source = Path("core/src/core/llm_client.py").read_text()

    assert "gen_ai.request.model" in source
    assert "gen_ai.provider.name" in source
    assert "gen_ai.usage.input_tokens" in source
    assert "LLM_CAPTURE_CONTENT" in source
