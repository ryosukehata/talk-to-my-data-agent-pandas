"""
Question Refiner - Domain Models

ドメインモデルの定義（エンティティと値オブジェクト）
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class RefinedQuestion(BaseModel):
    """洗練された質問（値オブジェクト）"""

    original_direction: str = Field(description="元のふわっとした質問の方向性")
    refined_question: str = Field(
        description="データ概要を踏まえて生成された具体的な質問"
    )
    reasoning: str = Field(description="なぜこの質問を生成したかの理由")
    relevant_columns: list[str] = Field(
        description="この質問に関連するカラム名のリスト", default_factory=list
    )


class QuestionRefinementRequest(BaseModel):
    """質問洗練リクエスト（値オブジェクト）"""

    user_direction: str = Field(description="ユーザーの質問の方向性")
    data_source: str = "file"


class QuestionRefinementResult(BaseModel):
    """質問生成の結果（値オブジェクト）"""

    success: bool = Field(description="生成が成功したかどうか")
    refined_questions: list[RefinedQuestion] = Field(
        description="生成された質問のリスト", default_factory=list
    )
    error: str | None = Field(description="エラーメッセージ（失敗時）", default=None)
