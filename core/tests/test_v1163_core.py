import pytest
from pydantic import ValidationError

from core.constants import MAX_PROMPT_LENGTH
from core.schema import ChatMessagePayload


def test_core_chat_message_payload_enforces_prompt_limit() -> None:
    ChatMessagePayload(message="a" * MAX_PROMPT_LENGTH)

    with pytest.raises(ValidationError):
        ChatMessagePayload(message="a" * (MAX_PROMPT_LENGTH + 1))
