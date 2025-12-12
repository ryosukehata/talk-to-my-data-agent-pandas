"""
Report Builder - Infrastructure Layer - LLM Summary Generator

LLMを使用してレポートのサマリーと結論を生成する
"""

from __future__ import annotations

from typing import Any

from utils.constants import ALTERNATIVE_LLM_BIG
from utils.customize.domain.report.service_interface import (
    IReportSummaryService,
    ReportGeneratedSummary,
)
from utils.llm_client import AsyncLLMClient
from utils.logging_helper import get_logger
from utils.token_tracking import TokenUsageTracker

logger = get_logger("LLMReportSummaryService")


class LLMReportSummaryService(IReportSummaryService):
    """LLMを使用してレポートのサマリーと結論を生成するサービス"""

    def __init__(
        self,
        model: str | None = None,
        token_tracker: TokenUsageTracker | None = None,
    ):
        self._model = model or ALTERNATIVE_LLM_BIG
        self._token_tracker = token_tracker

    async def generate(
        self,
        messages: list[dict[str, Any]],
    ) -> ReportGeneratedSummary:
        logger.info("Calling LLM for summary generation...")

        async with AsyncLLMClient(token_tracker=self._token_tracker) as client:
            response, _ = await client.chat.completions.create_with_completion(
                model=self._model,
                messages=messages,
                response_model=ReportGeneratedSummary,
            )

        logger.info("Summary and conclusion generated successfully")
        return response
