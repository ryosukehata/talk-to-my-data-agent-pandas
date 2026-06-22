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
- chart prompt に、title/axis/annotation は plain text のみという制約を追加。

## 見送り

- dependency / lock file 更新は infra PR で扱う。
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
  - seat license 403 が `ApplicationUsageException` になること。
  - ValueError wrapped 404 が `RecipeError` になること。
  - token counting fallback が heuristic strategy であること。

### GREEN

- `app_backend/app/__init__.py` に `get_app_version()` と runtime env `APP_VERSION` を追加。
- `app_backend/app/telemetry/*` に `ReadableFormatter` を追加し、default config を `readable` に変更。
- `core/src/core/config.py` を追加し、upstream と同じ `use_builder_api_token` setting を持たせる。
- `core/src/core/datarobot_client.py` に builder token fallback と empty use case handling を追加。
- `core/src/core/data_connections/datarobot/helpers.py` に wrapped ClientError / seat license 403 handling を追加。
- `core/src/core/api.py` / `core/src/core/rest_api.py` の DataRobot user-token context で builder token fallback を許可。
- `core/src/core/token_tracking.py` に `HeuristicTokenCountingStrategy` を追加し、default fallback と message counting を heuristic に変更。
- `core/src/core/prompts.py` に chart title/text の plain text 制約を追加。

## 検証

- `uv run pytest app_backend/tests/test_v1153_backend_compat.py -q`: 10 passed
- `uv run pytest app_backend/tests/test_v1153_backend_compat.py app_backend/tests/test_main.py app_backend/tests/test_v1151_fastapi_integration.py -q`: 19 passed, 3 skipped
- `uv run pytest app_backend/tests -q`: 104 passed, 3 skipped

## 既知事項

- `app_backend/tests` 終了後、LiteLLM の atexit logging が閉じた stream に書こうとする warning が出ることがある。pytest の終了コードは成功しており、本 PR の変更による test failure ではない。
