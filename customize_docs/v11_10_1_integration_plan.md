# v11.10.1 integration notes

## Scope

`origin/dev` を起点に `upstream/main` (`v11.10.1`) を取り込む。

取り込む:

- OTel chat metrics
- OTel LLM span の DataRobot user id 属性
- OTel endpoint/header と use case entity id の infra export
- DataRobot NIM deployed LLM の CLI/infra 選択肢
- Dictionary table の edit icon
- JDBC Preview の Snowflake / SAP Datasphere / BigQuery URI 対応
- persistent file system と related tests の upstream 修正

維持する:

- pandas 公開挙動
- `utils/customize` 配下のカスタム機能
- `core.database_helpers` と `utils.database_helpers` の互換 import
- `core.data_connections.database.database_implementations` は互換ファサードとして維持
- root docs と `core/uv.lock` はこの fork の過去方針どおり採用しない

## Implementation decisions

- upstream は database implementation 本体を `core.data_connections.database.database_implementations` に置くが、この fork は既存互換のため `core.database_helpers` を本体として残す。
- `snowflake` / `sap` / `bigquery` / `datarobot_jdbc` は upstream `v11.10.1` に寄せ、`JDBC_URI` 必須の `JdbcPreviewOperator` 経路だけを使う。旧 Snowflake / BigQuery / SAP operator への fallback はこのブランチでは残さない。
- `app_backend` の古い `fsspec` / `pyarrow` direct pin は core 側の upstream 依存制約と衝突するため削除した。
- `app_backend/uv.lock` と `infra/uv.lock` は conflict marker を手編集せず、対応する `pyproject.toml` から再生成した。

## Tests

実施済み:

- `uv run --project core pytest core/tests/test_v1182_core.py core/tests/test_metrics.py core/tests/test_dr_file_system.py -q`: 16 passed, 22 skipped
- `uv run pytest app_backend/tests/test_upstream_compat_imports.py app_backend/tests/test_llm_client.py app_backend/tests/test_v1182_compat.py -q`: 31 passed
- `uv run pytest app_backend/tests customize_docs/test_question_refiner.py customize_docs/test_report_questions_generator.py customize_docs/test_word_generation_llm.py -q`: 155 passed, 2 skipped
- `npm --prefix app_frontend test`: 27 files / 163 tests passed
- `task --list --sort none`: passed
- `uv run ruff check core/src/core/database_helpers.py core/src/core/llm_client.py core/src/core/middleware.py core/src/core/telemetry app_backend/app/config.py app_backend/tests/test_llm_configuration.py app_backend/tests/test_v1182_compat.py infra/infra/app_backend.py infra/infra/components/dr_credential.py infra/configurations/llm/nim_deployed_llm.py`: passed
- `uv run --project core pytest core/tests/test_v1182_core.py -q`: 16 passed

補足:

- `npm --prefix app_frontend test -- DictionaryTable` は専用 test file が存在しないため `No test files found` で終了した。代わりに frontend 全体の Vitest を実行して確認した。
- backend/customize テスト完了後に LiteLLM の既存 atexit logging warning が表示されたが、pytest の終了コードは 0。
