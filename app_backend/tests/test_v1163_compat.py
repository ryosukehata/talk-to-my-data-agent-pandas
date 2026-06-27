import pytest
from core.constants import MAX_PROMPT_LENGTH
from core.schema import ChatMessagePayload
from pydantic import ValidationError


def test_chat_message_payload_allows_max_prompt_length() -> None:
    payload = ChatMessagePayload(message="a" * MAX_PROMPT_LENGTH)

    assert payload.message == "a" * MAX_PROMPT_LENGTH


def test_chat_message_payload_rejects_prompt_over_max_length() -> None:
    with pytest.raises(ValidationError):
        ChatMessagePayload(message="a" * (MAX_PROMPT_LENGTH + 1))
