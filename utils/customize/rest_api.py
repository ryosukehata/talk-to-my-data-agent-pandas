"""
Custom REST API Endpoints

カスタマイズされたAPIエンドポイントを提供するモジュール。
プロンプトテンプレート管理、CSVバリデーション、データベース設定などの機能を含む。
"""

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from utils.customize.custom_prompts import UserPrompts
from utils.customize.database_helpers import (
    get_schemas_with_descriptions,
    get_tables_with_descriptions,
)
from utils.customize.feature_flag_config import get_feature_flags
from utils.customize.template_manager import get_template_manager
from utils.database_helpers import get_external_database

# カスタマイズ用のルーター
router = APIRouter()


# =============================================================================
# Pydantic Models for Custom Prompts
# =============================================================================


class CustomPromptCreate(BaseModel):
    """カスタムプロンプト作成用のモデル"""

    name: str
    prompt_text_template: str
    description: str | None = None


class CustomPromptResponse(BaseModel):
    """カスタムプロンプトレスポンス用のモデル"""

    name: str
    category: str
    description: str | None
    prompt_text_template: str


class CustomPromptDelete(BaseModel):
    """カスタムプロンプト削除用のモデル"""

    name: str


# =============================================================================
# Helper Functions
# =============================================================================


def get_user_id_from_request(request: Request) -> str:
    """リクエストからuser_idを取得する（ミドルウェアで処理済みの情報を使用）"""
    # メインAPIのミドルウェアで既に処理されたセッション情報を利用
    if hasattr(request.state, "session") and request.state.session:
        # DataRobotアカウント情報からuser_idを取得
        account_info = getattr(request.state.session, "datarobot_account_info", None)
        if account_info and account_info.get("uid"):
            return account_info["uid"]

    # フォールバック: ヘッダーからuser_idを生成
    email_header = request.headers.get("x-user-email")
    if email_header:
        import uuid

        return str(uuid.uuid5(uuid.NAMESPACE_OID, email_header))[:36]

    # デフォルトのuser_id（開発用）
    return "default_user"


# =============================================================================
# Custom Prompts Endpoints
# =============================================================================


@router.post("/custom-prompts")
async def create_custom_prompt(
    request: Request, prompt_data: CustomPromptCreate
) -> dict[str, str]:
    """ユーザーのカスタムプロンプトを作成

    Args:
        request: FastAPIリクエストオブジェクト
        prompt_data: プロンプトデータ

    Returns:
        作成結果のメッセージ

    Raises:
        HTTPException: 作成に失敗した場合
    """
    try:
        user_id = get_user_id_from_request(request)
        user_prompts = UserPrompts(user_id)
        user_prompts.save_prompt(
            name=prompt_data.name,
            prompt=prompt_data.prompt_text_template,
            description=prompt_data.description,
        )

        return {"message": f"Custom prompt '{prompt_data.name}' created successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create custom prompt: {str(e)}"
        )


@router.get("/custom-prompts")
async def get_custom_prompts(request: Request) -> dict[str, list[CustomPromptResponse]]:
    """ユーザーのカスタムプロンプト一覧を取得

    Args:
        request: FastAPIリクエストオブジェクト

    Returns:
        カスタムプロンプトのリスト

    Raises:
        HTTPException: 取得に失敗した場合
    """
    try:
        user_id = get_user_id_from_request(request)
        user_prompts = UserPrompts(user_id)
        prompts = user_prompts.load_prompts()

        return {"custom_prompts": prompts}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get custom prompts: {str(e)}"
        )


@router.get("/custom-prompts/{prompt_name}")
async def get_custom_prompt_by_name(
    request: Request, prompt_name: str
) -> CustomPromptResponse:
    """指定されたカスタムプロンプトを取得

    Args:
        request: FastAPIリクエストオブジェクト
        prompt_name: プロンプト名

    Returns:
        カスタムプロンプト

    Raises:
        HTTPException: プロンプトが見つからない場合
    """
    try:
        user_id = get_user_id_from_request(request)
        user_prompts = UserPrompts(user_id)
        prompt = user_prompts.get_prompt_by_name(prompt_name)
        if not prompt:
            raise HTTPException(
                status_code=404, detail=f"Custom prompt '{prompt_name}' not found"
            )

        return prompt
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get custom prompt: {str(e)}"
        )


@router.delete("/custom-prompts")
async def delete_custom_prompt(
    request: Request, prompt_data: CustomPromptDelete
) -> dict[str, str]:
    """ユーザーのカスタムプロンプトを削除

    Args:
        request: FastAPIリクエストオブジェクト
        prompt_data: 削除するプロンプトデータ

    Returns:
        削除結果のメッセージ

    Raises:
        HTTPException: 削除に失敗した場合またはプロンプトが見つからない場合
    """
    try:
        user_id = get_user_id_from_request(request)
        user_prompts = UserPrompts(user_id)
        success = user_prompts.delete_prompt(prompt_data.name)
        if not success:
            raise HTTPException(
                status_code=404, detail=f"Custom prompt '{prompt_data.name}' not found"
            )

        return {"message": f"Custom prompt '{prompt_data.name}' deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to delete custom prompt: {str(e)}"
        )


@router.get("/custom-prompts-names")
async def get_custom_prompt_names(request: Request) -> dict[str, list[str]]:
    """ユーザーのカスタムプロンプト名一覧を取得

    Args:
        request: FastAPIリクエストオブジェクト

    Returns:
        カスタムプロンプト名のリスト

    Raises:
        HTTPException: 取得に失敗した場合
    """
    try:
        user_id = get_user_id_from_request(request)
        user_prompts = UserPrompts(user_id)
        names = user_prompts.list_prompt_names()

        return {"prompt_names": names}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get custom prompt names: {str(e)}"
        )


# =============================================================================
# Prompt Template Endpoints
# =============================================================================


@router.get("/templates/categories")
async def get_template_categories() -> dict[str, list[str]]:
    """Get all available template categories"""
    manager = get_template_manager()
    return {"categories": manager.get_all_categories()}


@router.get("/templates")
async def get_templates(
    category: str | None = None, search: str | None = None
) -> dict[str, list[dict[str, str]]]:
    """Get templates, optionally filtered by category or search keyword

    Args:
        category: Filter templates by category (営業, 人事, 財務, マーケティング, オペレーション)
        search: Search templates by keyword in name, description, or prompt content

    Returns:
        Dictionary containing list of matching templates
    """
    manager = get_template_manager()

    if search:
        templates = manager.search_templates(search)
    elif category:
        templates = manager.get_templates_by_category(category)
    else:
        templates = manager.get_all_templates()

    return {"templates": templates}


@router.get("/templates/{template_name}")
async def get_template(template_name: str) -> dict[str, dict[str, str]]:
    """Get a specific template by name

    Args:
        template_name: Name of the template to retrieve

    Returns:
        Dictionary containing the template data

    Raises:
        HTTPException: 404 if template not found
    """
    manager = get_template_manager()
    template = manager.get_template_by_name(template_name)

    if not template:
        raise HTTPException(
            status_code=404, detail=f"Template '{template_name}' not found"
        )

    return {"template": template}


@router.get("/templates/stats/summary")
async def get_template_summary() -> dict[str, Any]:
    """Get template statistics and summary information"""
    manager = get_template_manager()

    return {
        "total_templates": manager.get_template_count(),
        "categories": manager.get_all_categories(),
        "category_counts": manager.get_category_summary(),
    }


@router.post("/templates/reload")
async def reload_templates() -> dict[str, str]:
    """Reload templates from data source

    Force reload templates from the CSV file or data registry.
    This will refresh the template cache with the latest data.

    Returns:
        Success message with reload status

    Raises:
        HTTPException: If reload fails
    """
    try:
        manager = get_template_manager()
        manager._load()

        return {
            "message": "Templates reloaded successfully",
            "total_templates": str(manager.get_template_count()),
            "categories": str(len(manager.get_all_categories())),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to reload templates: {str(e)}"
        )


# =============================================================================
# Database Configuration Endpoints
# =============================================================================


@router.get("/database/tables")
async def get_database_tables(schema: str | None = None) -> dict[str, str]:
    """Get list of available tables with descriptions"""
    return get_tables_with_descriptions(schema=schema)


@router.get("/database/schemas")
async def get_database_schemas() -> dict[str, str]:
    """Get list of available schemas with descriptions"""
    return get_schemas_with_descriptions()


@router.get("/database/default-schema")
async def get_default_schema() -> str:
    """Get the default schema name from environment configuration"""
    db_operator = get_external_database()
    credentials = getattr(db_operator, "_credentials", None)
    return getattr(credentials, "db_schema", "") if credentials else ""


# =============================================================================
# Configuration / Feature Flags Endpoints
# =============================================================================


@router.get("/config/feature-flags")
async def get_feature_flags_endpoint() -> dict[str, Any]:
    """
    Get feature flags configuration from environment variables

    Returns:
        Dictionary containing feature flag values
    """
    try:
        return get_feature_flags()
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get feature flags: {str(e)}"
        )


# =============================================================================
# CSV Validation Endpoints (Future)
# =============================================================================

# 将来的にCSVバリデーション関連のAPIをここに追加予定
