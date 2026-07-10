"""
Question Refiner の動作確認スクリプト
"""

import asyncio
import io
import os

# OpenTelemetryのエクスポートを無効化（テスト用）
os.environ["OTEL_SDK_DISABLED"] = "true"

import pytest

if os.environ.get("RUN_CUSTOMIZE_DOCS_E2E") != "1":
    pytest.skip(
        "DataRobot/LLM E2E smoke script. Set RUN_CUSTOMIZE_DOCS_E2E=1 to run.",
        allow_module_level=True,
    )

import pandas as pd
from core.analyst_db import AnalystDB, InternalDataSourceType
from core.api import get_dictionary
from core.customize import prompts
from core.customize.domain.question_refiner.domain import (
    QuestionRefinementRequest,
)
from core.customize.infrastructure.analyst_db.data_retriever import (
    RefinerDataInfoMessageFactory,
)
from core.customize.infrastructure.llm.llm import (
    LLMQuestionGenerationService,
)
from core.customize.usecase.question_refiner.refiner import (
    MessageFactory,
    RefineQuestionUseCase,
    RefineUserPromptBuilder,
)
from core.rest_api import app
from core.schema import AnalystDataset
from fastapi.testclient import TestClient


async def create_test_dataset() -> AnalystDataset:
    """テスト用のダミーデータセットを作成

    Returns:
        (データセット名, CSVファイルパス) のタプル
    """
    # テスト用の売上データを作成
    data = {
        "date": pd.date_range("2024-01-01", periods=100, freq="D"),
        "product": ["商品A", "商品B", "商品C"] * 33 + ["商品A"],
        "amount": [1000 + i * 10 for i in range(100)],
        "quantity": [10 + i % 5 for i in range(100)],
        "region": ["東京", "大阪", "名古屋", "福岡"] * 25,
    }
    df = pd.DataFrame(data)
    print(f"  - 行数: {len(df)}")
    print(f"  - カラム数: {len(df.columns)}")
    print(f"  - カラム: {', '.join(df.columns)}")

    dataset = AnalystDataset(name="test_sales_data", data=df)
    # analysis_data = await cleanse_dataframe(dataset)
    return dataset


async def load_sensor_data() -> AnalystDataset:
    """センサーデータセットを読み込む

    Returns:
        (データセット名, CSVファイルパス) のタプル
    """
    # センサーデータをCSVから読み込み
    csv_path = "assets/sensor_logs_linewide_L_handon.csv"
    df = pd.read_csv(csv_path)

    dataset = AnalystDataset(name="sensor_data", data=df)
    return dataset


async def set_analystDB(dataset: AnalystDataset) -> AnalystDB:
    dictionary = await get_dictionary(dataset)

    analyst_db = await AnalystDB.create(
        "user_123",
        ".",
        "chats",
        "datasets",
    )
    await analyst_db.register_dataset(
        dataset, data_source=InternalDataSourceType.GENERATED
    )
    await analyst_db.register_data_dictionary(dictionary)

    return analyst_db


async def main(user_direction: str = "売上の傾向を知りたい"):
    """動作確認のメイン関数"""
    # AnalystDB のインスタンスを作成

    # 1. テストデータセットを作成してアップロード
    print("=== ステップ1: テストデータの準備 ===")
    analyst_dataset = await load_sensor_data()  # create_test_dataset()

    analyst_db = await set_analystDB(analyst_dataset)
    # print(analyst_dataset.name)
    print(await analyst_db.get_dataset_metadata(analyst_dataset.name))
    print(await analyst_db.get_data_dictionary(analyst_dataset.name))
    print("✓ テストデータセット登録完了")

    data_info_analyst_db = RefinerDataInfoMessageFactory(
        analyst_db, [analyst_dataset.name]
    )
    await data_info_analyst_db.set_data_info()
    print("✓ データ情報の取得完了")
    print("\n=== ステップ1.5: データ情報の確認 ===")

    print(data_info_analyst_db.shape_info)
    print(data_info_analyst_db.sample_data)
    print(data_info_analyst_db.dictionary_data)

    print("\n===データ情報の確認完了 ===")
    print("\n=== messagesへの変換確認 ===")
    print(await data_info_analyst_db.create_message())
    print("=== messagesへの変換確認完了 ===")

    print("\n=== ステップ2: user promptの確認 ===")

    user_prompt = RefineUserPromptBuilder(data_info_analyst_db)
    user_prompt = await user_prompt.build(
        QuestionRefinementRequest(user_direction=user_direction)
    )
    print(user_prompt)

    print("\n=== ステップ2: user promptの変換の確認 ===")

    print("\n=== ステップ3: prompt  builderの動作確認 ===")
    messages = MessageFactory.create_message(
        system_prompt=prompts.QUESTION_REFINER_SYSTEM_PROMPT,
        user_prompt=user_prompt,
    )
    print(messages)
    print("=== ステップ3: prompt  builderの動作確認完了 ===")

    print("\n=== ステップ4: 質問洗練の動作確認 ===")
    question_generation_service = LLMQuestionGenerationService()
    refined_questions = await question_generation_service.get(messages)

    print(refined_questions)
    print("=== ステップ4: 質問洗練の動作確認完了 ===")

    print("\n✓ 全ステップ完了")
    print(f"{user_direction}で実行した結果")
    print(f"生成された質問数: {refined_questions.refined_question}")


async def use_usecase(user_direction: str = "売上の傾向を知りたい"):
    # 1. テストデータセットを作成してアップロード
    print("=== ステップ1: テストデータの準備 ===")
    analyst_dataset = await load_sensor_data()  # create_test_dataset()

    analyst_db = await set_analystDB(analyst_dataset)
    print(await analyst_db.get_dataset_metadata(analyst_dataset.name))
    print(await analyst_db.get_data_dictionary(analyst_dataset.name))
    print("✓ テストデータセット登録完了")

    data_info_analyst_db = RefinerDataInfoMessageFactory(
        analyst_db, [analyst_dataset.name]
    )
    await data_info_analyst_db.set_data_info()
    print("✓ データ情報の取得完了")

    prompt_builder = RefineUserPromptBuilder(data_info_analyst_db)
    message_factory = MessageFactory()
    question_generation_service = LLMQuestionGenerationService()
    usecase = RefineQuestionUseCase(
        prompt_builder,
        message_factory,
        question_generation_service,
    )
    result = await usecase.run(
        request=QuestionRefinementRequest(user_direction=user_direction)
    )
    print(result)


def test_rest_api_e2e(user_direction: str = "売上の傾向を知りたい"):
    """E2E方式でREST APIをテスト

    1. まずデータセットをアップロードAPIで登録
    2. その後、Question Refiner APIを呼び出し
    """
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

    # ステップ2: Question Refiner APIを呼び出し
    print("\n--- ステップ2: Question Refiner APIの呼び出し ---")

    refiner_payload = {
        "user_direction": user_direction,
        "data_source": "file",  # InternalDataSourceType.FILEの値は"file"
        "num_questions": 5,
    }

    refiner_response = client.post(
        "/api/v1/refiner",
        json=refiner_payload,
        headers=headers,
    )

    print(f"Refinerステータス: {refiner_response.status_code}")
    print(f"レスポンス: {refiner_response.json()}")

    if refiner_response.status_code == 200:
        print("✓ Question Refiner API呼び出し成功")
        result = refiner_response.json()
        if result.get("success"):
            questions = result.get("refined_questions", [])
            print(f"\n生成された質問 ({len(questions)}件):")
            for i, q in enumerate(questions, 1):
                print(f"  {i}. {q}")
    else:
        print("❌ Question Refiner APIの呼び出しに失敗しました")

    print("\n=== E2E REST APIテスト完了 ===")


if __name__ == "__main__":
    # テストモードを選択
    # "usecase": ユースケース層を直接テスト
    # "e2e": REST API経由でE2Eテスト
    test_mode = "usecase"  # "usecase" or "e2e"

    for user_direction in [
        #        "売上の傾向を知りたい",
        #        "地域ごとの販売パフォーマンスを分析したい",
        #        "商品別の売上比較をしたい",
        "ライン停止イベントの発生頻度を分析したいです",
        "ライン停止イベントの発生頻度を分析したいです、いつどこで起きたか知りたいです",
        "センサー異常と停止の関連性特定",
    ]:
        print(f"\n\n##### ユーザーの方向性: {user_direction} #####\n")

        if test_mode == "usecase":
            # ユースケース層を直接テスト
            asyncio.run(use_usecase(user_direction=user_direction))
        elif test_mode == "e2e":
            # REST API経由でE2Eテスト
            test_rest_api_e2e(user_direction=user_direction)
