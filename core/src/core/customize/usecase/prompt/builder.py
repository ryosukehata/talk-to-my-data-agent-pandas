from abc import ABC, abstractmethod

from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam
from openai.types.chat.chat_completion_system_message_param import (
    ChatCompletionSystemMessageParam,
)
from openai.types.chat.chat_completion_user_message_param import (
    ChatCompletionUserMessageParam,
)

from core.customize.domain.question_refiner.domain import (
    QuestionRefinementRequest,
)
from core.customize.domain.report.domain import Report
from core.customize.domain.report.service_interface import ReportSectionData
from core.customize.prompts import REPORT_WORD_SUMMARY_SYSTEM_PROMPT
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

    async def build(
        self, request: QuestionRefinementRequest
    ) -> list[ChatCompletionMessageParam]:
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


class ISummarySectionDataFactory(ABC):
    """サマリー用セクションデータ取得のインターフェース"""

    @abstractmethod
    async def create_message(
        self,
        report: Report,
        sections: list[ReportSectionData] | None = None,
    ) -> list[ChatCompletionMessageParam]:
        pass


class SummaryPromptBuilder:
    def __init__(
        self,
        section_data_factory: ISummarySectionDataFactory | None = None,
        system_prompt: str | None = None,
    ):
        self._section_data_factory = section_data_factory
        self._system_prompt = system_prompt or REPORT_WORD_SUMMARY_SYSTEM_PROMPT

    async def build(
        self,
        report: Report,
        sections: list[ReportSectionData] | None = None,
    ) -> list[ChatCompletionMessageParam]:
        if self._section_data_factory is None:
            user_message = self._build_default_user_message(report)
            return [
                ChatCompletionSystemMessageParam(
                    role="system", content=self._system_prompt
                ),
                user_message,
            ]

        user_messages = await self._section_data_factory.create_message(
            report,
            sections,
        )

        messages: list[ChatCompletionMessageParam] = [
            ChatCompletionSystemMessageParam(role="system", content=self._system_prompt)
        ]
        messages.extend(user_messages)
        return messages

    def _build_default_user_message(
        self, report: Report
    ) -> ChatCompletionUserMessageParam:
        theme_line = report.theme or "テーマ情報が利用できません"
        content = (
            f"# レポートタイトル\n{report.title}\n\n"
            f"# レポートテーマ\n{theme_line}\n\n"
            "# 分析セクション\nセクションの詳細を取得できませんでしたが、タイトルとテーマに基づき要約を生成してください。\n"
        )
        return ChatCompletionUserMessageParam(role="user", content=content)
