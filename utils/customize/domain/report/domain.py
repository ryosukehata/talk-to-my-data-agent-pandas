"""
Report Builder - Domain Models

ドメインモデルの定義（エンティティと値オブジェクト）
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

# ============================================================
# 値オブジェクト (Value Objects)
# ============================================================


class ReportStatus(str, Enum):
    """レポートのステータス"""

    PENDING = "pending"  # 初期化完了、質問生成待ち
    REFINING = "refining"  # 質問洗練中
    CHAT_PROCESSING = "chat_processing"  # チャット実行中
    COMPLETED = "completed"  # 質問実行が全て完了
    GENERATING_WORD = "generating_word"  # Word生成中
    DONE = "done"  # Word生成完了
    ERROR = "error"  # エラー発生


class QuestionStatus(str, Enum):
    """各質問のステータス"""

    PENDING = "pending"  # 未実行（洗練待ち）
    REFINING = "refining"  # 洗練中
    READY = "ready"  # 洗練済み・実行待ち
    RUNNING = "running"  # 実行中
    COMPLETED = "completed"  # 完了
    ERROR = "error"  # エラー


# ============================================================
# エンティティ (Entities)
# ============================================================


class ReportQuestion(BaseModel):
    """レポート内の各質問"""

    question_id: str = Field(description="質問の一意識別子")
    original_direction: str = Field(description="元のふわっとした方向性")
    refined_question: str = Field(description="洗練された具体的な質問")
    status: QuestionStatus = Field(
        default=QuestionStatus.PENDING, description="質問の実行ステータス"
    )
    chat_id: str | None = Field(default=None, description="実行時のチャットID")
    message_id: str | None = Field(default=None, description="実行時のメッセージID")
    error_message: str | None = Field(default=None, description="エラーメッセージ")
    executed_at: datetime | None = Field(default=None, description="実行完了日時")


class ReportSection(BaseModel):
    """Wordレポートの各セクション"""

    heading: str = Field(description="セクション見出し")
    content: str = Field(description="セクション本文")
    chart_path: str | None = Field(default=None, description="グラフ画像パス")


class Report(BaseModel):
    """レポートエンティティ（集約ルート）"""

    report_id: str = Field(description="レポートの一意識別子")
    title: str = Field(description="レポートタイトル")
    theme: str = Field(default="", description="レポートのテーマ")
    user_id: str = Field(description="作成者のユーザーID")
    data_source: str = Field(default="file", description="データソース種別")
    status: ReportStatus = Field(
        default=ReportStatus.PENDING, description="レポートのステータス"
    )
    questions: list[ReportQuestion] = Field(
        default_factory=list, description="質問リスト"
    )
    summary: str | None = Field(default=None, description="エグゼクティブサマリー")
    conclusion: str | None = Field(default=None, description="結論")
    word_file_path: str | None = Field(
        default=None, description="生成されたWordファイルパス"
    )
    created_at: datetime = Field(default_factory=datetime.now, description="作成日時")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新日時")
    error_message: str | None = Field(default=None, description="エラーメッセージ")

    def to_dict(self) -> dict[str, Any]:
        """辞書形式に変換（永続化用）"""
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Report:
        """辞書から復元"""
        return cls.model_validate(data)

    def get_progress(self) -> tuple[int, int]:
        """進捗を取得 (完了数, 全体数)"""
        completed = sum(
            1 for q in self.questions if q.status == QuestionStatus.COMPLETED
        )
        return completed, len(self.questions)

    def is_all_questions_completed(self) -> bool:
        """全ての質問が完了したか"""
        return all(q.status == QuestionStatus.COMPLETED for q in self.questions)

    def get_next_pending_question(self) -> ReportQuestion | None:
        """次の未実行質問を取得"""
        for q in self.questions:
            if q.status == QuestionStatus.PENDING:
                return q
        return None


# ============================================================
# リクエスト/レスポンス用の値オブジェクト
# ============================================================


class ReportGenerateWordRequest(BaseModel):
    """Word生成リクエスト"""

    report_id: str = Field(description="レポートID")


# ============================================================
# 質問生成用のモデル
# ============================================================


class GeneratedQuestion(BaseModel):
    """LLMが生成した質問"""

    question: str = Field(description="生成された具体的な質問")
    reasoning: str = Field(description="なぜこの質問を生成したかの理由")
    relevant_columns: list[str] = Field(
        description="この質問に関連するカラム名のリスト", default_factory=list
    )


class ReportQuestionsGenerationResult(BaseModel):
    """レポート用質問生成の結果"""

    questions: list[GeneratedQuestion] = Field(
        description="生成された質問のリスト", default_factory=list
    )


class ReportQuestionsGenerationRequest(BaseModel):
    """レポート用質問生成リクエスト"""

    theme: str = Field(description="レポートのテーマ（ふわっとした方向性）")
    num_questions: int = Field(default=5, description="生成する質問の数", ge=1, le=10)
    data_source: str = Field(default="file", description="データソース種別")
