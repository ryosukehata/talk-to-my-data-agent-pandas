"""
Report Builder - API Layer

レポート作成のFastAPIエンドポイント
"""

from __future__ import annotations

import tempfile

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from starlette.requests import Request

from core.analyst_db import AnalystDB
from core.customize.domain.report.domain import (
    QuestionStatus,
    Report,
    ReportQuestionsGenerationRequest,
    ReportStatus,
)
from core.customize.infrastructure.analyst_db.data_retriever import (
    RefinerDataInfoMessageFactory,
    get_datasets_names,
)
from core.customize.infrastructure.analyst_db.section_data_retriever import (
    AnalystDBSectionDataRetriever,
)
from core.customize.infrastructure.chat.chat_executor import ChatExecutor
from core.customize.infrastructure.llm.report_questions_generator import (
    LLMReportQuestionsGenerationService,
)
from core.customize.infrastructure.llm.report_summary_generator import (
    LLMReportSummaryService,
)
from core.customize.infrastructure.storage.report_storage import ReportStorage
from core.customize.infrastructure.word.word_generator import WordGenerator
from core.customize.usecase.prompt.builder import SummaryPromptBuilder
from core.customize.usecase.report import (
    DeleteReportUseCase,
    ExecuteQuestionsUseCase,
    GenerateWordUseCase,
    GetReportUseCase,
    InitReportUseCase,
    ListReportsUseCase,
)
from core.customize.usecase.report.generate_questions import GenerateQuestionsUseCase
from core.logging_helper import get_logger
from core.rest_api import get_initialized_db

logger = get_logger("ReportRouter")

report_router = APIRouter(prefix="/reports", tags=["reports"])


# ==============================================================================
# レスポンスモデル
# ==============================================================================


class ReportSummary(BaseModel):
    """レポート概要（一覧用）"""

    report_id: str
    title: str
    status: ReportStatus
    progress: float
    created_at: str
    updated_at: str
    word_file_path: str | None = None
    summary: str | None = None
    conclusion: str | None = None


class ReportListResponse(BaseModel):
    """レポート一覧レスポンス"""

    reports: list[ReportSummary]
    total: int


class ReportDetailResponse(BaseModel):
    """レポート詳細レスポンス"""

    report: Report


class ReportCreateResponse(BaseModel):
    """レポート作成レスポンス"""

    report_id: str
    message: str


class ReportExecuteResponse(BaseModel):
    """質問実行レスポンス"""

    report_id: str
    status: ReportStatus
    message: str


class ReportWordResponse(BaseModel):
    """Word生成レスポンス"""

    report_id: str
    status: ReportStatus
    word_file_path: str | None
    message: str


class DeleteResponse(BaseModel):
    """削除レスポンス"""

    success: bool
    message: str


# ==============================================================================
# ヘルパー関数
# ==============================================================================


def get_user_id(request: Request) -> str:
    """リクエストからユーザーIDを取得"""
    user_id = request.headers.get("x-user-id")
    if user_id:
        return user_id

    session = getattr(request.state, "session", None)
    account_info = getattr(session, "datarobot_account_info", None)
    if isinstance(account_info, dict):
        uid = account_info.get("uid")
        if isinstance(uid, str) and uid:
            return uid
        email = account_info.get("email")
        if isinstance(email, str) and email:
            return email

    user_id = request.headers.get("x-user-email")
    if user_id:
        return user_id

    return "anonymous"


def get_repository(request: Request) -> ReportStorage:
    """レポートリポジトリを取得"""
    user_id = get_user_id(request)
    return ReportStorage(user_id)


def report_to_summary(report: Report) -> ReportSummary:
    """ReportをReportSummaryに変換"""

    total_questions = len(report.questions)
    if total_questions > 0:
        refined_count = sum(
            1
            for q in report.questions
            if q.refined_question and q.refined_question != q.original_direction
        )
        executed_count = sum(
            1 for q in report.questions if q.status == QuestionStatus.COMPLETED
        )
        progress_value = 0.5 * (refined_count / total_questions) + 0.5 * (
            executed_count / total_questions
        )
    else:
        progress_value = 0.0

    return ReportSummary(
        report_id=report.report_id,
        title=report.title,
        status=report.status,
        progress=progress_value,
        created_at=report.created_at.isoformat(),
        updated_at=report.updated_at.isoformat(),
        word_file_path=report.word_file_path,
        summary=report.summary,
        conclusion=report.conclusion,
    )


# ==============================================================================
# エンドポイント
# ==============================================================================


@report_router.get(
    "",
    response_model=ReportListResponse,
    status_code=status.HTTP_200_OK,
    summary="レポート一覧を取得",
)
async def list_reports(
    request: Request,
    analyst_db: AnalystDB = Depends(get_initialized_db),
) -> ReportListResponse:
    user_id = get_user_id(request)
    repository = get_repository(request)

    usecase = ListReportsUseCase(repository)
    reports = await usecase.run(user_id)

    return ReportListResponse(
        reports=[report_to_summary(r) for r in reports],
        total=len(reports),
    )


@report_router.get(
    "/{report_id}",
    response_model=ReportDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="レポート詳細を取得",
)
async def get_report(
    report_id: str,
    request: Request,
    analyst_db: AnalystDB = Depends(get_initialized_db),
) -> ReportDetailResponse:
    repository = get_repository(request)

    usecase = GetReportUseCase(repository)
    report = await usecase.run(report_id)

    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report not found: {report_id}",
        )

    return ReportDetailResponse(report=report)


class UpdateQuestionRequest(BaseModel):
    """質問更新リクエスト"""

    refined_question: str | None = None
    status: QuestionStatus | None = None
    error_message: str | None = None


class UpdateQuestionResponse(BaseModel):
    """質問更新レスポンス"""

    success: bool
    question_id: str
    message: str


@report_router.patch(
    "/{report_id}/questions/{question_id}",
    response_model=UpdateQuestionResponse,
    status_code=status.HTTP_200_OK,
    summary="質問を更新",
)
async def update_question(
    report_id: str,
    question_id: str,
    update_request: UpdateQuestionRequest,
    request: Request,
    analyst_db: AnalystDB = Depends(get_initialized_db),
) -> UpdateQuestionResponse:
    """質問のrefined_questionを更新（洗練結果を保存）"""
    repository = get_repository(request)

    # レポート取得
    report = await repository.get(report_id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report not found: {report_id}",
        )

    # 質問を探して更新
    question_found = False
    for question in report.questions:
        if question.question_id == question_id:
            if update_request.refined_question is not None:
                question.refined_question = update_request.refined_question
                if update_request.status is None:
                    question.status = QuestionStatus.READY
            if update_request.status is not None:
                question.status = update_request.status
            if "error_message" in update_request.model_fields_set:
                question.error_message = update_request.error_message
            question_found = True
            break

    if not question_found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Question not found: {question_id}",
        )

    # 保存
    await repository.save(report)

    return UpdateQuestionResponse(
        success=True,
        question_id=question_id,
        message="Question updated successfully",
    )


@report_router.post(
    "",
    response_model=ReportCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="新しいレポートを作成",
)
async def create_report(
    create_request: ReportQuestionsGenerationRequest,
    request: Request,
    analyst_db: AnalystDB = Depends(get_initialized_db),
) -> ReportCreateResponse:
    """新しいレポートを作成（テーマから方向性レベルの質問を生成）

    このエンドポイントは方向性レベルの質問のみを生成します。
    質問の洗練は別途 POST /refiner を呼び出してください。
    """
    user_id = get_user_id(request)
    repository = get_repository(request)

    try:
        # データセット情報を取得
        datasets_names = await get_datasets_names(
            data_source=create_request.data_source, analyst_db=analyst_db
        )
        data_info_factory = RefinerDataInfoMessageFactory(
            analyst_db, dataset_names=datasets_names
        )
        await data_info_factory.set_data_info()

        # 質問生成サービスを構築
        questions_generation_service = LLMReportQuestionsGenerationService()
        questions_generator = GenerateQuestionsUseCase(
            data_info_factory=data_info_factory,
            questions_generation_service=questions_generation_service,
        )

        # レポート初期化（方向性レベルの質問を生成）
        usecase = InitReportUseCase(
            repository=repository,
            questions_generator=questions_generator,
        )
        report = await usecase.run(
            request=create_request,
            user_id=user_id,
        )

        return ReportCreateResponse(
            report_id=report.report_id,
            message=f"Report created with {len(report.questions)} direction-level questions. Please use /refiner to refine each question.",
        )
    except TimeoutError as e:
        logger.exception("Timed out while creating report")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(e),
        )
    except Exception as e:
        logger.exception("Failed to create report")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@report_router.post(
    "/{report_id}/execute",
    response_model=ReportExecuteResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="レポートの質問を実行",
)
async def execute_questions(
    report_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    analyst_db: AnalystDB = Depends(get_initialized_db),
) -> ReportExecuteResponse:
    """レポートの質問を実行（バックグラウンド）"""
    repository = get_repository(request)
    chat_executor = ChatExecutor()
    user_id = get_user_id(request)

    # レポートの存在確認
    report = await repository.get(report_id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report not found: {report_id}",
        )

    # バックグラウンドで実行
    async def execute_in_background() -> None:
        usecase = ExecuteQuestionsUseCase(repository, chat_executor)
        updated_report = await usecase.run(report_id, analyst_db, request)

        if updated_report.is_all_questions_completed():
            logger.info(
                "Auto-generating Word document for report %s after question execution",
                report_id,
            )
            await _run_word_generation(
                report_id=report_id,
                repository=repository,
                analyst_db=analyst_db,
                author=user_id,
            )

    background_tasks.add_task(execute_in_background)

    return ReportExecuteResponse(
        report_id=report_id,
        status=ReportStatus.CHAT_PROCESSING,
        message="Questions execution started in background",
    )


@report_router.post(
    "/{report_id}/generate-word",
    response_model=ReportWordResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Word文書を生成",
)
async def generate_word(
    report_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    analyst_db: AnalystDB = Depends(get_initialized_db),
) -> ReportWordResponse:
    """レポートのWord文書を生成"""
    user_id = get_user_id(request)
    repository = get_repository(request)
    report = await repository.get(report_id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report not found: {report_id}",
        )

    # 全質問が完了しているか確認
    if not report.is_all_questions_completed():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Not all questions are completed. Execute questions first.",
        )

    async def generate_in_background() -> None:
        await _run_word_generation(
            report_id=report_id,
            repository=repository,
            analyst_db=analyst_db,
            author=user_id,
        )

    background_tasks.add_task(generate_in_background)

    return ReportWordResponse(
        report_id=report_id,
        status=ReportStatus.GENERATING_WORD,
        word_file_path=None,
        message="Word generation started in background",
    )


async def _run_word_generation(
    *,
    report_id: str,
    repository: ReportStorage,
    analyst_db: AnalystDB,
    author: str | None,
) -> None:
    word_generator = WordGenerator()
    section_data_retriever = AnalystDBSectionDataRetriever(analyst_db)
    summary_service = LLMReportSummaryService()
    summary_prompt_builder = SummaryPromptBuilder(
        section_data_factory=section_data_retriever
    )

    usecase = GenerateWordUseCase(
        repository=repository,
        word_generator=word_generator,
        section_data_retriever=section_data_retriever,
        summary_service=summary_service,
        summary_prompt_builder=summary_prompt_builder,
    )

    try:
        await usecase.run(report_id, author=author)
    finally:
        section_data_retriever.cleanup_generated_charts()


@report_router.get(
    "/{report_id}/download",
    summary="Word文書をダウンロード",
)
async def download_word(
    report_id: str,
    request: Request,
    analyst_db: AnalystDB = Depends(get_initialized_db),
) -> FileResponse:
    repository = get_repository(request)

    report = await repository.get(report_id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report not found: {report_id}",
        )

    if report.status != ReportStatus.DONE or not report.word_file_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Word document is not ready. Generate it first.",
        )

    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp_file:
        local_path = tmp_file.name

    success = await repository.get_word_file(report_id, local_path)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve Word document",
        )

    return FileResponse(
        local_path,
        filename=f"report_{report_id}.docx",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@report_router.delete(
    "/{report_id}",
    response_model=DeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="レポートを削除",
)
async def delete_report(
    report_id: str,
    request: Request,
    analyst_db: AnalystDB = Depends(get_initialized_db),
) -> DeleteResponse:
    """レポートを削除"""
    repository = get_repository(request)

    usecase = DeleteReportUseCase(repository)
    success = await usecase.run(report_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete report: {report_id}",
        )

    return DeleteResponse(
        success=True,
        message=f"Report {report_id} deleted successfully",
    )
