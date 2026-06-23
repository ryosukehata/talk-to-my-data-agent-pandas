# v11.5.3 React 静的配信 manifest 対応

## 目的

`dev` に v11.5.3 frontend PR が入った後の follow-up として、upstream `v11.5.3` の `TemplateResponse` / Vite manifest ベースの React 配信方式を、この fork の runtime env と SPA deep reload 互換を維持したまま取り込む。

## 標準構成の確認

- FastAPI は API route を優先し、静的frontendは `StaticFiles` や template route で後段に置く構成が標準。
- Vite は `build.manifest=true` により `.vite/manifest.json` を生成し、backend が hash付きentry JS / CSS / import chunk を参照する構成がbackend integrationの標準。

## 採用方針

- `app_frontend/vite.config.ts` は `manifest: true` が既に有効なため維持する。
- `app_backend/templates/index.html` を追加し、manifestから解決したentry JS、CSS、modulepreloadを差し込む。
- `APP_BASE_URL` / `BASE_PATH` / `API_PORT` / `IS_STATIC_FRONTEND` は従来どおり `/_dr_env.js` で渡す。既存frontendの `getBaseUrl()` 契約を変えないため。
- notebook static frontendでは、アセットURLだけ `notebook-sessions/{id}/ports/{PORT}/...` へ正規化する。
- manifestまたはtemplateがない checkout では、従来の generated `static/index.html` fallback と static未生成時のimport safetyを維持する。

## TDD

### RED

- `app_backend/tests/test_main.py`
  - `get_frontend_runtime_env()` が notebook static frontend の `APP_BASE_URL` / `BASE_PATH` / `API_PORT` 契約を返すこと。
  - `get_static_asset_base_url()` が notebook assets にAPI portを含め、通常の `BASE_PATH` はそのまま正規化すること。
  - `get_manifest_assets()` が Vite manifest のentry JS、entry/import CSS、modulepreloadを返すこと。
  - manifestがない場合は空のasset listを返し、fallback可能であること。
  - `get_spa_template_context()` が runtime asset base と manifest assetsをtemplate contextに反映すること。

### GREEN

- `app_backend/app/__init__.py`
  - runtime env生成を `get_frontend_runtime_env()` に集約。
  - Vite manifest readerを追加し、import chunkのCSSとmodulepreloadも重複なく解決。
  - `create_spa_response()` でmanifest/templateが揃う場合は `TemplateResponse`、揃わない場合は従来の `FileResponse(static/index.html)` を返す。
- `app_backend/templates/index.html`
  - `/_dr_env.js`、favicon、CSS、modulepreload、entry JSをtemplate contextから出力。

## 検証結果

- `uv run --project app_backend pytest app_backend/tests/test_main.py -q`: 14 passed
- `uv run --project app_backend pytest app_backend/tests/test_main.py app_backend/tests/test_llm_configuration.py app_backend/tests/test_v1151_fastapi_app_factory.py app_backend/tests/test_v1151_fastapi_integration.py app_backend/tests/test_v1153_backend_compat.py -q`: 41 passed
- `uv run pytest customize_docs -q`: 27 passed, 2 skipped
- `uv run --project app_backend ruff check app_backend/app/__init__.py app_backend/tests/test_main.py app_backend/tests/test_v1153_backend_compat.py core/src/core/config.py core/src/core/customize/usecase/report/__init__.py core/src/core/customize/usecase/report/init_report.py utils/customize/usecase/report/__init__.py customize_docs/test_pulumi_workflow_refresh.py customize_docs/test_taskfile_deployment_dx.py`: passed
