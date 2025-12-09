from abc import ABC, abstractmethod

from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam
from openai.types.chat.chat_completion_system_message_param import (
    ChatCompletionSystemMessageParam,
)
from openai.types.chat.chat_completion_user_message_param import (
    ChatCompletionUserMessageParam,
)

from utils.customize.domain.question_refiner.domain import (
    QuestionRefinementRequest,
)
from utils.logging_helper import get_logger

logger = get_logger(__name__)


class IRefinerDataInfoMessageFactory(ABC):
    async def create_message(self) -> list[ChatCompletionMessageParam]:
        return [
            await self.build_data_shape_info(),
            await self.build_sample_data_info(),
            await self.build_dictionary_data(),
        ]

    @abstractmethod
    async def build_dictionary_data(self) -> ChatCompletionMessageParam:
        pass

    @abstractmethod
    async def build_data_shape_info(self) -> ChatCompletionMessageParam:
        pass

    @abstractmethod
    async def build_sample_data_info(self) -> ChatCompletionMessageParam:
        pass


class RefineUserPromptBuilder:
    def __init__(self, datainfo_factory: IRefinerDataInfoMessageFactory = None):
        self.datainfo_factory = datainfo_factory

    async def build(self, request: QuestionRefinementRequest) -> str:
        messages = [
            ChatCompletionUserMessageParam(
                role="user", content=f"User Direction: {request.user_direction}"
            )
        ]
        if self.datainfo_factory:
            messages.extend(await self.datainfo_factory.create_message())
        return messages


class MessageFactory:
    @staticmethod
    def create_message(
        system_prompt: str, user_prompt: list[ChatCompletionMessageParam]
    ) -> list[ChatCompletionMessageParam]:
        messages: list[ChatCompletionMessageParam] = [
            ChatCompletionSystemMessageParam(role="system", content=system_prompt),
        ]
        messages.extend(user_prompt)
        return messages
