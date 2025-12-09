"""Question Refiner Module - データ概要から具体的な質問を生成

クリーンアーキテクチャに沿った設計：
- domain: ドメインモデル（エンティティと値オブジェクト）
- repository: データ取得の抽象インターフェース（ポート）
- service_interface: LLM サービスの抽象インターフェース（ポート）
- use_case: ビジネスロジック（アプリケーション層）
- infrastructure: 外部依存の具体実装（アダプター）
- llm_service: LLM サービスの具体実装（アダプター）
- question_refiner: ファサード（簡単に使えるインターフェース）
"""

from utils.customize.domain.question_refiner.domain import (
    QuestionRefinementRequest,
    QuestionRefinementResult,
    RefinedQuestion,
)
from utils.customize.question_refiner.question_refiner import (
    QuestionRefiner,
    refine_user_question,
)

__all__ = [
    # ファサード（推奨）
    "QuestionRefiner",
    "refine_user_question",
    # ドメインモデル
    "RefinedQuestion",
    "QuestionRefinementRequest",
    "QuestionRefinementResult",
]
