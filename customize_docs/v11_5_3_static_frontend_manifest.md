# v11.5.3 React 静的配信 manifest 対応

## 目的

`dev` に v11.5.3 frontend PR が入った後の follow-up として、upstream `v11.5.3` の `TemplateResponse` / Vite manifest ベースの React 配信方式へ backend entrypoint を戻す。今後の upstream 更新を基準にしやすくするため、fork 側の static frontend 互換ロジックは `app_backend/app/__init__.py` から外す。

## 標準構成の確認

- FastAPI は API route を優先し、静的frontendは `StaticFiles` や template route で後段に置く構成が標準。
- Vite は `build.manifest=true` により `.vite/manifest.json` を生成し、backend が hash付きentry JS / CSS / import chunk を参照する構成がbackend integrationの標準。

## 採用方針

- `app_backend/app/__init__.py`、`app_backend/templates/index.html`、`app_backend/tests/test_main.py` は upstream `v11.5.3` と一致させる。
- runtime env は upstream と同じく template 内の `window.ENV = {{ env | tojson }}` で渡す。
- notebook static frontend の base path は upstream と同じ `get_app_base_url(api_port)` に集約し、`BASE_PATH` に `/notebook-sessions/{id}/ports/{PORT}/` を入れる。
- fork 固有差分は backend本体ではなくテスト補助へ閉じ込める。`app_backend/tests/conftest.py` だけ monorepo の `core` import 用に `sys.path` を補助し、env-before-import は `noqa: E402` で明示する。

## TDD

### RED

- `app_backend/tests/test_main.py`
  - upstream と同じく `/`、`/assets/datarobot_favicon.png`、`/health` が通ること。
- `app_backend/tests/test_v1151_fastapi_app_factory.py`
  - upstream `v11.5.3` の `create_app()` は同一インスタンスを返す契約ではないため、factory公開とroute構成を確認する。

### GREEN

- `app_backend/app/__init__.py`
  - upstream `v11.5.3` と同一内容へ戻す。
- `app_backend/templates/index.html`
  - upstream `v11.5.3` と同一内容へ戻す。
- `app_backend/tests/conftest.py`
  - upstream fixtureを復帰し、monorepo checkoutで `app` と `core` をimportできるよう `sys.path` 補助だけ追加する。

## 検証結果

- `npm install`: passed
- `npm run build` in `app_frontend`: passed
- `uv run --project app_backend pytest app_backend/tests/test_main.py -q`: 3 passed
- `uv run --project app_backend pytest app_backend/tests/test_main.py app_backend/tests/test_v1151_fastapi_app_factory.py app_backend/tests/test_v1151_fastapi_integration.py app_backend/tests/test_v1153_backend_compat.py -q`: 27 passed
- `uv run --project app_backend ruff check app_backend/app/__init__.py app_backend/tests/test_main.py app_backend/tests/conftest.py app_backend/tests/test_v1151_fastapi_app_factory.py`: passed
