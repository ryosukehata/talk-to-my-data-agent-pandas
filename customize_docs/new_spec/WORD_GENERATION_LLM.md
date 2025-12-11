# Word生成LLM機能

## 概要

レポートのWord文書生成時に、LLMを使用してエグゼクティブサマリーと結論を自動生成する機能。

## アーキテクチャ

クリーンアーキテクチャに基づき、以下の責務分離を実現：

### ドメイン層 (Domain Layer)

`utils/customize/domain/report/service_interface.py`

```
+----------------------------------+
|     IReportSummaryService        |
|----------------------------------|
| + generate(messages) -> Result   |
+----------------------------------+

+----------------------------------+
|   IReportSectionDataRetriever    |
|----------------------------------|
| + get_section_data(...) -> Data  |
+----------------------------------+
```

**値オブジェクト:**
- `ReportSectionData`: セクションのデータ（heading, question, content, chart_paths）
- `ReportGeneratedSummary`: LLM生成結果（summary, conclusion）

### ユースケース層 - プロンプトビルダー

`utils/customize/usecase/prompt/builder.py`

```
+----------------------------------+
|   ISummarySectionDataFactory     |  ← UseCase層インターフェース
|----------------------------------|
| + create_message(report,         |
|   sections=None) -> Messages     |
+----------------------------------+
              ▲
              │ (Infrastructure層で実装)
              │
+----------------------------------+
| AnalystDBSectionDataRetriever    |
+----------------------------------+


+----------------------------------+
|     SummaryPromptBuilder         |
|----------------------------------|
| + build(report, sections=None)   |
|   -> Messages                    |
| - section_data_factory           |
| - system_prompt                  |
+----------------------------------+
```

### インフラ層 (Infrastructure Layer)

- `utils/customize/infrastructure/analyst_db/section_data_retriever.py`
  - AnalystDBからチャット結果を取得し、`ReportSectionData` を構築
  - `ISummarySectionDataFactory` としてもメッセージを生成
- `utils/customize/infrastructure/llm/report_summary_generator.py`
  - LLMクライアントを呼び出し、`ReportGeneratedSummary` を返す

### ユースケース層 (UseCase Layer)

`utils/customize/usecase/report/generate_word.py`

1. セクションデータ取得 (`IReportSectionDataRetriever`)
2. プロンプト構築 (`SummaryPromptBuilder`)
3. サマリー生成 (`IReportSummaryService`)
4. Word生成 (`WordGenerator`)
5. 永続化 (`ReportRepository.save_word_file`, `Report.status` 更新)

### API層 (API Layer)

`utils/customize/api_endpoints/report.py`

```
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
```

---

## テストスクリプト

`customize_docs/test_word_generation_llm.py`

- モックリポジトリ／LLMサービスで LLM経路とフォールバック経路をそれぞれ検証
- 実行例: `PYTHONPATH=. DATAROBOT_ENDPOINT=mock DATAROBOT_API_TOKEN=mock python customize_docs/test_word_generation_llm.py`

---

## メモ (2025-12-08)

1. 全質問完了後にフロントで `/generate-word` を自動発火させる。
2. Word生成完了後は `/reports/{id}/download` を呼んで即ダウンロード。
3. フロントではサマリー／結論をヘッダー表示（英語文言）。
4. `ReportSummary` に `summary`／`conclusion`／`word_file_path` を追加。
5. FastAPI に `/reports` 系ルートを `index.html` にフォールバックする設定を追加。
