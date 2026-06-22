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
- Data Registry / DataStore まわりの 403 seat license error を利用者向け例外へ変換。
- token usage の default fallback を `tiktoken` から heuristic strategy へ変更。
- token tracking 実装を `datarobot_genai.core.utils.token_tracking` へ寄せ、既存 `core.token_tracking` / `utils.token_tracking` import は compatibility re-export として維持。
- backend 依存関係を upstream `v11.5.3` の source constraints に寄せ、`datarobot-genai`、`pyarrow==20.0.0`、`pydantic>=2.11.4`、`duckdb>=1.3.1`、`datarobot-asgi-middleware>=0.2.0` などを反映。
- chart prompt に、title/axis/annotation は plain text のみという制約を追加。

## 見送り

- React UI 側の version 表示、Add Data modal、Settings modal は frontend PR で扱う。
- `.env.template`、CI workflow、Taskfile は infra PR で扱う。

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
  - local empty use case が `default_use_case=[]` として設定されること。
  - token 使用時も空 `DATAROBOT_DEFAULT_USE_CASE` が `default_use_case=[]` として DataRobot client に渡ること。
  - seat license 403 が `ApplicationUsageException` になること。
  - ValueError wrapped 404 が `RecipeError` になること。
  - token counting fallback が heuristic strategy であること。
  - `TokenUsageTracker` などが `datarobot_genai` 実装から提供されること。
  - `estimate_csv_rows_for_token_limit` が既存コードの `model` 引数付き呼び出しを受けられること。

### GREEN

- `app_backend/app/__init__.py` に `get_app_version()` と runtime env `APP_VERSION` を追加。
- `app_backend/app/telemetry/*` に `ReadableFormatter` を追加し、default config を `readable` に変更。
- `core/src/core/config.py` を追加し、upstream と同じ `use_builder_api_token` setting を持たせる。
- `core/src/core/datarobot_client.py` に builder token fallback と empty use case handling を追加。
- `core/src/core/data_connections/datarobot/helpers.py` に wrapped ClientError / seat license 403 handling を追加。
- `core/src/core/api.py` / `core/src/core/rest_api.py` の DataRobot user-token context で builder token fallback を許可。
- `core/src/core/token_tracking.py` を `datarobot_genai.core.utils.token_tracking` の compatibility re-export に変更。
- `core/src/core/token_tracking.py` の `estimate_csv_rows_for_token_limit` は既存 4 引数呼び出しを受け、`model` を無視して `datarobot_genai` 実装へ委譲する。
- `core/src/core/llm_client.py` の `TokenUsageTracker` import を `datarobot_genai` へ変更。
- `app_backend/requirements.in` を upstream 形式で追加し、`app_backend/requirements.txt` を compile 生成物として更新。
- `fastapi>=0.115.11,<0.130` にして、`fastapi 0.138` / `starlette 1.3` 系で `_IncludedRouter.path` が存在せず ASGI instrumentation が落ちる問題を避ける。
- `core/src/core/prompts.py` に chart title/text の plain text 制約を追加。

## 検証

- `uv run --project app_backend --all-extras --dev pytest app_backend/tests/test_v1153_backend_compat.py -q`: 13 passed
- `uv run --project app_backend --all-extras --dev pytest app_backend/tests/test_v1153_backend_compat.py app_backend/tests/test_main.py app_backend/tests/test_v1151_fastapi_integration.py -q`: 21 passed, 3 skipped
- `uv run --project app_backend --all-extras --dev pytest app_backend/tests -q`: 107 passed, 3 skipped
- `uv run --project app_backend --all-extras --dev ruff check app_backend/tests/test_v1153_backend_compat.py core/src/core/llm_client.py core/src/core/token_tracking.py`: passed

## 既知事項

- `app_backend/tests` 終了後、LiteLLM の atexit logging が閉じた stream に書こうとする warning が出ることがある。pytest の終了コードは成功しており、本 PR の変更による test failure ではない。
- Python 3.12.11 では `aiohttp.connector` の `enable_cleanup_closed` deprecation warning が 1 件出る。pytest の終了コードは成功。
