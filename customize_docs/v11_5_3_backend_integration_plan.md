# v11.5.3 backend integration plan

## 目的

upstream `v11.5.3` の backend/runtime 差分を、現行 fork の pandas 前提、`utils` compatibility layer、既存 FastAPI app factory を維持したまま取り込む。

## 対象

- `/health` response に deploy version 情報を追加。
- static frontend runtime env (`/_dr_env.js`) に `APP_VERSION` を追加。
- logging default を JSON から readable format へ変更し、extra fields を維持。
- DataRobot API 呼び出しで builder token fallback を許可できるようにする。
- builder token fallback の設定を upstream と同じ `core.config.Config` 経由に寄せる。
- local 実行時の空 `DATAROBOT_DEFAULT_USE_CASE` を DataRobot client config へ明示する。
- Data Registry / DataStore まわりの 403 seat license error と wrapped `ClientError` handling を upstream に寄せる。
- token usage の default fallback を `tiktoken` から heuristic strategy へ変更。
- token tracking 実装を `datarobot_genai.core.utils.token_tracking` へ寄せ、`core.token_tracking` / `utils.token_tracking` の compatibility shim は削除する。
- `llm_client.py` に upstream の OpenAI exception import と verbose error logging を取り込む。
- `core/pyproject.toml` と `app_backend/core -> ../core` の editable package 構成を upstream `v11.5.3` に寄せる。
- backend 依存関係を upstream `v11.5.3` の source constraints に寄せ、`datarobot-genai`、`pyarrow==20.0.0`、`pydantic>=2.11.4`、`duckdb>=1.3.1`、`datarobot-asgi-middleware>=0.2.0` などを反映。
- upstream `v11.5.1` 以降の `core/src/core/routers/*` 分割を復帰し、monolithic な `core.rest_api` を app factory と互換 re-export 中心へ縮小する。
- OpenTelemetry は upstream と同じ `app_backend/app/telemetry/otel.py` と `core/src/core/telemetry` symlink 構成へ寄せる。
- chart prompt に、title/axis/annotation は plain text のみという制約を追加。
- CI workflow は upstream `v11.5.3` の backend/core/frontend/infra 分割と Taskfile 実行方式へ寄せ、root `requirements.txt` install に依存する独自 workflow は削除する。
- frontend CI は upstream と同じ lint/test/knip/coverage 構成へ寄せる。ただしこの fork には `app_frontend/package-lock.json` がないため、install command は `npm install` を維持する。
- upstream Taskfile の strict mypy 実行は、既存 fork の customize 実装と tests がまだ mypy clean ではないため今回の CI 復旧範囲から外す。型整備は別 PR で扱う。
- `app_backend/Taskfile.yaml` の `TEST_USER_EMAIL` は dev task のみに残し、test task へは渡さない。CI では deployed-like environment と衝突して session middleware が runtime error になるため。

## 見送り

- React UI 側の version 表示、Add Data modal、Settings modal は frontend PR で扱う。
- React UI 本体の upstream 追従は frontend PR で扱う。
- `.env.template` は infra PR で扱う。

## TDD

### RED

- `app_backend/tests/test_main.py`
  - `/health` に `version` が含まれること。
  - `VERSION` file の空白を除去して app version を読むこと。
- `app_backend/tests/test_v1153_backend_compat.py`
  - default log format が `readable` であること。
  - readable formatter が extra fields を失わないこと。
  - builder token fallback が許可時だけ使われること。
  - `core.config.Config` が `USE_BUILDER_API_TOKEN` / `MLOPS_RUNTIME_PARAM_USE_BUILDER_API_TOKEN` と `DATAROBOT_API_TOKEN` を公開すること。
  - 空文字の boolean env (`USE_DATAROBOT_LLM_GATEWAY=` など) は未設定扱いになり、Config 初期化を壊さないこと。
  - local empty use case が `default_use_case=[]` として設定されること。
  - token 使用時も空 `DATAROBOT_DEFAULT_USE_CASE` が `default_use_case=[]` として DataRobot client に渡ること。
  - seat license 403 が `ApplicationUsageException` になること。
  - ValueError wrapped 404 が `RecipeError` になること。
  - ClientError を含まない ValueError が unexpected exception として `RecipeError` になること。
  - token counting fallback が heuristic strategy であること。
  - `TokenUsageTracker` などを `datarobot_genai` から直接 import すること。

### GREEN

- `app_backend/app/__init__.py` に `get_app_version()` と runtime env `APP_VERSION` を追加。
- `app_backend/app/telemetry/*` に `ReadableFormatter` を追加し、default config を `readable` に変更。
- `core/src/core/config.py` を追加し、upstream と同じ `use_builder_api_token` setting を持たせる。
- `core/src/core/datarobot_client.py` に builder token fallback と empty use case handling を追加。
- `core/src/core/data_connections/datarobot/helpers.py` に wrapped ClientError / seat license 403 / ClientError を含まない ValueError fallback handling を追加。
- `core/src/core/api.py` / `core/src/core/rest_api.py` の DataRobot user-token context で builder token fallback を許可。
- `core/src/core/token_tracking.py` と `utils/token_tracking.py` を削除し、参照箇所は `datarobot_genai.core.utils.token_tracking` へ直接切り替える。
- `estimate_csv_rows_for_token_limit` の呼び出しは upstream と同じ 3 引数に揃える。
- `core/src/core/llm_client.py` の `TokenUsageTracker` import を `datarobot_genai` へ変更。
- `core/src/core/llm_client.py` は既存の `LLMClientConfig` / `create_with_completion` 対応を維持しつつ、upstream の `APIConnectionError` / `APITimeoutError` / `RateLimitError` などの詳細ログを `CompletionsProxy` に追加する。
- `core/pyproject.toml`、`core/README.md`、`core/Taskfile.yaml`、`app_backend/core` symlink を復帰し、`app_backend/pyproject.toml` から `core` を editable dependency として参照する。
- `app_backend/requirements.in` を upstream 形式で追加し、`app_backend/requirements.txt` を compile 生成物として更新。
- `core` の upstream 制約 `kaleido==0.2.0` と衝突しないよう、app_backend 側の重複制約も `kaleido==0.2.0` に戻す。
- `fastapi>=0.115.11,<0.130` にして、`fastapi 0.138` / `starlette 1.3` 系で `_IncludedRouter.path` が存在せず ASGI instrumentation が落ちる問題を避ける。
- `core/src/core/prompts.py` に chart title/text の plain text 制約を追加。
- `core/src/core/deps.py` と `core/src/core/routers/*` を復帰し、registry/database/datasets/dictionaries/chats/external-data-stores/user の endpoint 実装を upstream と同じ router module に分割。
- `core/src/core/rest_api.py` は upstream の thin app factory に寄せつつ、既存の `create_app()` singleton、`app` export、`core.customize.rest_api` mount、`utils.rest_api` 経由の互換 re-export を維持。
- `core/src/core/file_utils.py` を追加し、CSV decode/validation helper を router から参照する構成へ移動。ただし fork の pandas 前提を維持するため、upstream の polars return ではなく `pd.DataFrame` を返す。
- `core/src/core/routers/database.py` は upstream split を採用しつつ、既存 fork の `schema_name` 指定を background task に渡す挙動を維持。
- `app_backend/tests/test_v1151_fastapi_app_factory.py` に、`/api/v1/datasets/upload`、`/api/v1/database/select`、`/api/v1/chats/{chat_id}/messages` が `core.routers.*` の endpoint を指す characterization test を追加。
- `app_backend/app/telemetry/otel.py` と `core/src/core/telemetry -> ../../../app_backend/app/telemetry` を復帰し、`core.rest_api` は upstream と同じ `from .telemetry import otel` を使う。
- `core/src/core/data_analyst_telemetry.py` は `core.telemetry.otel` への互換 alias に縮小し、既存の `telemetry.trace` / `telemetry.time` import を維持しながら実体を upstream `OTel` singleton に揃える。
- `app_backend/tests/test_v1153_backend_compat.py` に `core.rest_api.otel` と旧 `core.data_analyst_telemetry.telemetry` が同じ `core.telemetry.otel` を指すことを固定するテストを追加。
- `.github/workflows/*` を upstream `v11.5.3` の分割 workflow に寄せ、root `requirements.txt` を install する `lint-python` / `python-static-checks` / `python-deps-install-test` / `python-unit-tests` / `pulumi-up` workflow を削除する。
- `app_backend/Taskfile.yaml`、`frontend/Taskfile.yaml`、`infra/Taskfile.yaml`、`frontend/pyproject.toml`、`frontend/uv.lock`、`infra/pyproject.toml`、`infra/uv.lock` を upstream `v11.5.3` に寄せる。
- `app_frontend/package.json` に upstream workflow が要求する `test:coverage` script と `@vitest/coverage-v8` を追加する。
- `app_frontend/vite.config.ts` に upstream と同じ coverage reporter (`json-summary` を含む) を追加し、coverage report action が参照する `coverage-summary.json` を生成する。
- `core/Taskfile.yaml` と `frontend/Taskfile.yaml` は、Python tests が未配置の場合の pytest exit 5 を成功扱いにする。legacy `frontend` は coverage XML が生成されないため、`frontend-test.yml` の coverage upload は外す。
- `core/src/core/resources.py` は `pydantic-settings` 2.12 で `parse_env_vars` の公開位置が変わったため、旧 `pydantic_settings.sources` と新 `pydantic_settings.sources.utils` の両方に対応する。
- `core.config.Config` は `DataRobotAppFrameworkBaseSettings` の設定を継承しつつ `env_ignore_empty=True` にして、空の `.env` / runtime parameter を未設定扱いにする。
- `core.customize.usecase.report` / `utils.customize.usecase.report` の互換 re-export は lazy import にし、Word生成など質問生成LLMを使わない経路で `datarobot_genai` import を強制しない。

## 検証

- `uv run --project app_backend --all-extras --dev pytest app_backend/tests/test_v1153_backend_compat.py -q`: 12 passed
- `uv run --project app_backend --all-extras --dev pytest app_backend/tests/test_llm_client.py -q`: 12 passed
- `uv run --project app_backend --all-extras --dev pytest app_backend/tests/test_v1153_backend_compat.py app_backend/tests/test_main.py app_backend/tests/test_v1151_fastapi_integration.py -q`: 22 passed, 3 skipped
- `uv run --project app_backend --all-extras --dev pytest app_backend/tests -q`: 107 passed, 3 skipped
- `uv run --project app_backend --all-extras --dev pytest app_backend/tests/test_v1151_fastapi_app_factory.py app_backend/tests/test_v1151_fastapi_integration.py app_backend/tests/test_rest_api_v0424_compat.py app_backend/tests/test_main.py app_backend/tests/test_upstream_compat_imports.py -q`: 29 passed, 3 skipped
- `uv run --project app_backend --all-extras --dev pytest app_backend/tests -q`: 108 passed, 3 skipped
- `uv run --project app_backend --all-extras --dev pytest app_backend/tests/test_v1153_backend_compat.py app_backend/tests/test_v1151_fastapi_app_factory.py app_backend/tests/test_v1151_fastapi_integration.py app_backend/tests/test_main.py -q`: 28 passed, 3 skipped
- `uv run --project app_backend --all-extras --dev pytest app_backend/tests -q`: 109 passed, 3 skipped
- `uv run --project app_backend --all-extras --dev ruff check core/src/core/llm_client.py app_backend/tests/test_llm_client.py`: passed
- `uv run --project app_backend --all-extras --dev ruff check core/src/core/data_connections/datarobot/helpers.py app_backend/tests/test_v1153_backend_compat.py`: passed
- `uv run --project app_backend --all-extras --dev ruff check --fix core/src/core/rest_api.py core/src/core/file_utils.py core/src/core/routers app_backend/tests/test_rest_api_v0424_compat.py app_backend/tests/test_v1151_fastapi_app_factory.py`: passed
- `uv run --project app_backend --all-extras --dev ruff check app_backend/app/telemetry core/src/core/rest_api.py core/src/core/data_analyst_telemetry.py app_backend/tests/test_v1153_backend_compat.py app_backend/tests/test_v1151_fastapi_app_factory.py`: passed
- `uv run --project core python - <<'PY' ...`: core import smoke passed
- `uv run --project core python - <<'PY' ...`: `core.token_tracking` removed smoke passed
- `uv run ruff format --check .` / `uv run ruff check .` (`app_backend`): passed
- `uv run pytest -q` (`app_backend`): 112 passed
- `uv run ruff format --check src` / `uv run ruff check src` (`core`): passed
- `uv run pytest --cov ...` with no-test exit handling (`core`): no tests collected, accepted as package-level no-test state
- `uv run ruff format --check .` / `uv run ruff check .` (`infra`): passed
- `uv run ruff format --check .` / `uv run ruff check .` (`frontend`): passed
- `uv sync --all-extras --dev` (`frontend`): passed after restoring `frontend/core -> ../core`
- `uv run pytest --cov ...` with no-test exit handling (`frontend`): no tests collected, accepted as legacy no-test state
- `uv run --with 'pydantic-settings==2.12.0' python - <<'PY' ...` (`app_backend`): `core.resources` import passed
- `npm run lint` (`app_frontend`): passed with 6 existing warnings
- `npm run test` (`app_frontend`): 123 passed
- `npm run knip` (`app_frontend`): passed with 1 configuration hint
- `npm run test:coverage` (`app_frontend`): 123 passed and coverage summary generated
- `npm run build` (`app_frontend`): passed
- GitHub workflow YAML parse via `python3` + PyYAML: passed
- 2026-06-23 PR #103 最新dev追従後:
  - `uv run --project app_backend pytest app_backend/tests/test_main.py app_backend/tests/test_llm_configuration.py app_backend/tests/test_v1151_fastapi_app_factory.py app_backend/tests/test_v1151_fastapi_integration.py app_backend/tests/test_v1153_backend_compat.py -q`: 41 passed
  - `uv run --project app_backend pytest app_backend/tests -q`: 119 passed, 3 warnings
  - `uv run pytest customize_docs -q`: 27 passed, 2 skipped
  - `uv run --project app_backend ruff check app_backend/app/__init__.py app_backend/tests/test_main.py app_backend/tests/test_v1153_backend_compat.py core/src/core/config.py core/src/core/customize/usecase/report/__init__.py core/src/core/customize/usecase/report/init_report.py utils/customize/usecase/report/__init__.py customize_docs/test_pulumi_workflow_refresh.py customize_docs/test_taskfile_deployment_dx.py`: passed

## 既知事項

- `app_backend/tests` 終了後、LiteLLM の atexit logging が閉じた stream に書こうとする warning が出ることがある。pytest の終了コードは成功しており、本 PR の変更による test failure ではない。
- Python 3.12.11 では `aiohttp.connector` の `enable_cleanup_closed` deprecation warning が 1 件出る。pytest の終了コードは成功。
- `app_backend` / `core` で strict mypy を試すと既存 customize/tests 由来のエラーが多数出る。upstream CI 構成との差分として、今回の Taskfile lint は ruff に限定する。
