# v11.8.2 integration notes

## Scope

`dev` に `v11.7.2` 同期PRがmergeされた状態を土台に、`v11.8.0..v11.8.2` から必要差分だけを移植する。

取り込む:

- transfer database hang修正
- `datarobot>=3.13.0` 前提
- `used_datasets` schema/frontend表示
- `datarobot_jdbc` database connection
- OTel endpoint/header/disabled env config
- frontend i18n `<html lang>` 同期とlocale修正

維持する:

- pandas公開挙動
- `core/src/core/customize`
- custom prompts
- question refiner
- report builder
- template selector
- LLM prompt/completion本文をデフォルト送信しない telemetry 方針

見送る:

- upstream のPolars前提差分
- broad theme/docs/logo churn
- sidebar keyboard shortcut削除など、今回のPR3受け入れに必須ではないUI churn
- requirements削除。forkでは既存deploy経路互換のため `requirements.txt` / `app_backend/requirements.txt` を維持する

## Implementation decisions

- `git merge v11.8.2` は legacy upstream churn とPolars前提差分の再衝突が大きいため、必要差分を手動移植する。実装後に `ours` merge で `v11.8.2` を履歴上の祖先にする。
- `AsyncDataRobotClient` は `httpx.Timeout(60.0, connect=30.0)` を明示し、paginationの `next` URL 取得では初回paramsを再送しない。
- OTel は `Config` の `otel_exporter_otlp_endpoint`, `otel_exporter_otlp_headers`, `otel_sdk_disabled` を app startup で `otel.configure(config)` に渡す。disabled時は FastAPI/requests/httpx auto-instrumentation を起動しない。
- `CodeGeneration` / `RunAnalysisResult` に `used_datasets` を追加し、LLMに利用可能dataset keyを明示する。LLMが不正な型を返した場合は空配列へ丸め、既存実行を落とさない。
- frontendは `IAnalysisComponent.used_datasets` を追加し、Behind the scenesのコードタブに使用datasetのprovenance stripを表示する。
- `JDBCCredentials` と `JdbcPreviewOperator` を追加し、PostgreSQL/MySQL/SQL Server の `jdbc:` URIだけを受け付ける。DataRobot SDKの同期preview APIはasyncメソッド内でexecutor経由にしてevent loopを塞がない。
- `.env.template`, `.datarobot/cli/base.yml`, infra runtime parameters に `datarobot_jdbc` / `JDBC_URI` / `JDBC_CONNECTION_PARAMETERS` と OTel env を追加する。
- `app_frontend/src/i18n/index.ts` で `document.documentElement.lang` をi18n languageに同期し、`pt_BR` などのunderscoreはhyphenへ正規化する。

## TDD notes

REDで追加したテスト:

- `core/tests/test_v1182_core.py`
  - `AsyncDataRobotClient` timeout / pagination params
  - telemetry disabled時のauto-instrumentation抑止
  - `used_datasets` schema
  - `datarobot_jdbc` connection type / credentials / operator
- `app_backend/tests/test_v1182_compat.py`
  - OTel config
  - DataRobot SDK constraint
  - `.env.template` / CLI / infra runtime parameter
- `app_frontend/tests/components/CodeTabContent.test.tsx`
  - `usedDatasets` が空なら非表示
  - dataset名をcomma-separatedで表示
- `app_frontend/tests/i18n/index.test.ts`
  - `<html lang>` 初期化
  - `pt_BR` -> `pt-BR` 正規化

RED確認:

- `uv run --project core pytest core/tests/test_v1182_core.py -q`
  - `JDBCCredentials` 未実装で import error
- `uv run pytest app_backend/tests/test_v1182_compat.py -q`
  - OTel config / SDK constraint / env docs / infra runtime parameter未実装で失敗
- `pnpm --dir app_frontend test ...`
  - repoはnpm CI構成だが、ローカルpnpmはbuild approval policyでテスト実行前に停止。以降はCIと同じnpmで検証する

GREEN確認:

- `uv run --project core pytest core/tests/test_v1182_core.py core/tests/scripts/test_transfer_database.py -q`: 10 passed
- `uv run --project core pytest core/tests -q`: 11 passed
- `uv run pytest app_backend/tests/test_v1182_compat.py app_backend/tests/test_api_analysis_execution_v0424_compat.py app_backend/tests/test_upstream_compat_imports.py -q`: 25 passed
- `uv run pytest app_backend/tests customize_docs/test_question_refiner.py customize_docs/test_report_questions_generator.py customize_docs/test_word_generation_llm.py -q`: 128 passed, 2 skipped
- `npm --prefix app_frontend test`: 27 files / 163 tests passed
- `npm --prefix app_frontend run lint`: 0 errors, existing warnings only
- `npm --prefix app_frontend run knip`: passed, existing configuration hint only
- `npm --prefix app_frontend run build`: passed
- `task --list --sort none`: passed
- `uv run ruff check core/src/core/database_helpers.py core/src/core/api.py core/src/core/credentials.py core/src/core/persistent_storage.py core/src/core/telemetry/otel.py core/tests/test_v1182_core.py app_backend/app app_backend/tests/test_v1182_compat.py app_backend/tests/test_api_analysis_execution_v0424_compat.py infra/infra/components/dr_credential.py infra/infra/app_backend.py`: passed
- `uv run --project infra ruff check`: passed
- `task infra:unit`: skipped because `infra/tests/units/` does not exist

## Local test notes

- `uv run --project infra pytest` はrepository rootの `pytest.ini` を拾い、infra venvで `app_backend/tests` まで収集して `datarobot_asgi_middleware` 不足で失敗する。これはv11.6.3/v11.7.2で記録済みのproject-level collection問題と同じで、infra Taskfileの対応経路は `task infra:unit`。
- `pnpm --dir app_frontend test` は `ERR_PNPM_IGNORED_BUILDS` で `pnpm install` の段階で止まった。CIは `.github/workflows/app_frontend-vitest.yml` と `app_frontend/Taskfile.yaml` の両方でnpmを使うため、npmコマンドで最終確認した。
- 一度pnpmを実行した副作用で `node_modules` がpnpmレイアウトになり、`npm run build` が `unenv/node/process` import解決で失敗した。`rm -rf app_frontend/node_modules && npm --prefix app_frontend install` でCI相当のnpmレイアウトへ戻し、build/test/lint/knipを再実行して通過確認した。
- 2026-06-28 dev merge後の `Pulumi Up` は ApplicationSource build 成功後、CustomApplication の ready 判定で失敗した。DataRobot APIで対象ApplicationSource versionを確認すると `healthEndpointPath` が `null` で、アプリ側は `/health` を公開しているため、`ApplicationSourceResourcesArgs.health_endpoint_path="/health"` を明示して readiness probe をアプリ実装に合わせた。
