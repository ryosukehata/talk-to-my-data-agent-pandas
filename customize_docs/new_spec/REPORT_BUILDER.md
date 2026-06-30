# レポートビルダー機能 仕様書

## 概要

ユーザーがデータをアップロードし、「こんなレポートが欲しい」と要望を入力するだけで、AIが自動的に質問を生成・実行し、Word形式のレポートを作成する機能。

---

## 1. 機能概要

### 1.1 ユーザーフロー

```
1. ユーザーがデータをアップロード（既存機能）
2. サイドバーから「レポート作成」画面にアクセス
3. 「どんなレポートが欲しいですか？」にテーマを入力
4. [Create Report] ボタンをクリック
5. システムが自動で以下を実行（全自動）:
   a. 【質問生成】テーマから意思決定に必要な質問を5個生成（方向性レベル）
   b. レポート詳細画面に自動遷移（ローディング画面表示）
   c. 【質問洗練】各質問に対して Refiner API を並列呼び出し（自動開始）
   d. 【チャット実行】洗練完了後、自動でチャット実行開始
6. 各質問の実行結果がリアルタイムで表示される
7. (将来) Word形式のレポートを生成・ダウンロード
```

**ポイント:**
- テーマ入力後はワンクリックで全自動実行
- 質問洗練（Refine）は並列実行で高速化
- Refine完了後は自動でExecute開始（手動操作不要）

### 1.2 システムフロー図

```
┌──────────────┐     ┌──────────────────┐     ┌──────────────────┐     ┌──────────────┐     ┌──────────────┐
│   ユーザー    │     │  質問生成         │     │  質問洗練         │     │  チャット     │     │  Word       │
│   テーマ入力  │ ──▶ │  (方向性5個生成)  │ ──▶ │  (並列Refine)    │ ──▶ │   実行       │ ──▶ │   生成      │
└──────────────┘     └──────────────────┘     └──────────────────┘     └──────────────┘     └──────────────┘
       │                     │                        │                       │
       │                     │POST /reports           │POST /refiner (並列)   │POST /execute
       │                     │                        │PATCH /questions/{id}  │  (自動開始)
       ▼                     ▼                        ▼                       ▼
  ユーザー操作          バックエンド             フロントエンドが           バックエンドで
  (ワンクリック)        InitReportUseCase        並列オーケストレーション    順次実行
```

---

## 2. 画面設計

### 2.1 レポート作成画面

```
┌─────────────────────────────────────────────────────────┐
│ レポート作成                                              │
├─────────────────────────────────────────────────────────┤
│                                                           │
│ ※ 使用データはチャットと同様にdata_sourceから自動取得          │
│                                                           │
│ どんなレポートが欲しいですか？                              │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ 売上の傾向と季節性を分析して、来月の売上予測と          │ │
│ │ 改善点を教えてください。                               │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                           │
│                    [レポート生成開始]                      │
│                                                           │
├─────────────────────────────────────────────────────────┤
│ 進捗状況                                                  │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ ✅ 質問1: 売上の月次推移を分析                        │ │
│ │ ✅ 質問2: 季節性パターンの検出                        │ │
│ │ 🔄 質問3: 売上予測モデルの構築 (実行中...)            │ │
│ │ ⏳ 質問4: 改善点の特定                               │ │
│ │ ⏳ 質問5: 推奨アクションの生成                        │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                           │
│ ████████████░░░░░░░░ 3/5 完了                             │
│                                         [キャンセル]       │
└─────────────────────────────────────────────────────────┘
```

### 2.2 レポート履歴画面

```
┌─────────────────────────────────────────────────────────┐
│ レポート履歴                                              │
├─────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────────┐ │
│ │ 📄 売上分析レポート                                   │ │
│ │    2025-12-09 15:30 | sensor_logs.csv               │ │
│ │    [ダウンロード] [削除]                              │ │
│ ├─────────────────────────────────────────────────────┤ │
│ │ 📄 顧客セグメント分析                                 │ │
│ │    2025-12-08 10:15 | customers.xlsx                │ │
│ │    [ダウンロード] [削除]                              │ │
│ └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### 2.3 サイドバーへの追加

```
┌─────────────────┐
│ 📊 データ        │
│ 💬 チャット      │
│ 📝 レポート作成  │  ← 新規追加
│ 📋 レポート履歴  │  ← 新規追加
└─────────────────┘
```

---

## 3. API設計

### 3.1 エンドポイント一覧

| メソッド | エンドポイント | 説明 |
|---------|---------------|------|
| POST | `/customize/reports` | レポート作成（テーマから方向性レベルの質問を自動生成） |
| GET | `/customize/reports` | レポート履歴一覧 |
| GET | `/customize/reports/{report_id}` | レポート詳細取得 |
| PATCH | `/customize/reports/{report_id}/questions/{question_id}` | 質問を更新（洗練結果を保存） |
| POST | `/customize/reports/{report_id}/execute` | 質問実行（バックグラウンド） |
| POST | `/customize/reports/{report_id}/generate-word` | Word生成（バックグラウンド） |
| GET | `/customize/reports/{report_id}/download` | レポートダウンロード |
| DELETE | `/customize/reports/{report_id}` | レポート削除 |

### 3.2 アーキテクチャ

レポートビルダーは以下の3ステップで構成され、各ステップは独立したAPIとして実装されています：

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Step 1: 質問生成 (POST /reports)                                             │
│ - テーマから方向性レベルの質問を生成                                          │
│ - InitReportUseCase が担当                                                   │
│ - レスポンス後、フロントエンドがレポート詳細画面に遷移                          │
├─────────────────────────────────────────────────────────────────────────────┤
│ Step 2: 質問洗練 (POST /refiner + PATCH /reports/{id}/questions/{qid})       │
│ - フロントエンドが各質問に対して既存の Refiner API を呼び出し                   │
│ - 洗練結果を PATCH で保存                                                    │
│ - ユーザーは洗練結果を確認・編集可能                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│ Step 3: 質問実行 (POST /reports/{id}/execute)                                │
│ - 洗練された各質問でチャットを実行                                            │
│ - ExecuteQuestionsUseCase が担当                                             │
│ - バックグラウンドで順次実行                                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

**設計の特徴:**
- 各ステップは独立したAPI呼び出しとして実装
- フロントエンドがオーケストレーションを担当
- ユーザーに進捗をリアルタイムで表示可能
- 質問の洗練は既存の Refiner API を再利用

### 3.3 API詳細

#### POST /customize/reports

**Request:**
```json
{
  "theme": "売上の傾向と季節性を分析して、来月の売上予測と改善点を教えてください",
  "num_questions": 5,
  "data_source": "file"
}
```

**Response:**
```json
{
  "report_id": "abc123-uuid",
  "message": "Report created with 5 direction-level questions. Please use /refiner to refine each question."
}
```

**処理内容:**
1. データセット情報を取得（RefinerDataInfoMessageFactory）
2. LLM にテーマ + データ概要を送信 → 方向性レベルの質問を5個生成
3. レポートを DRAFT 状態で保存（refined_question は空）

#### PATCH /customize/reports/{report_id}/questions/{question_id}

**Request:**
```json
{
  "refined_question": "売上カラム、日付カラムを使って、月別売上推移を折れ線グラフで可視化してください"
}
```

**Response:**
```json
{
  "success": true,
  "question_id": "q1-uuid",
  "message": "Question updated successfully"
}
```

**処理内容:**
1. レポートから該当質問を検索
2. refined_question フィールドを更新
3. 保存

#### GET /customize/reports/{report_id}

**Response:**
```json
{
  "report": {
    "report_id": "abc123-uuid",
    "title": "売上の傾向と季節性を分析して...",
    "user_id": "user@example.com",
    "status": "draft",
    "questions": [
      {
        "question_id": "q1-uuid",
        "original_direction": "月別の売上推移はどうなっているか",
        "refined_question": "",
        "status": "pending",
        "chat_id": null,
        "message_id": null
      },
      // ... 5個
    ],
    "created_at": "2025-12-09T15:30:00",
    "updated_at": "2025-12-09T15:30:00"
  }
}
```

#### POST /customize/reports/{report_id}/execute

**Response:**
```json
{
  "report_id": "abc123-uuid",
  "status": "processing",
  "message": "Questions execution started in background"
}
```

**処理内容（バックグラウンド）:**
1. 各質問を順次実行
2. `run_complete_analysis_task` でチャット実行
3. 結果（chat_id, message_id）を保存
4. 全完了後、status を `completed` に更新

#### POST /customize/reports/{report_id}/generate-word

**Response:**
```json
{
  "report_id": "abc123-uuid",
  "status": "generating_word",
  "word_file_path": null,
  "message": "Word generation started in background"
}
```

**処理内容（バックグラウンド）:**
1. 各質問の結果を `analyst_db.get_chat_message()` で取得
2. python-docx でWord文書を生成
3. PersistentStorage に保存
4. status を `done` に更新

#### GET /customize/reports/{report_id}/download

**Response:** Word文書ファイル（application/vnd.openxmlformats-officedocument.wordprocessingml.document）

---

## 4. レポート出力仕様

### 4.1 Word構成

```
┌─────────────────────────────────────┐
│ [レポートタイトル]                    │  ← AI自動生成
│ 作成日: 2025-12-09                   │
├─────────────────────────────────────┤
│ 1. エグゼクティブサマリー              │  ← AI統合サマリー
│    - 主要な発見事項                   │
│    - 推奨アクション                   │
├─────────────────────────────────────┤
│ 2. 分析1: [見出し]                   │  ← AI自動生成
│    - 分析結果                        │
│    - [グラフ画像]                    │
│    - インサイト                      │
├─────────────────────────────────────┤
│ 3. 分析2: [見出し]                   │
│    ...                              │
├─────────────────────────────────────┤
│ 4. 結論                             │  ← AI統合インサイト
│    - 総合評価                        │
│    - 次のステップ                    │
└─────────────────────────────────────┘
```

### 4.2 グラフ処理

- Plotlyグラフを画像化（PNG形式）
- サイズ: 幅600px、高さ400px（統一）
- Word内での配置: 中央揃え
- RunChartsResult の `fig1` / `fig2` から一時PNGを生成し、セクションごとに埋め込む
- Word生成完了後は生成した一時ファイルを即座に削除し、ストレージを汚さない

### 4.3 サマリー・結論生成

- `GenerateWordUseCase` で各質問の結果を集約し、専用プロンプトを用いて LLM からエグゼクティブサマリーと結論を生成する。
- 生成は `AsyncLLMClient` を利用し、将来の追加質問や高度な要約に対応できるようプロンプトをモジュール化する。
- LLM から不足情報への追加質問が返る場合は、別途フローを設計して処理できるよう拡張余地を残す。

---

## 5. 状態管理

### 5.1 レポートステータス

| ステータス | 説明 |
|-----------|------|
| `pending` | 初期化完了、質問生成待ち |
| `refining` | 質問洗練中 |
| `chat_processing` | チャット実行中 |
| `completed` | 質問実行が全て完了 |
| `generating_word` | Word生成中 |
| `done` | Word生成完了、ダウンロード可能 |
| `error` | エラー発生 |

### 5.2 バックグラウンド処理

- ページを離れても処理は継続
- 定期的にステータスをポーリング（5秒間隔）
- 完了時に通知（オプション）

### 5.3 進捗表示方針

- レポート詳細画面ではヘッダー右側に全体ステータスバッジを表示する。
- 進捗カードには全体進捗（完了数/総数）のバーを表示し、個別質問カードでは状態バッジで細かい進行状況を示す。
- 各質問カードでは `StatusBadge` と `Not refined` / `Refined` バッジで状態を示す。

---

## 6. Feature Flag

| フラグ名 | 説明 |
|---------|------|
| `VITE_ENABLE_REPORT_BUILDER` | レポート作成機能の有効化 |

---

## 7. エラーハンドリング

### 7.1 質問実行失敗時

- 該当の質問をスキップして続行
- レポートには「分析できませんでした」と記載
- 最終的に全て失敗した場合のみエラー

### 7.2 キャンセル処理

- 現在実行中の質問完了後に停止
- 途中結果は破棄

---

## 8. 質問生成機能の詳細仕様

### 8.1 概要

レポートビルダーの質問生成は**2段階構成**で行う：

1. **質問生成（方向性レベル）**: テーマから意思決定に必要な質問を5個生成
2. **質問洗練（具体化）**: 各質問を既存のRefiner機能で具体的な分析質問に変換

### 8.2 設計思想

- **報告を受ける人（意思決定者）の視点**: 生成される質問は、データ分析者ではなく、レポートを受け取って意思決定を行う人にとって価値のある内容であること
- **端的な質問**: 複雑な分析手法ではなく、「何を知りたいか」を端的に表現
- **多角的な視点**: テーマを様々な角度からカバーし、意思決定に必要な情報を網羅

### 8.3 処理フロー

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Step 1: 質問生成（GenerateQuestionsUseCase）                              │
├─────────────────────────────────────────────────────────────────────────┤
│ 入力:                                                                    │
│   - theme: "売上の傾向と季節性を分析して、来月の売上予測と改善点を教えて"   │
│   - num_questions: 5（MVP固定）                                          │
│   - data_info: データセットのカラム情報、サンプルデータ                    │
│                                                                          │
│ 出力（方向性レベルの質問）:                                               │
│   1. "月別の売上推移はどうなっているか"                                   │
│   2. "季節による売上の変動パターンはあるか"                               │
│   3. "売上が高い/低い時期の要因は何か"                                    │
│   4. "来月の売上はどの程度になりそうか"                                   │
│   5. "売上を改善するために注目すべき指標は何か"                           │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Step 2: 質問洗練（RefineQuestionUseCase）× 5回                           │
├─────────────────────────────────────────────────────────────────────────┤
│ 入力: 方向性レベルの質問 + data_info                                      │
│                                                                          │
│ 出力（具体的な分析質問）:                                                 │
│   "売上カラム、日付カラムを使って、2024年1月から12月までの月別売上推移を   │
│    折れ線グラフで可視化してください"                                      │
└─────────────────────────────────────────────────────────────────────────┘
```

### 8.4 質問生成のプロンプト設計

#### 8.4.1 システムプロンプトの方針

```
目的: 報告を受ける意思決定者にとって価値のある質問を生成する

生成する質問の特徴:
- 端的で明確（「〜はどうなっているか」「〜は何か」形式）
- 意思決定に直結する内容
- データで回答可能な範囲
- 互いに補完し合い、テーマを多角的にカバー

避けるべき質問:
- 分析手法を指定する質問（「回帰分析で〜」など）
- 可視化方法を指定する質問（「棒グラフで〜」など）
- 抽象的すぎる質問（「データを分析して」など）
```

#### 8.4.2 入力形式

```
Theme: {ユーザーが入力したテーマ}
Number of Questions: {生成する質問数、MVP=5}
Data Shapes: {各カラムのデータ型}
Sample Data: {10行程度のサンプル}
Data Dictionary: {各カラムの説明}
```

#### 8.4.3 出力形式

```json
{
  "questions": [
    {
      "question": "月別の売上推移はどうなっているか",
      "reasoning": "時系列での傾向把握は売上分析の基本であり、意思決定の土台となる"
    },
    ...
  ]
}
```

### 8.5 質問洗練（Refiner）との連携

質問生成後、各質問を既存の `RefineQuestionUseCase` に渡して具体化する：

```python
# InitReportUseCase 内での処理イメージ
for generated_question in generated_questions:
    # Step 2: 各質問を洗練
    refined = await refine_question_usecase.run(
        direction=generated_question.question,
        data_info=data_info,
    )
    report.add_question(
        original_direction=generated_question.question,
        refined_question=refined.question,
    )
```

### 8.6 エラーハンドリング

| エラー種別 | 対応 |
|-----------|------|
| 質問生成失敗（LLMエラー） | エラーを返す。リトライはユーザー操作 |
| 質問洗練失敗（1つの質問） | 方向性をそのまま使用（`refined_question = original_direction`） |
| 質問洗練失敗（全質問） | 全て方向性のまま続行（エラーにはしない） |

### 8.7 MVP制約・実装方針

| 項目 | MVP実装 | 将来拡張 |
|-----|--------|---------|
| 質問数 | 5固定 | LLMが最適な数を判断 |
| 質問の編集 | 不可 | ユーザーが質問を追加・削除・編集 |
| 質問の承認 | 自動で次へ | ユーザーが質問リストを確認・承認 |
| data_info_factory | 質問生成・洗練で共有 | 分離して個別に取得 |
| RefineQuestionUseCase | API層で依存を構築して渡す | ファクトリパターンで簡略化 |

---

## 9. 実装チェックリスト

### Phase 1: バックエンドAPI - 基盤

- [x] Feature Flag設定 (`VITE_ENABLE_REPORT_BUILDER`)
- [x] Domain層: エンティティ、値オブジェクト
  - [x] `Report`, `ReportQuestion`, `ReportSection` エンティティ
  - [x] `ReportStatus`, `QuestionStatus` 値オブジェクト
  - [x] `IReportRepository` リポジトリインターフェース
  - [x] `GeneratedQuestion`, `ReportQuestionsGenerationRequest/Result` 質問生成用モデル
- [x] Infrastructure層
  - [x] `storage/report_storage.py` - PersistentStorage永続化（ユーザー別ローカルキャッシュ同期対応）
  - [x] `chat/chat_executor.py` - チャット実行（create_chat + add_chat_message + run_complete_analysis_task）
  - [x] `word/word_generator.py` - Word生成（python-docx）
- [x] 依存パッケージ: `python-docx` 追加

### Phase 1.5: バックエンドAPI - 質問生成（2段階構成）

- [x] 質問生成（方向性レベル）
  - [x] `llm/report_questions_generator.py` - LLMサービス
  - [x] `generate_questions.py` - UseCase
  - [x] プロンプト更新: 意思決定者視点の方向性質問を生成
    - [x] 「分析手法」「可視化方法」を指定しない質問形式に
    - [x] 「〜はどうなっているか」「〜は何か」形式
- [x] 質問洗練（具体化）- **フロントエンドからのオーケストレーション方式に変更**
  - [x] 既存の `POST /refiner` API を利用
  - [x] `PATCH /reports/{id}/questions/{qid}` で洗練結果を保存
  - [x] `InitReportUseCase` は方向性レベルの質問生成のみに責務を限定
- [x] エラーハンドリング
  - [x] 質問生成失敗時: Timeoutはエラーを返し、LLM例外/空結果はフォールバック質問でReport作成を継続
  - [x] 質問洗練失敗時: フロントエンドで処理

### Phase 1.6: バックエンドAPI - レポート操作

- [x] UseCase層
  - [x] `init_report.py` - レポート初期化（方向性レベルの質問生成のみ）
  - [x] `execute_questions.py` - 質問実行
  - [x] `generate_word.py` - Word生成
  - [x] `list_reports.py` - 一覧取得
  - [x] `get_report.py` - 詳細取得
  - [x] `delete_report.py` - 削除
- [x] API層
  - [x] `POST /reports` - レポート作成（方向性レベルの質問生成）
  - [x] `GET /reports` - 一覧取得
  - [x] `GET /reports/{report_id}` - 詳細取得
  - [x] `PATCH /reports/{report_id}/questions/{question_id}` - 質問更新（洗練結果保存）
  - [x] `POST /reports/{report_id}/execute` - 質問実行
  - [x] `POST /reports/{report_id}/generate-word` - Word生成
  - [x] `GET /reports/{report_id}/download` - ダウンロード
  - [x] `DELETE /reports/{report_id}` - 削除

### Phase 1.7: Word生成改修

- [ ] `GenerateWordUseCase` で LLM サマリー・結論生成を実装（AsyncLLMClient + 専用プロンプト）
- [ ] チャート画像を PersistentStorage から取得し、一時ファイル経由でWordへ埋め込んだ後に削除
- [ ] `ReportStatus` / `QuestionStatus` を `pending→refining→chat_processing→generating_word→done/error` 等の遷移で統一し、フロント表示も合わせる
- [ ] 進捗カードでは全体進捗バーを表示し、個別質問カードではバッジで状態を示す
- [ ] Word生成時のエラーハンドリングとログ出力を精査

### Phase 2: フロントエンドAPI層

- [x] `app_frontend/src/api/reports/types.ts` - 型定義
  - [x] `Report`, `ReportQuestion`, `ReportSummary` 型
  - [x] `ReportStatus`, `QuestionStatus` 型
  - [x] リクエスト/レスポンス型
  - [x] `UpdateQuestionRequest/Response` 型
- [x] `app_frontend/src/api/reports/api.ts` - API関数
  - [x] `listReports()` - 一覧取得
  - [x] `getReport()` - 詳細取得
  - [x] `createReport()` - レポート作成
  - [x] `updateQuestion()` - 質問更新
  - [x] `executeQuestions()` - 質問実行
  - [x] `generateWord()` - Word生成
  - [x] `deleteReport()` - 削除
- [x] `app_frontend/src/api/reports/hooks.ts` - React Queryフック
  - [x] `useReports()` - 一覧取得
  - [x] `useReport()` - 詳細取得（自動リフレッシュ対応）
  - [x] `useCreateReport()` - レポート作成
  - [x] `useUpdateQuestion()` - 質問更新
  - [x] `useExecuteQuestions()` - 質問実行
  - [x] `useGenerateWord()` - Word生成
  - [x] `useDeleteReport()` - 削除
- [x] `app_frontend/src/api/reports/index.ts` - エクスポート

### Phase 3: フロントエンドUI層

- [x] サイドバーにメニュー追加（`src/components/Sidebar.tsx`）
  - [x] チャットの下、設定の上にレポートメニューを配置
- [x] ルーティング設定（`/reports`, `/reports/:reportId`）
  - [x] `src/pages/routes.ts` 更新
  - [x] `src/pages/index.tsx` 更新
- [x] レポート作成/詳細画面（`src/pages/Reports.tsx`）
  - [x] `CreateReportForm` - テーマ入力フォーム
    - [x] ローディング中のフルスクリーン表示
  - [x] `ReportDetail` - レポート詳細表示
    - [x] 質問一覧表示（方向性・洗練済み質問）
    - [x] 「Refine All」ボタン（全質問を一括洗練）
    - [x] 各質問に「Refine」ボタン（個別洗練）
    - [x] 洗練中の状態表示（スピナー）
    - [x] 未洗練/洗練済みバッジ表示
    - [x] 「Execute Questions」ボタン（洗練完了後に有効化）
    - [x] 進捗バー表示（実行中）
    - [x] チャット結果へのリンク
    - [x] 削除ボタン
  - [x] `ReportList` - レポート一覧表示
  - [x] `StatusBadge` - ステータスバッジコンポーネント
- [x] 自動化フロー
  - [x] レポート作成後、自動でRefine開始（useEffect）
  - [x] Refineは並列実行（Promise.all）
  - [x] Refine完了後、自動でExecute開始
- [x] UIコンポーネント
  - [x] `src/components/ui/card.tsx` - Cardコンポーネント追加
- [ ] i18n対応（英語・日本語）- 部分対応（`t()`使用）

#### 2025-02-XX フロントエンド不具合修正
- `useUpdateQuestionStatus()` で `updateQuestionStatus` API を取り込み忘れていたためビルドが失敗していた問題を解消
- `StatusBadge` で `ready` ケースが重複し、TypeScript警告が出ていた箇所を修正
- `index.html` で `_dr_env.js` をESMとして解決できずビルドが停止していたため、実行時フェッチ+挿入方式に変更→修正
- `PATCH /reports/{report_id}/questions/{question_id}` が `status` を受け取れず422となっていたため、バックエンドで `status` の任意更新を許可（`status` 未指定で `refined_question` だけ送った場合は READY へ自動遷移）
- 質問実行が全て完了した際に `GenerateWordUseCase` を自動起動し、レポートWord生成までバックエンドで完結するように変更
- フロント詳細画面に「Download Word」ボタンを追加し、生成済みドキュメントをUIから直接取得できるようにした
- 一覧ページの各レポートカードにも「Download Word」ボタンを設置し、完了済みレポートをトップから即ダウンロードできる導線を追加
- レポート進捗（一覧・詳細とも）を「洗練（50%）＋チャット実行（50%）」の合算で表示するよう更新（未データ時のNaN回避）
- Word生成時に各質問の回答テキスト／会話ログを取得・格納し、ドキュメントに回答・会話要約・bottom_lineが出力されるように拡張

### 既知の課題（Known Issues）

- [ ] **Refine完了時の一時的な状態表示のちらつき**
  - 問題: refinerのレスポンスが返ってきて次の質問に処理が移る間に、一瞬「未refine」状態のUIが表示される
  - 原因: `refetch()`と`setRefiningQuestionIds`の更新タイミングのずれ
  - 改善案: 楽観的更新（Optimistic Update）を使用して、APIレスポンス受信時に即座にローカル状態を更新する

- [x] **PersistentStorageの保存直後取得でエラーが発生していた**
  - 課題: 保存直後に取得すると `Filename None does not exist.` が返るケースがあり、外部ストレージ側の同期遅延が原因だった。
  - 解決: ユーザー単位のローカルキャッシュを保持し、`atomic_write_json` で原子的に書き込んだ後に `PersistentStorage` へ同期する二層構造へ変更。加えて、`ReportStorage.get()` ではローカルから読み出した上でストレージ同期（必要なら再フェッチ）を行うため、API遅延に引きずられない。
  - 備考: フォールバックとして `NullPersistentStorage` を利用し、ログで検知できるようにした。

### Phase 4: テスト

- [ ] バックエンドAPIユニットテスト
- [ ] フロントエンドコンポーネントテスト
- [ ] E2Eテスト

### Phase 5: ドキュメント

- [x] REPORT_BUILDER.md更新（アーキテクチャ、API設計）
- [ ] CHANGELOG.md更新
- [ ] README更新（使い方）

---

## 9. 将来の拡張（スコープ外）

### 9.1 質問生成の改善
- **質問数のLLM決定**: テーマの複雑さに応じてLLMが最適な質問数を判断
- **質問の編集・承認**: ユーザーが生成された質問を確認・編集・追加・削除できる機能

### 9.2 データ選択の改善
- **データセットの手動選択**: ユーザーがレポートに使用するデータセットを明示的に選択
- **複数データソースの統合**: file/database等複数ソースを組み合わせたレポート

### 9.3 その他
- スケジュール実行
- テンプレート機能（定型レポート）
- レポート構成のカスタマイズ
- PDF出力対応
- 会社ロゴ/ブランドカラー対応

---

## 10. 永続化設計

### 10.1 保存方式

既存の `PersistentStorage` を使用してDataRobot Catalogにファイルを保存する。

| ファイル種別 | 保存形式 | 説明 |
|------------|---------|------|
| メタデータ | JSON | レポートID、ステータス、chatId等 |
| Wordファイル | .docx | 生成されたレポート本体 |
| グラフ画像 | PNG | 一時ファイル（Word生成後は不要） |

### 10.2 ファイル構成

```
# ファイル名の規則
report_{report_id}.json     # メタデータ
report_{report_id}.docx     # Wordファイル
```

### 10.3 メタデータJSON構造

```json
{
  "report_id": "abc123",
  "user_id": "user_xyz",
  "status": "completed",
  "chat_id": "chat_789",
  "title": "売上分析レポート",
  "user_request": "売上の傾向と季節性を分析して...",
  "data_source": "file",
  "dataset_ids": ["dataset_123"],
  "questions": [
    {
      "index": 0,
      "direction": "売上の月次推移を分析",
      "refined_question": "2024年1月から12月までの月別売上合計を...",
      "status": "completed"
    }
  ],
  "word_file_name": "report_abc123.docx",
  "created_at": "2025-12-09T15:30:00Z",
  "updated_at": "2025-12-09T15:45:00Z"
}
```

### 10.4 永続化フロー

```
1. レポート初期化時
   └─ report_{id}.json を保存（status: initialized）

2. 各質問実行後
   └─ report_{id}.json を更新（質問のstatusを更新）

3. Word生成完了時
   ├─ report_{id}.docx を保存
   └─ report_{id}.json を更新（status: completed, word_file_name追加）

4. ダウンロード時
   └─ report_{id}.docx を取得して返却

5. 削除時
   ├─ report_{id}.json を削除
   └─ report_{id}.docx を削除
```

### 10.5 再起動・ページ離脱時の復旧

- JSONに `chat_id` が保存されているため、`analyst_db.get_chat(chat_id)` で結果を再取得可能
- ステータスが `executing` のまま残っている場合は、フロントエンドから再開または削除を選択

#### 10.6 レポート保存フローの最適化

- `utils/customize/infrastructure/storage/report_storage.py` は、`custom_prompts.py` と同様にユーザー単位のローカルキャッシュを `utils/customize/` 配下に保持しつつ、`PersistentStorage` と同期する二層構造に変更。
- メタデータ・インデックス・Word をローカルに原子的に書き込み (`atomic_write_json` / `shutil.copy2`) 後、`PersistentStorage` に同期。外部ストレージのレスポンスに依存せず安定してアクセス可能。
- インデックスファイルは `report_index_{user_id}.json` としてユーザーごとに分離し、ローカル更新後に即座にストレージへ反映。
- Word ファイル保存時にはローカルコピーを残してからアップロードし、同期失敗時にもリトライや再利用ができるようにした。
- `PersistentStorage` が利用できない環境では `NullPersistentStorage` にフォールバックし、ログ出力で検知可能。

---

## 11. アーキテクチャ設計（クリーンアーキテクチャ）

### 11.1 ディレクトリ構成（実装済み）

```
utils/customize/
├── api_endpoints/
│   ├── __init__.py
│   ├── question_refiner.py
│   └── report.py                 # FastAPI Router（エンドポイント）
├── domain/
│   └── report/
│       ├── __init__.py
│       ├── domain.py             # エンティティ・値オブジェクト
│       │   ├── Report            # レポートエンティティ（集約ルート）
│       │   ├── ReportQuestion    # 質問エンティティ
│       │   ├── ReportStatus      # レポートステータス
│       │   ├── QuestionStatus    # 質問ステータス
│       │   ├── GeneratedQuestion # LLM生成質問
│       │   ├── ReportQuestionsGenerationRequest/Result
│       │   └── ReportCreateRequest/GenerateWordRequest
│       └── repository_interface.py  # IReportRepository
├── usecase/
│   └── report/
│       ├── __init__.py
│       ├── init_report.py        # レポート初期化（質問自動生成含む）
│       ├── execute_questions.py  # 質問実行
│       ├── generate_word.py      # Word生成
│       ├── generate_questions.py # テーマから質問自動生成
│       ├── list_reports.py       # 履歴一覧
│       ├── get_report.py         # 詳細取得
│       └── delete_report.py      # 削除
├── infrastructure/
│   ├── llm/
│   │   ├── llm.py                            # 既存: 質問洗練LLM
│   │   └── report_questions_generator.py     # 新規: 質問自動生成LLM
│   ├── analyst_db/
│   │   └── data_retriever.py                 # 既存: データ情報取得
│   ├── storage/
│   │   ├── __init__.py
│   │   └── report_storage.py     # PersistentStorageでレポート保存
│   ├── word/
│   │   ├── __init__.py
│   │   └── word_generator.py     # python-docxでWord生成
│   └── chat/
│       ├── __init__.py
│       └── chat_executor.py      # run_complete_analysis_task呼び出し
└── prompts.py                    # REPORT_QUESTIONS_GENERATOR_SYSTEM_PROMPT 追加
```

### 11.2 依存関係図

```
┌─────────────────────────────────────────────────────────────┐
│                    API Layer (FastAPI)                       │
│                 api_endpoints/report/                        │
└─────────────────────┬───────────────────────────────────────┘
                      │ depends on
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                    Use Case Layer                            │
│                   usecase/report/                            │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐│
│  │ InitReport  │ │ExecuteQuestion│ │ GenerateWord           ││
│  └─────────────┘ └─────────────┘ └─────────────────────────┘│
└─────────────────────┬───────────────────────────────────────┘
                      │ depends on (interfaces)
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                    Domain Layer                              │
│                   domain/report/                             │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐│
│  │ Report      │ │ Question    │ │ IReportRepository       ││
│  │ (Entity)    │ │(ValueObject)│ │ (Interface)             ││
│  └─────────────┘ └─────────────┘ └─────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
                      ▲ implements
                      │
┌─────────────────────────────────────────────────────────────┐
│                 Infrastructure Layer                         │
│  ┌─────────────────┐ ┌───────────────┐ ┌──────────────────┐ │
│  │ storage/        │ │ chat/         │ │ word/            │ │
│  │ report_storage  │ │ chat_executor │ │ word_generator   │ │
│  │ (Persistent     │ │ (run_complete_│ │ (python-docx)    │ │
│  │  Storage)       │ │ analysis_task)│ │                  │ │
│  └─────────────────┘ └───────────────┘ └──────────────────┘ │
│  ┌─────────────────┐ ┌───────────────┐                      │
│  │ llm/            │ │ analyst_db/   │  ← 既存              │
│  │ (AsyncLLMClient)│ │(data_retriever)│                     │
│  └─────────────────┘ └───────────────┘                      │
└─────────────────────────────────────────────────────────────┘
```

### 11.3 インフラストラクチャ層の詳細

#### infrastructure/storage/report_storage.py

```python
"""レポートの永続化（PersistentStorageを利用）"""
from utils.persistent_storage import PersistentStorage
from utils.customize.domain.report.entities import Report

class ReportStorage:
    def __init__(self, user_id: str):
        self._storage = PersistentStorage(user_id)
    
    async def save_metadata(self, report: Report) -> None:
        """メタデータJSONを保存"""
        local_path = f"/tmp/report_{report.report_id}.json"
        # JSONに書き出し
        atomic_write_json(local_path, report.to_dict())
        # 永続ストレージに保存
        await self._storage.save_to_storage(
            f"report_{report.report_id}.json", local_path
        )
    
    async def save_word_file(self, report_id: str, local_path: str) -> None:
        """Wordファイルを保存"""
        await self._storage.save_to_storage(
            f"report_{report_id}.docx", local_path
        )
    
    async def get_metadata(self, report_id: str) -> Report | None:
        """メタデータを取得"""
        ...
    
    async def list_reports(self) -> list[Report]:
        """レポート一覧を取得"""
        ...
    
    async def delete(self, report_id: str) -> None:
        """レポートを削除"""
        ...
```

#### infrastructure/chat/chat_executor.py

```python
"""チャット実行（run_complete_analysis_taskを利用）"""
from utils.rest_api import run_complete_analysis_task

class ChatExecutor:
    async def execute(
        self,
        question: str,
        analyst_db: AnalystDB,
        chat_id: str,
        message_id: str,
        data_source: str,
        request: Request,
    ) -> ChatResult:
        chat_request = ChatRequest(messages=[
            {"role": "user", "content": question}
        ])
        await run_complete_analysis_task(
            chat_request=chat_request,
            data_source=data_source,
            analyst_db=analyst_db,
            chat_id=chat_id,
            message_id=message_id,
            enable_chart_generation=True,
            enable_business_insights=True,
            request=request,
        )
        # 結果はanalyst_dbから取得
        return await analyst_db.get_chat_message(chat_id, message_id)
```

#### infrastructure/word/word_generator.py

```python
"""Word生成（python-docxを利用）"""
from docx import Document
from docx.shared import Inches

class WordGenerator:
    def generate(
        self,
        title: str,
        summary: str,
        sections: list[ReportSection],
        conclusion: str,
    ) -> str:
        """Wordファイルを生成し、ローカルパスを返す"""
        doc = Document()
        
        # タイトル
        doc.add_heading(title, 0)
        
        # サマリー
        doc.add_heading("エグゼクティブサマリー", level=1)
        doc.add_paragraph(summary)
        
        # 各セクション
        for section in sections:
            doc.add_heading(section.heading, level=1)
            doc.add_paragraph(section.content)
            if section.chart_path:
                doc.add_picture(section.chart_path, width=Inches(5))
        
        # 結論
        doc.add_heading("結論", level=1)
        doc.add_paragraph(conclusion)
        
        # 保存
        local_path = f"/tmp/report_{uuid.uuid4()}.docx"
        doc.save(local_path)
        return local_path
```

### 11.4 Refiner（質問洗練）の連携

既存の `llm/` を再利用。追加のアダプターは不要：

```python
# usecase/report/execute_question.py から直接呼び出し
from utils.customize.usecase.question_refiner.refiner import RefineQuestionUseCase
```

---

## 12. 技術スタック

### バックエンド

- FastAPI
- python-docx（Word生成）
- Plotly（グラフ画像化: `plotly.io.write_image`）
- PersistentStorage（DataRobot Catalog永続化）
- 既存のRefiner API、Chat API（直接関数呼び出し）
- asyncio（バックグラウンド処理）

### フロントエンド

- React + TypeScript
- React Query（状態管理 + ポーリング）
- TailwindCSS（UI）
- i18next（多言語）

---

## 13. 参考: 既存コードの活用

| 機能 | 既存コード | 利用方法 |
|-----|-----------|---------|
| 質問洗練 | `RefineQuestionUseCase` | 直接関数呼び出し |
| チャット実行 | `run_complete_analysis_task` | 直接関数呼び出し |
| 永続化 | `PersistentStorage` | JSON/Wordファイル保存 |
| データソース | 既存データアップロード | そのまま利用 |
| Feature Flag | `feature_flag_config.py` | パターン踏襲 |
| i18n | `ja.json`, `useTranslation` | パターン踏襲 |
| キャッシュ | `PersistentCache`, `atomic_write_json` | パターン踏襲 |


---

## 14. CI修正記録（2026-06-03）

PR #35 (`dev` -> `main`) をmainへ進めるため、Report Builder取り込み後のCI失敗をローカル再現して修正する。

### 対応内容

- `utils/customize/infrastructure/storage/report_storage.py` をRuff標準フォーマットに合わせる。
- ルート直下に誤って追跡されていた空ファイル `FETCH_HEAD` を削除する。
- Pulumi workflowに `VITE_ENABLE_REPORT_BUILDER` を追加し、dev/main環境へfeature flagを渡せるようにする。
- `Reports.tsx` のReact Hooks依存配列を補正し、ESLint警告を解消する。
- `app_frontend/package-lock.json` が追跡されていないため、CIのfresh `npm install` でPrettier判定が変わらないよう `prettier` を `3.6.2` に固定する。
- ルートからの `uv run pytest` が通るよう、pytestのimport pathとテスト用DataRobot envを明示する。
- DataRobot/LLMへ接続する `customize_docs` のE2E動作確認スクリプトは `RUN_CUSTOMIZE_DOCS_E2E=1` のときだけ実行し、通常の単体テストから外部依存を分離する。

### 検証対象

- `uv run ruff format --check .`
- `uv run ruff check .`
- `uv run pytest`
- `npm run test`（`app_frontend`）
- `npm run lint`（`app_frontend`）
- `npm run build`（`app_frontend`）
- `yamlfmt .github/workflows/pulumi-up.yml`

### 検証結果

- `uv run ruff format --check .`: 成功
- `uv run ruff check .`: 成功
- `uv run pytest`: 4 passed / 2 skipped（外部DataRobot/LLM E2E）
- `npm run test`（`app_frontend`）: 101 passed
- `npm run lint`（`app_frontend`）: 成功（警告なし）
- `npm run build`（`app_frontend`）: 成功
- lockfileなし一時コピーでの `npm install` + `npm run lint`（`app_frontend`）: 成功
- Node 22.22.3でのVitest/ESLint/Vite build: 成功
- `app_backend` CI相当の `uv run ruff format --check .` / `uv run ruff check .` / `uv run pytest`: 成功

---

## 15. dev環境手動スモーク確認（2026-06-03）

対象:

- dev app: `https://app.datarobot.com/custom_applications/6930f689133582194bec4bed/`
- 既存レポート: `59899024-4377-4c68-90f7-2dc4bc2660b2`

### GitHub secret / variable確認

- GitHub Environmentは `main` のみ存在し、`dev` environmentは存在しない。
- `.github/workflows/pulumi-up.yml` は `environment: main` で実行されるため、`dev` branchのPulumi updateもGitHub Environment `main` のsecret/variableを参照する。
- repo secretに `VITE_ENABLE_REPORT_BUILDER` は存在しない。
- `main` environment secretに `VITE_ENABLE_REPORT_BUILDER` は存在しない。
- `main` environment variableにも `VITE_ENABLE_REPORT_BUILDER` は存在しない。

### スモーク結果

| 項目 | 結果 | メモ |
|-----|------|------|
| dev appログイン後表示 | OK | Chromeの既存DataRobotセッションでアプリ本体を表示できた。 |
| Report Builder導線表示 | OK / 注意 | Sidebarの `Reports` と一覧画面を表示できた。ただし `reportBuilderEnabled` feature flagでは制御されていない。 |
| Report一覧 | OK | 既存レポート `店舗の売上の要因を分析したい` が表示された。 |
| Report詳細 | OK | 既存レポート詳細を開き、3件の質問が `Completed` と表示された。 |
| Chat結果導線 | OK | `View Chat Result` から既存チャット結果へ遷移できた。 |
| Chat結果表示 | OK | サマリー、結論、パネル表示を確認した。 |
| 新規Report作成 / 質問生成 | NG | `Smoke test 2026-06-03 店舗売上要因` で作成開始後、`Generating questions...` のまま完了しなかった。キャンセル後、一覧には残らなかった。 |
| Refine実行 | NG | チャット入力に `売上と訪問客数の関係は？` を入れて `質問を洗練` を実行したが、`洗練中...` のまま完了しなかった。 |
| `/reports` 直接アクセス | NG | `https://app.datarobot.com/custom_applications/6930f689133582194bec4bed/reports` を直接開くと `{"detail":"Not Found"}` になる。アプリ内遷移では表示可能。 |
| Word生成 / ダウンロード導線 | 未確認 | 現在の操作手段では詳細画面下部までスクロールできず、導線の表示確認ができなかった。 |
| 削除導線 | 部分確認 | 既存レポート詳細に削除ボタンは表示された。既存レポートを消す操作になるため実削除は未実行。 |

### main投入前の懸念

1. `VITE_ENABLE_REPORT_BUILDER` がGitHub側に未設定のため、workflowで追加したenvは空値になる。
2. Report Builder UIは現在 `reportBuilderEnabled` に接続されておらず、feature flagで表示制御されていない。
3. `/reports` と `/reports/{reportId}` のSPA deep linkがbackend fallbackに含まれておらず、直接アクセスやリロードで404になる。
4. dev環境でReport Builderの新規質問生成とRefinerが完了しない。LLM/API接続、タイムアウト、エラー表示の確認が必要。
5. Word生成導線は今回未確認のため、main merge前に別途確認が必要。

---

## 16. dev環境スモーク懸念への修正（2026-06-03）

### 対応内容

- GitHub repo secret `VITE_ENABLE_REPORT_BUILDER` を `origin` repo (`ryosukehata/talk-to-my-data-agent-pandas`) に設定した。
- BackendのSPA fallbackに `/reports` と `/reports/{reportId}` を追加し、直接アクセス / reload でもReact側へ返すようにした。
- `reportBuilderEnabled` をfrontendのfeature flag型・MSW mock・Sidebar・route guardへ接続した。
  - flagが `true` のときだけSidebarのReport Builder導線を表示する。
  - flagが `false` または未取得の場合、`/reports` routeは `/data` へ戻す。
- Report Builder / Refiner のLLM呼び出しにtimeoutを追加した。
  - 共通: `CUSTOMIZE_LLM_TIMEOUT_SECONDS`
  - Report Builder専用: `REPORT_BUILDER_LLM_TIMEOUT_SECONDS`
  - Refiner専用: `QUESTION_REFINER_LLM_TIMEOUT_SECONDS`
  - 未設定時は60秒。
  - Python 3.10の `asyncio.wait_for` は `asyncio.TimeoutError` を送出するため、timeout捕捉をPython 3.10/3.11/3.12で同じ挙動になるよう正規化した。
- Report detailのrefine処理で、失敗時に質問ステータスを `error` へ戻し、`error_message` を保存・表示するようにした。
- 自動refine後のexecuteは、全質問のrefineが成功した場合のみ実行するようにした。
- `completed` だがWord未生成のreportに `Generate Word` ボタンを表示し、`generating_word` 中はpollingするようにした。

### 追加テスト

- `app_backend/tests/test_main.py::test_reports_spa_routes`
  - `/reports` と `/reports/{reportId}` が `text/html` を返すことを確認。
- `app_backend/tests/test_llm_timeout.py`
  - Report Builder質問生成LLMがtimeoutで戻ることを確認。
  - Refiner LLMがtimeoutで戻ることを確認。
  - Report Builder質問生成UseCaseがtimeout理由を空質問へ潰さず保持することを確認。
- `app_frontend/tests/components/Sidebar.test.tsx`
  - `reportBuilderEnabled=false` でReports導線を非表示にすることを確認。
  - `reportBuilderEnabled=true` でReports導線を表示することを確認。

### 検証結果

- `uv run ruff check .`: 成功
- `PYTHONPATH=app_backend:. DATAROBOT_API_TOKEN=test-token DATAROBOT_ENDPOINT=https://example.com OTEL_SDK_DISABLED=true uv run pytest`: 8 passed / 2 skipped
- `PYTHONPATH=app_backend:. DATAROBOT_API_TOKEN=test-token DATAROBOT_ENDPOINT=https://example.com OTEL_SDK_DISABLED=true uv run --python 3.10 pytest app_backend/tests/test_llm_timeout.py`: 3 passed
- `PYTHONPATH=app_backend:. uv run mypy app_backend/tests/test_llm_timeout.py utils/customize/infrastructure/llm/timeout.py utils/customize/infrastructure/llm/report_questions_generator.py utils/customize/infrastructure/llm/llm.py utils/customize/usecase/report/generate_questions.py utils/customize/domain/question_refiner/service_interface.py`: 成功
- `uv run ruff check app_backend/tests/test_main.py app_backend/tests/test_llm_timeout.py utils/customize/infrastructure/llm/timeout.py utils/customize/infrastructure/llm/report_questions_generator.py utils/customize/infrastructure/llm/llm.py utils/customize/api_endpoints/report.py app_backend/app/main.py`: 成功
- `PYTHONPATH=app_backend:. DATAROBOT_API_TOKEN=test-token DATAROBOT_ENDPOINT=https://example.com uv run pytest app_backend/tests/test_main.py::test_reports_spa_routes app_backend/tests/test_llm_timeout.py`: 3 passed
- `./node_modules/.bin/vitest --run tests/components/Sidebar.test.tsx`（`app_frontend`）: 2 passed
- `./node_modules/.bin/vitest --run`（`app_frontend`）: 103 passed
- `./node_modules/.bin/eslint .`（`app_frontend`）: 成功
- `./node_modules/.bin/tsc -b tsconfig.app.json && ./node_modules/.bin/vite build`（`app_frontend`）: 成功
- `pnpm --dir app_frontend test` / `pnpm --dir app_frontend lint`: ローカルのpnpm 11.5.1が依存build script承認を要求し、`pnpm install` 段階で失敗した。追跡ファイルへのlock差分は残していない。

### 残確認

- この修正をdevへdeployした後、dev環境で新規Report作成・refine・execute・Word生成/ダウンロード・smoke用Report削除を再確認する。
- 既存レポートの削除は破壊的操作のため、smoke用に新規作成したreportのみ削除確認対象にする。

### dev環境確認で見つかった追加修正（2026-06-04）

- Chromeの認証済みセッションで `/reports` を直接開いたところ、アプリはSPAとして起動したが `/data/店舗売上予測.xlsx` にredirectされた。
- GitHub secret `VITE_ENABLE_REPORT_BUILDER` は設定済みだったが、PulumiがDataRobot Custom Applicationへ渡す `runtime_parameter_values` のfeature flag一覧に `VITE_ENABLE_REPORT_BUILDER` が含まれていなかった。
- `utils/customize/feature_flag_config.py` にfeature flag env一覧を集約し、backendのfeature flag endpointとPulumi runtime parameter作成で同じ一覧を使うようにした。
- `app_backend/tests/test_feature_flag_config.py` を追加し、Report Builder flagがenvから読めることとruntime parameter対象一覧に含まれることを確認する。

### dev環境スモーク継続で見つかった追加修正（2026-06-04）

- `VITE_ENABLE_REPORT_BUILDER` のruntime parameter修正後、Chromeの認証済みセッションで `/reports` direct link、SidebarのReports導線、既存Report一覧、`Generate Word` ボタン表示を確認した。
- 新規Report作成は `Generating questions...` から一定時間後に戻ったが、`Request failed with status code 500` で失敗した。
- 原因候補はReport Builder flag secretではなく、質問生成LLMが例外または空結果を返し、`GenerateQuestionsUseCase` が空質問を返した後に `InitReportUseCase` が `Failed to generate questions from theme` を投げる経路。
- `GenerateQuestionsUseCase` でTimeoutは従来通り上位へ伝播し、それ以外のLLM例外または空結果は決定的なフォールバック質問へ置き換えるようにした。
- `POST /v1/reports` はTimeoutを `504 Gateway Timeout` として返し、その他の失敗はスタックトレース付きでログへ出すようにした。
- FrontendのReport作成/Refine失敗表示は、Axiosの汎用文言ではなくFastAPIの `detail` を優先して表示するようにした。

#### 追加テスト・検証

- `app_backend/tests/test_llm_timeout.py`
  - LLM質問生成が例外を投げた場合に、指定件数のフォールバック質問を返すことを確認。
  - LLM質問生成が空結果を返した場合に、指定件数のフォールバック質問を返すことを確認。
- `uv run ruff check .`: 成功
- `PYTHONPATH=app_backend:. DATAROBOT_API_TOKEN=test-token DATAROBOT_ENDPOINT=https://example.com OTEL_SDK_DISABLED=true uv run pytest`: 12 passed / 2 skipped
- `npm run lint`（`app_frontend`）: 成功
- `npm run test`（`app_frontend`）: 103 passed
- `npm run build`（`app_frontend`）: 成功
- `pnpm --dir app_frontend lint` はローカルpnpm 11.5.1が `pnpm install` 段階でbuild script承認を要求して失敗した。CIは `.github/workflows` 上 `npm install` / `npm run test` / `npm run lint` / `npm run build` 構成のため、npm scriptで確認した。

### Refiner実行で見つかったLLM互換修正（2026-06-04）

- 新規Report作成後の自動Refineで、DataRobot LLM互換エンドポイントから `Unsupported parameter: max_tokens is not supported with this model. Use max_completion_tokens instead.` が返った。
- アプリ側のRefiner実装では `max_tokens` を直接指定していなかったため、`instructor` / OpenAI互換クライアント層で付与される `max_tokens` を吸収する必要があった。
- `utils/llm_client.py` に `CompletionTokenCompatibilityProxy` を追加し、LLM呼び出し直前に `max_tokens` を削除して `max_completion_tokens` へ変換するようにした。
- `app_backend/tests/test_llm_client.py` を追加し、通常のcompletion proxyとOpenAI client直下の互換proxyの両方で `max_tokens` が下流に残らないことを確認する。
- dev環境で再確認したところ、DataRobot LLM Blueprint側の `max_completion_length=2048` もOpenAI向けに legacy `max_tokens` として送られている可能性が高かった。
- OpenAI reasoning系モデルでは `max_tokens` ではなく `max_completion_tokens` / Responses APIの `max_output_tokens` を使う必要があるため、`infra/settings_generative.py` の `LLMSettings.max_completion_length` は未指定にした。
- `app_backend/tests/test_infra_llm_settings.py` を追加し、LLM Blueprint設定で `max_completion_length` を再度固定しないことをASTベースで確認する。importによるDataRobot SDK初期化を避けるため、設定ファイルを直接parseしている。

### デプロイ後のReport永続化修正（2026-06-30）

- 現象: Report Builderは表示されるが、新規作成・実行したreportが新しいrunで一覧に残らない。
- 原因: `ReportStorage` が metadata / index / Word のPersistentStorage保存を `asyncio.create_task(...)` で投げっぱなしにしていた。特にindex更新では一時ファイルを非同期taskへ渡した直後に削除していたため、`report_index_{user_id}` が永続化されず、次のrunで一覧復元できなかった。
- 修正: `ReportStorage.save()` / `_update_index()` / `save_word_file()` / `delete()` で、ローカルキャッシュ更新後にPersistentStorageの保存・削除完了を `await` する。
- 追加テスト:
  - `app_backend/tests/test_report_storage.py::test_save_persists_report_and_index_before_return`
    - `save()` が戻った時点で report metadata と index がPersistentStorageへ保存済みであることを確認。
  - `app_backend/tests/test_report_storage.py::test_list_by_user_recovers_reports_from_storage_after_new_run`
    - 別run相当の空ローカルキャッシュから、PersistentStorageのindexとmetadataを使って一覧復元できることを確認。

### Sidebar導線改善（2026-06-30）

- 現象: Sidebar上のReport Builder導線がDatasets / Chatsと違う見た目で、ファイルアイコンのみのため見つけづらい。
- 修正: Sidebarを `Datasets` -> `Chats` -> `Reports` の一連の流れにし、Reportsも同じセクション見出しと `+ New Report` ボタンで表示する。
- `+ New Report` は `/reports?new=1` に遷移し、Reports画面の作成フォームを開いた状態にする。
- 既存ReportのSidebar項目には `key` を設定し、クリック時の詳細遷移とactive表示に使えるようにする。
- 日本語UI向けに `New Report` -> `新しいレポート` の翻訳を追加。
- 追加テスト:
  - `app_frontend/tests/components/Sidebar.test.tsx`
    - feature flagがoffのときReportsとNew Reportを非表示にする。
    - feature flagがonのとき `Datasets` -> `Chats` -> `Reports` の順に表示し、`New Report` ボタンを表示する。

---

## 冗長箇所メモ

- **PersistentStorageの説明**: 現状は保存方式・チェックリスト・アーキテクチャなど複数箇所で同じ内容を繰り返し記載（例: 行202, 373, 541, 671, 690）。
- **Word生成手順**: python-docx利用や生成フローがAPI詳細・チェックリスト・技術スタックで重複（行111, 254, 303, 318, 378, 626付近）。
- **チャット実行(run_complete_analysis_task)**: API処理内容・アーキテクチャ図・インフラ詳細で似た説明を再掲（行183, 489, 581-599, 689）。
- **質問自動生成フロー**: ユーザーフロー、API節、チェックリスト、アーキテクチャ節に重複（行29, 107, 304, 306, 470周辺）。
- **Word構成仕様**: 4章の出力仕様と11.3節のWordGenerator説明で内容が重なる。

## 改善方針

1. 各テーマごとに詳細を1章へ集約し、他章では要約または参照リンクに置き換える。
2. チェックリスト(第8章)は完了可否のみに絞り、詳細説明は該当章への参照に統一する。
3. アーキテクチャ詳細(第11.3節)を実装リファレンスとし、API処理内容の節では高レベルな流れのみを記載する。
4. Word出力仕様は第4章に統合し、WordGenerator節では実装上の補足（テンプレート、スタイル設定など）に限定する。
