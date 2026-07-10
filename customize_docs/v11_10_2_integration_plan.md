# v11.10.2 integration notes

## Scope

`origin/dev` を起点に `upstream/main` (`v11.10.2`) を取り込む。

取り込む:

- `SESSION_SECRET_KEY` runtime parameter
- app backend の session cookie middleware / profiling middleware
- DataRobot CLI `versions.yaml` の install command 追加
- OTel dependency upper bound 緩和と logging / SQLAlchemy instrumentation
- `aiohttp`, `urllib3`, `tornado`, `requests`, `python-multipart`, `cryptography` の CVE 対応
- app backend の Python 3.12 前提化
- root `requirements.txt` の test/runtime 依存を v11.10.2 security baseline に合わせる

維持する:

- pandas 公開挙動
- `core/src/core/customize`
- `core.rest_api` の互換 API factory
- JDBC Preview 経路と旧 database import 互換
- `core/uv.lock` と `docs/.bin/uv.lock` はこの fork の過去方針どおり採用しない

## Implementation decisions

- `app_backend/app/__init__.py` は upstream の `SessionMiddleware` と `PyInstrumentMiddleware` を取り込みつつ、API factory はこの fork の `core.rest_api.create_app` を使い続ける。
- `infra/infra/app_backend.py` は fork 側の `pulumi_datarobot as datarobot` alias と ApplicationSource resource 設定を維持し、`SESSION_SECRET_KEY` credential runtime parameter だけを追加する。
- `core/src/core/data_cleansing_helpers.py` は pandas 実装を維持し、upstream の null count 安定化を pandas の `isna()` に合わせて移植する。
- upstream は native Snowflake 依存を外しているが、この fork は互換 import と旧 operator を残している。`cryptography>=48.0.1,<49.0` は `snowflake-connector-python<4` の `cffi<2` 制約と衝突するため、Snowflake connector を `>=4.5.0,<5.0`、Snowflake SQLAlchemy を `>=1.11.0,<2.0` に上げて解決する。
- frontend は upstream の `axios` security update (`^1.18.1`) を採用する。`axios-retry` はこの fork の `apiClient` で未使用のため追加しない。
- `app_backend/uv.lock` と `infra/uv.lock` は conflict marker を手編集せず、対応する `pyproject.toml` から再生成する。
- root の `uv run pytest` は app_backend project ではなく root `requirements.txt` 由来の環境で app import するため、root requirements も同じ security/profiling 依存へ更新する。
- `PyInstrumentMiddleware` は `PROFILING_ENABLED=true` かつ `profile=1` のリクエスト時だけ `pyinstrument` を要求する。通常起動や root test import では profiling 依存が未同期でも落ちないようにする。
- `TEST_USER_EMAIL` は dev server 専用のローカル開発用値なので、Taskfile の top-level env には置かず `tasks.dev.env` に限定する。これにより `task test` や deployed instance の import path に `TEST_USER_EMAIL` が漏れない。
- app factory tests は upstream の session middleware 初期化に必要な `SESSION_SECRET_KEY` を明示する。
- LLM client の unit test は `Config()` を fake に差し替え、ローカルの `.env` / `pulumi_config.json` にある LLM runtime parameter が upstream default model の検証を上書きしないようにする。実装側は引き続き DataRobot settings fallback を尊重する。
- `pulumi-up.yml` は `SESSION_SECRET_KEY` を GitHub Actions secret から Pulumi env に渡す。secret値はリポジトリに置かず、GitHub Secret `SESSION_SECRET_KEY` として管理する。

## Tests

実施済み:

- `uv run pytest customize_docs/test_v11_10_2_integration.py -q`: 5 passed
- `uv run --project core pytest core/tests/test_v1182_core.py -q`: 21 passed, 3 warnings
- `uv run pytest app_backend/tests/test_v1151_fastapi_integration.py app_backend/tests/test_v1153_backend_compat.py app_backend/tests/test_v1182_compat.py app_backend/tests/test_upstream_compat_imports.py -q`: 37 passed
- `uv run ruff check app_backend/app/__init__.py app_backend/app/config.py app_backend/app/profiling.py app_backend/tests/test_v1151_fastapi_integration.py app_backend/tests/test_v1153_backend_compat.py app_backend/tests/test_v1182_compat.py core/src/core/data_cleansing_helpers.py infra/infra/app_backend.py customize_docs/test_v11_10_2_integration.py`: passed
- `npm --prefix app_frontend test -- src/api/database/api-requests.test.ts`: 1 file / 2 tests passed
- `npm --prefix app_frontend run build`: passed
- `uv run pytest app_backend/tests/test_llm_client.py::test_llm_client_config_uses_upstream_config_defaults app_backend/tests/test_llm_client.py::test_async_llm_client_deployed_llm_uses_config_default_model -q`: 2 passed
- `uv run pytest customize_docs/test_v11_10_2_integration.py app_backend/tests/test_v1151_fastapi_app_factory.py app_backend/tests/test_v1151_fastapi_integration.py app_backend/tests/test_main.py app_backend/tests/test_v1150_compat.py -q`: 24 passed
- `uv run ruff check app_backend/tests/test_llm_client.py app_backend/tests/test_v1151_fastapi_app_factory.py customize_docs/test_v11_10_2_integration.py`: passed
- `task --dir app_backend test`: 160 passed, 1 warning
- `uv run pytest customize_docs/test_v11_10_2_integration.py -q`: 5 passed

補足:

- `npm --prefix app_frontend install --package-lock-only` は Node.js `v24.10.0` に対して `i18next-parser` の engine warning を出したが、lock 更新自体は終了コード 0。
- 初回 backend test で root 環境に `pyinstrument` が未同期だったため `app.profiling` import が失敗した。原因は root `uv run pytest` と app_backend project lock の依存境界差分。`requirements.txt` と `customize_docs/test_v11_10_2_integration.py` に回帰確認を追加し、profiling middleware は optional import にした。
- backend config test はローカル `.env` / DataRobot settings 由来の OTel endpoint/header 補完を受けたため、`otel_sdk_disabled=""` の coercion 確認に必要な OTel fields を明示的に空へ固定した。
- `npm --prefix app_frontend run build` は既存の Browserslist stale data と大きい chunk warning を出したが、終了コードは 0。
- CI failure 調査では、`TEST_USER_EMAIL` が `task test` にも漏れて deployed instance guard に引っかかったこと、app factory tests が `SESSION_SECRET_KEY` を設定していなかったことを確認した。ローカル full backend test では追加で `pulumi_config.json` の LLM fallback による unit test 非決定性も検出し、test isolation を追加した。
- dev merge 後の Pulumi Up failure は `SESSION_SECRET_KEY environment variable is required to deploy app_backend`。workflow env に `SESSION_SECRET_KEY` がなかったため、GitHub Secret が設定されていても Pulumi program に渡らない状態だった。
