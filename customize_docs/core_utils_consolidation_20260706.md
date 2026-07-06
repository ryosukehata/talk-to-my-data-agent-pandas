# core/utils 構成整理

## 背景

`v11.5.1` の upstream 追従で、実装本体は `utils` から `core/src/core`
へ移行済み。現在の `utils` は旧 import を壊さないための互換 shim だが、
AGENTS と一部テストがまだ `utils` を実装場所のように扱っていた。

## 方針

- canonical implementation は `core/src/core`。
- customize のクリーンアーキテクチャ実装は `core/src/core/customize`。
- `utils` / `utils.customize` は `core.*` への legacy compatibility shim のみ。
- 互換性検証テスト以外の新規テスト/実装は `core.*` を import する。
- `utils` 配下に新しい業務ロジックを追加しない。

## 実施内容

- `AGENTS.md` の実装場所を `core/src/core/customize` に更新。
- `utils/README.md` を追加し、互換 shim であることを明記。
- 非互換テストの import を `utils.*` から `core.*` に変更。
- `customize_docs/test_core_utils_consolidation.py` を追加し、以下を固定。
  - runtime code が legacy `utils` を import しないこと。
  - 互換性テスト以外が legacy `utils` を import しないこと。
  - `utils` 配下が `core` への shim のみであること。
  - AGENTS/README が `core/src/core/customize` を canonical として説明すること。
  - root pytest が別プロジェクトの `core/tests` を収集しないこと。
- root の `pytest.ini` / `pyproject.toml` で `core` を `norecursedirs`
  に追加。`core` project のテストは `uv run --project core pytest core/tests`
  で実行する。
- root 全体テストで既存の `.datarobot/cli/base.yml` drift も検出したため、
  `DATABASE_CONNECTION_TYPE` の後方互換値
  (`snowflake` / `bigquery` / `sap`) を CLI 選択肢へ戻した。

## テスト計画

- `uv run pytest customize_docs/test_core_utils_consolidation.py -q`
- `uv run pytest app_backend/tests/test_feature_flag_config.py app_backend/tests/test_llm_client.py app_backend/tests/test_llm_timeout.py customize_docs/test_word_generation_llm.py -q`
- `uv run pytest app_backend/tests/test_upstream_compat_imports.py app_backend/tests/test_v1151_core_customize_imports.py -q`
- `uv run pytest -q`

`customize_docs/test_question_refiner.py` と
`customize_docs/test_report_questions_generator.py` は
`RUN_CUSTOMIZE_DOCS_E2E=1` が必要な DataRobot/LLM E2E smoke のため、
通常の自動実行では module skip される。
