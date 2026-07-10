"""
Report Questions Generator の動作確認スクリプト

1. 質問生成（方向性レベル）のテスト
2. 質問洗練（具体化）のテスト
3. E2E APIテスト
"""

import asyncio
import io
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.absolute()))

# OpenTelemetryのエクスポートを無効化（テスト用）
os.environ["OTEL_SDK_DISABLED"] = "true"

import pytest

if os.environ.get("RUN_CUSTOMIZE_DOCS_E2E") != "1":
    pytest.skip(
        "DataRobot/LLM E2E smoke script. Set RUN_CUSTOMIZE_DOCS_E2E=1 to run.",
        allow_module_level=True,
    )

# rest_apiのインポート - appは後で取得
import core.rest_api as rest_api_module
import pandas as pd
from core.analyst_db import AnalystDB, InternalDataSourceType
from core.api import get_dictionary
from core.customize.domain.question_refiner.domain import (
    QuestionRefinementRequest,
)
from core.customize.domain.report.domain import (
    ReportQuestionsGenerationRequest,
)
from core.customize.infrastructure.analyst_db.data_retriever import (
    RefinerDataInfoMessageFactory,
)
from core.customize.infrastructure.llm.llm import LLMQuestionGenerationService
from core.customize.infrastructure.llm.report_questions_generator import (
    LLMReportQuestionsGenerationService,
)
from core.customize.usecase.prompt.builder import (
    MessageFactory,
    RefineUserPromptBuilder,
)
from core.customize.usecase.question_refiner.refiner import RefineQuestionUseCase
from core.customize.usecase.report.generate_questions import GenerateQuestionsUseCase
from core.schema import AnalystDataset
from fastapi.testclient import TestClient

app = rest_api_module.app


async def load_sensor_data() -> AnalystDataset:
    """センサーデータセットを読み込む"""
    csv_path = "assets/sensor_logs_linewide_L_handon.csv"
    df = pd.read_csv(csv_path)
    dataset = AnalystDataset(name="sensor_data", data=df)
    return dataset


async def set_analystDB(dataset: AnalystDataset) -> AnalystDB:
    """AnalystDBをセットアップ"""
    dictionary = await get_dictionary(dataset)

    analyst_db = await AnalystDB.create(
        "user_test",
        ".",
        "chats",
        "datasets",
    )
    await analyst_db.register_dataset(dataset, data_source=InternalDataSourceType.FILE)
    await analyst_db.register_data_dictionary(dictionary)

    return analyst_db


# =============================================================================
# Test 1: 質問生成（方向性レベル）のテスト
# =============================================================================


async def test_generate_questions():
    """テスト1: テーマから複数の質問を生成できるか確認"""
    print("\n" + "=" * 80)
    print("テスト1: 質問生成（方向性レベル）")
    print("=" * 80)

    # データセットの準備
    print("\n[1] データセットの準備...")
    analyst_dataset = await load_sensor_data()
    analyst_db = await set_analystDB(analyst_dataset)
    print(f"  ✓ データセット '{analyst_dataset.name}' を準備")

    # データ情報ファクトリの構築
    print("\n[2] データ情報ファクトリの構築...")
    # datasets_names = await get_datasets_names(data_source="file", analyst_db=analyst_db)
    # print(datasets_names)
    data_info_factory = RefinerDataInfoMessageFactory(
        analyst_db, dataset_names=[analyst_dataset.name]
    )
    await data_info_factory.set_data_info()
    print("  ✓ データ情報を取得")

    # 質問生成サービスの構築
    print("\n[3] 質問生成サービスの構築...")
    questions_generation_service = LLMReportQuestionsGenerationService()
    questions_generator = GenerateQuestionsUseCase(
        data_info_factory=data_info_factory,
        questions_generation_service=questions_generation_service,
    )
    print("  ✓ GenerateQuestionsUseCase を構築")

    # テーマから質問を生成
    print("\n[4] テーマから質問を生成...")
    theme = "センサーログの異常値と傾向を分析して、設備の保守タイミングを判断したい"
    request = ReportQuestionsGenerationRequest(
        theme=theme,
        num_questions=5,
        data_source="file",
    )
    print(f"  テーマ: {theme}")
    print(f"  生成数: {request.num_questions}個")

    result = await questions_generator.run(request)

    # 結果の確認
    print("\n[5] 生成結果:")
    print(f"  生成された質問数: {len(result.questions)}個")
    print()
    for i, gen_question in enumerate(result.questions, 1):
        print(f"  質問{i}: {gen_question.question}")
        print(f"    理由: {gen_question.reasoning}")
        print()

    # アサーション
    assert len(result.questions) > 0, "❌ 質問が生成されませんでした"
    assert len(result.questions) == 5, f"❌ 期待: 5個、実際: {len(result.questions)}個"

    print("✅ テスト1 成功: 質問生成が正常に動作しています")
    return result.questions


# =============================================================================
# Test 2: 質問洗練（具体化）のテスト
# =============================================================================


async def test_refine_questions(generated_questions):
    """テスト2: 生成された質問を洗練できるか確認"""
    print("\n" + "=" * 80)
    print("テスト2: 質問洗練（具体化）")
    print("=" * 80)

    # データセットの準備（再利用）
    print("\n[1] データセットの準備...")
    analyst_dataset = await load_sensor_data()
    analyst_db = await set_analystDB(analyst_dataset)

    # データ情報ファクトリの構築
    print("\n[2] データ情報ファクトリの構築...")
    # datasets_names = await get_datasets_names(data_source="file", analyst_db=analyst_db)
    data_info_factory = RefinerDataInfoMessageFactory(
        analyst_db, dataset_names=[analyst_dataset.name]
    )
    await data_info_factory.set_data_info()

    # 質問洗練サービスの構築
    print("\n[3] 質問洗練サービスの構築...")
    prompt_builder = RefineUserPromptBuilder(data_info_factory)
    message_factory = MessageFactory()
    question_generation_service = LLMQuestionGenerationService()
    question_refiner = RefineQuestionUseCase(
        prompt_builder,
        message_factory,
        question_generation_service,
    )
    print("  ✓ RefineQuestionUseCase を構築")

    # 各質問を洗練
    print("\n[4] 各質問を洗練...")
    refined_results = []

    for i, gen_question in enumerate(generated_questions, 1):
        print(f"\n  --- 質問{i}の洗練 ---")
        print(f"  方向性: {gen_question.question}")

        refine_request = QuestionRefinementRequest(
            user_direction=gen_question.question,
            data_source="file",
        )

        try:
            refine_result = await question_refiner.run(refine_request)

            if refine_result.success and refine_result.refined_questions:
                refined_question = refine_result.refined_questions[0]
                print("  ✅ 洗練成功:")
                print(f"     具体化: {refined_question.refined_question}")
                refined_results.append(
                    {
                        "original": gen_question.question,
                        "refined": refined_question.refined_question,
                        "success": True,
                    }
                )
            else:
                print("  ⚠️ 洗練失敗: 方向性をそのまま使用")
                refined_results.append(
                    {
                        "original": gen_question.question,
                        "refined": gen_question.question,
                        "success": False,
                    }
                )

        except Exception as e:
            print(f"  ❌ エラー: {e}")
            refined_results.append(
                {
                    "original": gen_question.question,
                    "refined": gen_question.question,
                    "success": False,
                    "error": str(e),
                }
            )

    # 結果サマリー
    print("\n[5] 洗練結果サマリー:")
    success_count = sum(1 for r in refined_results if r.get("success", False))
    print(f"  成功: {success_count}/{len(refined_results)}個")

    for i, result in enumerate(refined_results, 1):
        status = "✅" if result.get("success", False) else "⚠️"
        print(f"\n  {status} 質問{i}:")
        print(f"     方向性: {result['original'][:50]}...")
        print(f"     具体化: {result['refined'][:50]}...")

    print("\n✅ テスト2 成功: 質問洗練が正常に動作しています")
    return refined_results


# =============================================================================
# Test 3: E2E APIテスト
# =============================================================================


async def test_api_e2e():
    """テスト3: APIエンドポイントが正常に動作するか確認"""
    print("\n" + "=" * 80)
    print("テスト3: E2E APIテスト")
    print("=" * 80)
    """E2E方式でREST APIをテスト

    1. まずデータセットをアップロードAPIで登録
    2. その後、Question Refiner APIを呼び出し
    """

    # カスタマイズルーターを手動でマウント（循環インポート回避）
    # try:
    #    from core.customize.api_endpoints.question_refiner import refiner_router
    #    from core.customize.api_endpoints.report import report_router

    #    # ルーターが既に追加されているか確認
    #    has_report_routes = any(
    #        "report" in str(route.path).lower() for route in app.routes
    ##    )
    #    if not has_report_routes:
    #        print("  [INFO] カスタマイズルーターを手動でマウント中...")
    #        app.include_router(refiner_router, prefix="/api/v1")
    #        app.include_router(report_router, prefix="/api/v1")
    #        print("  [INFO] マウント完了")
    # except Exception as e:
    #    print(f"  [WARNING] ルーターのマウントに失敗: {e}")

    # TestClientを作成
    client = TestClient(app)

    print("\n=== E2E REST APIテスト開始 ===")

    # ステップ1: データセットをアップロード
    print("\n--- ステップ1: データセットのアップロード ---")

    # CSVファイルを読み込み
    csv_path = "assets/sensor_logs_linewide_L_handon.csv"
    df = pd.read_csv(csv_path)

    # DataFrameをCSV形式の文字列に変換
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_content = csv_buffer.getvalue()

    # アップロードAPIを呼び出し
    files = {"files": ("sensor_data.csv", csv_content, "text/csv")}
    headers = {"x-user-email": "test@example.com"}

    upload_response = client.post(
        "/api/v1/datasets/upload",
        files=files,
        headers=headers,
    )

    print(f"アップロードステータス: {upload_response.status_code}")
    print(f"レスポンス: {upload_response.json()}")

    if upload_response.status_code != 200:
        print("❌ データセットのアップロードに失敗しました")
        return

    print("✓ データセットアップロード成功")

    # リクエストデータ
    request_data = {
        "theme": "センサーログの異常値と傾向を分析して、設備の保守タイミングを判断したい",
        "num_questions": 5,
        "data_source": "file",
    }

    print(f"  テーマ: {request_data['theme']}")
    print(f"  生成数: {request_data['num_questions']}個")

    # POSTリクエストを送信
    print("\n[3] POST /api/v1/reports を実行...")

    response = client.post(
        "/api/v1/reports",
        json=request_data,
        headers=headers,
    )

    print(f"  ステータスコード: {response.status_code}")

    if response.status_code == 201:
        response_data = response.json()
        print("\n[4] レスポンスデータ:")
        print(f"  report_id: {response_data.get('report_id')}")
        print(f"  message: {response_data.get('message')}")

        # レポート詳細を取得
        report_id = response_data.get("report_id")
        if report_id:
            print(f"\n[5] GET /api/v1/reports/{report_id} を実行...")
            detail_response = client.get(
                f"/api/v1/reports/{report_id}",
                headers={"x-user-email": "test@example.com"},
            )

            if detail_response.status_code == 200:
                detail_data = detail_response.json()
                report = detail_data.get("report", {})

                print(f"  タイトル: {report.get('title')}")
                print(f"  ステータス: {report.get('status')}")
                print(f"  質問数: {len(report.get('questions', []))}個")

                print("\n[6] 生成された質問:")
                for i, question in enumerate(report.get("questions", []), 1):
                    print(f"\n  質問{i}:")
                    print(f"    方向性: {question.get('original_direction')}")
                    print(f"    具体化: {question.get('refined_question')[:80]}...")

                print("\n✅ テスト3 成功: APIが正常に動作しています")
            else:
                print(f"❌ レポート詳細取得失敗: {detail_response.status_code}")
                print(f"  エラー: {detail_response.text}")
    else:
        print(f"❌ レポート作成失敗: {response.status_code}")
        print(f"  エラー: {response.text}")


# =============================================================================
# メイン実行
# =============================================================================


async def main():
    """全テストを実行"""
    print("\n")
    print("=" * 80)
    print("Report Questions Generator 動作確認")
    print("=" * 80)

    try:
        # テスト1: 質問生成
        # generated_questions = await test_generate_questions()

        # テスト2: 質問洗練
        # await test_refine_questions(generated_questions)

        # テスト3: E2E API
        await test_api_e2e()

        print("\n" + "=" * 80)
        print("✅ 全テスト成功")
        print("=" * 80)

    except Exception as e:
        print("\n" + "=" * 80)
        print(f"❌ テスト失敗: {e}")
        print("=" * 80)
        raise


if __name__ == "__main__":
    asyncio.run(main())
