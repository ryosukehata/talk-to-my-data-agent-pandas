# Question Refiner 機能 実装ドキュメント

## 概要

Question Refiner機能は、ユーザーが入力した曖昧な質問をAIが自動的に洗練し、データセットに基づいた具体的な分析質問に変換する機能です。

## 機能概要

### ユーザーフロー

1. ユーザーが質問を入力（例：「売上を分析したい」）
2. 「Refine Question」ボタンをクリック
3. APIを呼び出し、洗練された質問を取得
4. 洗練された質問が入力欄に表示される（または自動送信）
5. ユーザーが送信ボタンを押すとチャットに送信

### Feature Flags

| フラグ名 | 環境変数 | デフォルト | 説明 |
|---------|----------|------------|------|
| `refinerEnabled` | `VITE_ENABLE_QUESTION_REFINER` | `false` | Refinerモードボタンの表示/非表示 |
| `refinerAutoSend` | `VITE_ENABLE_REFINER_AUTO_SEND` | `true` | `true`: 洗練後に自動送信 / `false`: 送信ボタンを押す必要あり |

## 変更ファイル一覧

### バックエンド

| ファイル | 変更内容 |
|----------|----------|
| `utils/customize/feature_flag_config.py` | `refinerEnabled`, `refinerAutoSend` フラグ追加 |
| `.env.template` | `VITE_ENABLE_QUESTION_REFINER`, `VITE_ENABLE_REFINER_AUTO_SEND` 追加 |
| `utils/customize/api_endpoints/question_refiner.py` | Refiner APIエンドポイント実装 |
| `utils/customize/api_endpoints/__init__.py` | パッケージ初期化 |
| `utils/customize/rest_api.py` | `refiner_router` を統合 |
| `utils/customize/domain/question_refiner/domain.py` | ドメインモデル定義 |
| `utils/customize/usecase/question_refiner/refiner.py` | ユースケース実装 |
| `utils/customize/infrastructure/analyst_db/data_retriever.py` | データ取得層 |
| `utils/customize/infrastructure/llm/llm.py` | LLMサービス層 |

### フロントエンド（API層）

| ファイル | 変更内容 |
|----------|----------|
| `app_frontend/src/api/feature-flag/types.ts` | `refinerEnabled`, `refinerAutoSend` 型追加 |
| `app_frontend/src/api/refiner/types.ts` | **新規作成** - リクエスト/レスポンス型定義 |
| `app_frontend/src/api/refiner/api.ts` | **新規作成** - API呼び出し関数 |
| `app_frontend/src/api/refiner/hooks.ts` | **新規作成** - `useRefineQuestions` hook |
| `app_frontend/src/api/refiner/index.ts` | **新規作成** - エクスポート |

### フロントエンド（UI層）

| ファイル | 変更内容 |
|----------|----------|
| `app_frontend/src/components/refiner/RefinerButton.tsx` | **新規作成** - Refinerボタンコンポーネント |
| `app_frontend/src/components/refiner/index.ts` | **新規作成** - エクスポート |
| `app_frontend/src/components/chat/InitialPrompt.tsx` | RefinerButton統合 |
| `app_frontend/src/components/chat/UserPrompt.tsx` | RefinerButton統合 |
| `app_frontend/src/components/chat/index.ts` | エクスポート更新 |

### 国際化（i18n）

| ファイル | 変更内容 |
|----------|----------|
| `app_frontend/src/i18n/locales/ja.json` | 日本語翻訳追加 |

## API仕様

### エンドポイント

```
POST /api/v1/refiner
```

### リクエスト

```json
{
  "user_direction": "売上を分析したい",
  "data_source": "file"
}
```

### レスポンス

```json
{
  "success": true,
  "refined_questions": [
    {
      "original_direction": "売上を分析したい",
      "refined_question": "sensor_data.timestamp_iso, sensor_data.line_stop_flagを使って...",
      "reasoning": "ライン停止イベントの発生頻度を分析するためには...",
      "relevant_columns": ["timestamp_iso", "line_stop_flag"]
    }
  ],
  "error": null
}
```

## 送信メッセージ形式

洗練された質問がチャットに送信される際のフォーマット：

```
Question: [洗練された質問]

Reasoning: [なぜこの質問を生成したか]

Relevant Columns: [関連するカラム名のリスト]
```

日本語の場合：

```
質問: [洗練された質問]

理由: [なぜこの質問を生成したか]

関連カラム: [関連するカラム名のリスト]
```

## 使用方法

### 1. 環境変数の設定

`.env`ファイルに以下を追加：

```env
# Refiner機能を有効化
VITE_ENABLE_QUESTION_REFINER=True

# 自動送信を有効化（オプション）
VITE_ENABLE_REFINER_AUTO_SEND=True
```

### 2. アプリケーションの起動

通常通りアプリケーションを起動すると、チャット入力欄の横に「Refine Question」ボタンが表示されます。

## アーキテクチャ

```
┌─────────────────────────────────────────────────────────────┐
│                    Presentation Layer                        │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ RefinerButton.tsx                                       ││
│  │ - Feature flagに基づいて表示/非表示                      ││
│  │ - ユーザー入力をAPIに送信                                ││
│  │ - 結果を入力欄に表示または自動送信                        ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                       API Layer                              │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ useRefineQuestions hook                                 ││
│  │ - React Query mutation                                  ││
│  │ - POST /api/v1/refiner                                  ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Backend (FastAPI)                         │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ question_refiner.py (Endpoint)                          ││
│  │ - リクエスト受付                                         ││
│  │ - ユースケース呼び出し                                    ││
│  └─────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────┐│
│  │ refiner.py (Use Case)                                   ││
│  │ - ビジネスロジック                                       ││
│  │ - プロンプト構築                                         ││
│  │ - LLM呼び出し                                           ││
│  └─────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────┐│
│  │ data_retriever.py (Infrastructure)                      ││
│  │ - AnalystDBからデータ情報取得                            ││
│  └─────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────┐│
│  │ llm.py (Infrastructure)                                 ││
│  │ - LLM API呼び出し                                       ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

## テスト

### E2Eテスト

```bash
python test_question_refiner.py
```

テストモードを切り替えるには、`test_question_refiner.py`内の`test_mode`変数を変更：

```python
test_mode = "e2e"      # REST API経由でテスト
test_mode = "usecase"  # ユースケース層を直接テスト
```
