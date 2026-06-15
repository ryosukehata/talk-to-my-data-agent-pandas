"""
Question Refiner Module - Facade

クリーンアーキテクチャに沿った質問洗練機能のファサード
各層の責務を分離し、依存関係を明確化
"""

from __future__ import annotations

from core.analyst_db import AnalystDB
from core.customize.domain.question_refiner.domain import (
    QuestionRefinementRequest,
    QuestionRefinementResult,
)
from core.customize.infrastructure.analyst_db.data_retriever import (
    RefinerDataInfoMessageFactory,
)
from core.customize.infrastructure.llm.llm import (
    LLMQuestionGenerationService,
)
from core.customize.usecase.question_refiner.refiner import (
    RefineQuestionUseCase,
)
from core.token_tracking import TokenUsageTracker


class QuestionRefiner:
    """質問を洗練するファサードクラス（後方互換性のため維持）"""

    def __init__(
        self,
        analyst_db: AnalystDB,
        token_tracker: TokenUsageTracker | None = None,
    ):
        """
        Args:
            analyst_db: データセットとメタデータを取得するためのデータベース
            token_tracker: トークン使用量を追跡するためのトラッカー（オプション）
        """
        # インフラストラクチャ層のインスタンス化
        self.data_info_factory = RefinerDataInfoMessageFactory(
            analyst_db, dataset_names=[]
        )
        self.llm_service = LLMQuestionGenerationService(token_tracker=token_tracker)

        # ユースケース層のインスタンス化
        self.refine_use_case = RefineQuestionUseCase(
            datainfo_factory=self.data_info_factory,
            question_generation_service=self.llm_service,
        )

    async def refine_question(
        self,
        user_direction: str,
        dataset_names: list[str],
        num_questions: int = 3,
    ) -> QuestionRefinementResult:
        """ふわっとした質問の方向性から具体的な質問を生成

        Args:
            user_direction: ユーザーの質問の方向性（例: "売上の傾向を知りたい"）
            dataset_names: 対象データセット名のリスト
            num_questions: 生成する質問の数（デフォルト: 3）

        Returns:
            QuestionRefinementResult: 生成された質問のリスト
        """
        request = QuestionRefinementRequest(
            user_direction=user_direction,
            dataset_names=dataset_names,
            num_questions=num_questions,
        )
        return await self.refine_use_case.run(request)


async def refine_user_question(
    analyst_db: AnalystDB,
    user_direction: str,
    dataset_names: list[str],
    num_questions: int = 3,
    token_tracker: TokenUsageTracker | None = None,
) -> QuestionRefinementResult:
    """質問を洗練するヘルパー関数

    Args:
        analyst_db: データベース
        user_direction: ユーザーの質問の方向性
        dataset_names: 対象データセット名のリスト
        num_questions: 生成する質問の数
        token_tracker: トークン追跡用（オプション）

    Returns:
        QuestionRefinementResult: 生成された質問
    """
    refiner = QuestionRefiner(analyst_db=analyst_db, token_tracker=token_tracker)
    return await refiner.refine_question(
        user_direction=user_direction,
        dataset_names=dataset_names,
        num_questions=num_questions,
    )
