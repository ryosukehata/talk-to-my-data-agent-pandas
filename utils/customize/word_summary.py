from __future__ import annotations

from typing import List

from utils.llm_client import AsyncLLMClient
from utils.customize.prompts import REPORT_WORD_SUMMARY_SYSTEM_PROMPT


async def generate_summary_and_conclusion(
    title: str,
    sections: List[str],
    token_tracker=None,
) -> tuple[str, str]:
    messages = [
        {
            "role": "system",
            "content": REPORT_WORD_SUMMARY_SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": _build_user_prompt(title, sections),
        },
    ]

    async with AsyncLLMClient(token_tracker=token_tracker) as client:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
        )

    content = response.choices[0].message.content if response.choices else ""

    if not content:
        return _fallback_summary(title, sections), _fallback_conclusion(sections)

    summary, conclusion = _parse_summary_response(content)
    return summary, conclusion


def _build_user_prompt(title: str, sections: List[str]) -> str:
    bullet_points = "

".join(f"### Section {idx + 1}
{section}" for idx, section in enumerate(sections))
    return f"""タイトル: {title}

分析内容（要約用）:
{bullet_points}
"""


def _parse_summary_response(content: str) -> tuple[str, str]:
    parts = content.split('
---
')
    if len(parts) >= 2:
        return parts[0].strip(), parts[1].strip()
    return content.strip(), _fallback_conclusion([])


def _fallback_summary(title: str, sections: List[str]) -> str:
    return (
        f"本レポートは「{title}」に関するデータ分析結果をまとめたものです。
"
        f"合計{len(sections)}件の分析を実施し、主な知見を整理しました。"
    )


def _fallback_conclusion(sections: List[str]) -> str:
    return (
        "以上の分析結果を踏まえ、次のアクションを検討してください。"
        "詳細な意思決定には、各セクションの知見を精査することを推奨します。"
    )
