from fastapi import APIRouter, Depends, HTTPException, status

from core.customize.domain.question_refiner.domain import (
    QuestionRefinementRequest,
    QuestionRefinementResult,
)
from core.customize.infrastructure.analyst_db.data_retriever import (
    RefinerDataInfoMessageFactory,
    get_datasets_names,
)
from core.customize.infrastructure.llm.llm import (
    LLMQuestionGenerationService,
)
from core.customize.usecase.question_refiner.refiner import (
    MessageFactory,
    RefineQuestionUseCase,
    RefineUserPromptBuilder,
)
from utils.analyst_db import AnalystDB
from utils.logging_helper import get_logger
from utils.rest_api import get_initialized_db

logger = get_logger(__name__)

refiner_router = APIRouter(prefix="/refiner", tags=["refiner"])


@refiner_router.post(
    "",
    response_model=QuestionRefinementResult,
    status_code=status.HTTP_200_OK,
)
async def run_evaluation(
    input_data: QuestionRefinementRequest,
    analyst_db: AnalystDB = Depends(get_initialized_db),
) -> QuestionRefinementResult:
    logger.info(f"🚀 Refiner API called with: {input_data}")

    datasets_names = await get_datasets_names(
        data_source=input_data.data_source, analyst_db=analyst_db
    )
    print("Datasets names:", datasets_names)
    data_info_analyst_db = RefinerDataInfoMessageFactory(
        analyst_db, dataset_names=datasets_names
    )
    await data_info_analyst_db.set_data_info()
    logger.info("✓ データ情報の取得完了")

    try:
        prompt_builder = RefineUserPromptBuilder(data_info_analyst_db)
        message_factory = MessageFactory()
        question_generation_service = LLMQuestionGenerationService()
        usecase = RefineQuestionUseCase(
            prompt_builder,
            message_factory,
            question_generation_service,
        )
        logger.info("🔄 Calling usecase.run()...")
        result = await usecase.run(request=input_data)
        logger.info(
            f"✅ Refiner result: success={result.success}, questions={len(result.refined_questions)}"
        )
        return result
    except Exception as e:
        logger.error(f"❌ Refiner failed with exception: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
