# v11.5.1 integration plan

## 目的

upstream `datarobot-community/talk-to-my-data-agent` の `v11.5.1` 差分を、pandas 前提と既存の `utils/customize/` 機能を維持したまま段階的に取り込む。

## 現在地

- 作成ブランチ: `codex/upstream-sync-v11.5.1`
- 起点: `origin/dev` `daadffc` (`v11.5.0` 取り込み済み)
- upstream tag: `v11.5.1` (`deb441d`)
- `v11.5.0` は現在ブランチの祖先。
- `v11.5.0..v11.5.1` の upstream 差分は主要領域だけで 125 files, 23,591 insertions, 15,798 deletions。
- upstream の最新タグは fetch 時点で `v11.8.2`。`v11.5.1` を履歴上の祖先にしておくと、その後の `v11.5.6` / `v11.6.x` / `v11.7.x` / `v11.8.x` へ進みやすい。

## 差分の大枠

| 領域 | upstream v11.5.1 の変更 | 方針 |
| --- | --- | --- |
| `utils` -> `core/src/core` | business logic / runtime helpers を core package へ移動 | 採用する。既存実装の canonical location を `core/src/core` へ移し、`utils.*` は互換 import として維持する。 |
| `utils/customize` -> `core/src/core/customize` | fork 側の custom prompts / report builder / question refiner / template selector を core package 配下へ移動 | 採用する。クリーンアーキテクチャ構成はそのまま移し、`utils.customize.*` は thin compatibility package にする。 |
| FastAPI backend | `app_backend` を thin app にし、core の router / middleware / deps を使う | core 移行後に段階採用。既存 customize router mount と static fallback は回帰テストで固定する。 |
| LLM | af-component-llm / LiteLLM 前提、柔軟な LLM configuration、default model 変更 | 採用候補。既存 `AsyncLLMClient` 利用箇所、token tracking、timeout、customize LLM 生成をテストで固定してから移植する。 |
| Task / CLI | `quickstart.py` から `task deploy` / `task dev` / `dr task compose` へ移行 | 採用候補。既存 quickstart 互換を消すかは別判断。まず Taskfile と CLI state の構文テストを追加する。 |
| Infra | `infra/infra/*`, LLM configuration variants, Pulumi location migration | 採用候補。custom job / report builder / feature flags / file manifest を壊さないように分割する。 |
| Workflows | backend/core/frontend/infra の CI workflow 分割 | 部分採用。現行 CI の `app_backend/tests` と `customize_docs` 実行範囲を維持する。 |
| legacy Streamlit | `frontend/app/*` への再配置 | 原則低優先。React が本線なので、依存 pin や壊れない範囲だけ扱う。 |
| Polars | 過去差分に含まれる Polars 前提の設計 | pandas へ移植しない。`pd.DataFrame` 公開挙動と `polars` 非許可を維持する。 |

## 事前マージ確認

`git merge-tree HEAD v11.5.1` では、以下の衝突が予想される。

- `.env.template`, workflows, `README.md`
- `app_backend/app/__init__.py`, `app_backend/app/main.py`, `app_backend/pyproject.toml`
- `app_frontend/src/components/AddDataModal.tsx`
- `core/src/core/api.py`, `data_cleansing_helpers.py`, `database_implementations.py`, `llm_client.py`, `prompts.py`
- `utils/customize/*` 全体が `core/src/core/customize/*` への file location conflict
- `frontend/*` legacy Streamlit
- `infra/__main__.py`, `infra/settings_app_infra.py`, `infra/settings_generative.py`, `pytest.ini`

そのため、いきなり通常 merge で解消するのではなく、先に移行境界をテストで固定してから小さい PR に分ける。

## 推奨方針

継続的に upstream の次バージョンへ追従するため、`v11.5.1` では core package 化を採用する。ただし既存 fork の外部境界は急に変えない。

- canonical implementation は段階的に `core/src/core` へ寄せる。
- `utils/customize/*` の実装本体は `core/src/core/customize/*` へ移す。
- 既存 import path は `utils.*` / `utils.customize.*` の compatibility shim で残す。
- `customize_docs` と既存 backend tests は当面 `utils.*` import のまま通す。
- 新規テストで `core.*` と `utils.*` が同じ公開オブジェクトを返すことを固定する。
- Polars 実装は pandas へ移植しない。upstream の非Polars bug fix だけ採否判断する。

## `utils/customize` 移行計画

`utils/customize/*` は移す。単に upstream の file location conflict を避けるのではなく、このリポジトリの customize 実装を `core` package の一部として扱う。

### 移動後の構成

```text
core/src/core/customize/
  api.py
  rest_api.py
  custom_prompts.py
  template_manager.py
  domain/
  usecase/
  infrastructure/
  api_endpoints/
  question_refiner/
```

`domain` / `usecase` / `infrastructure` / `api_endpoints` の分離は維持する。これは現在のクリーンアーキテクチャ構成をそのまま package root だけ変える移動にする。

### 互換 layer

`utils/customize` 配下に実装は残さない。代わりに最小限の package shim を残す。

- `utils/customize/__init__.py` は `core.customize` を指す互換入口にする。
- `from utils.customize.domain.report.domain import Report` のような既存 import は通す。
- 新規コードは `from core.customize...` を使う。
- `customize_docs` と既存テストは最初は旧 import のまま残し、互換性を検証する。
- docs / 新規テストでは新 import も併記し、移行完了後に段階的に `core.customize` へ寄せる。

### import 書き換え方針

移動した `core/src/core/customize/*` 内部では、段階的に `core.*` import へ統一する。

PR1 では、移動済みの customize 内 self-import を先に切り替える。

- `from utils.customize...` -> `from core.customize...`

PR2 の core package mechanical migration で、top-level 依存も切り替える。

- `from utils.analyst_db...` -> `from core.analyst_db...`
- `from utils.schema...` -> `from core.schema...`
- `from utils.llm_client...` -> `from core.llm_client...`
- `from utils.logging_helper...` -> `from core.logging_helper...`
- `from utils.persistent_storage...` -> `from core.persistent_storage...`
- `from utils.rest_api...` は router 分割後の location に合わせ、循環 import が出る箇所だけ薄い service/helper に分離する。

### 先に固定するテスト

- `import core.customize.rest_api` が成功する。
- `import core.customize.api_endpoints.report` が成功する。
- `import core.customize.api_endpoints.question_refiner` が成功する。
- `import utils.customize.api_endpoints.report` が成功する。
- `import utils.customize.api_endpoints.question_refiner` が成功する。
- 旧 import と新 import の主要 public class/function が同じ動作をする。
- customize routes が FastAPI app に mount される。
- `customize_docs/test_question_refiner.py`
- `customize_docs/test_report_questions_generator.py`
- `customize_docs/test_word_generation_llm.py`
- `app_backend/tests/test_feature_flag_config.py`
- `app_backend/tests/test_llm_timeout.py`

### ApplicationSource / deployment 反映

`infra/settings_app_infra.py` または移行後の `infra/infra/app_backend.py` で、ApplicationSource に含めるファイル一覧を更新する。

- `core/src/core/customize/**/*.py` を含める。
- `utils/customize/**/*.py` の実装重複を含めない。
- `utils/customize/__init__.py` など shim が必要な場合だけ含める。
- `customize_docs/test_application_source_file_manifest.py` で重複なしを固定する。

### 移行後に残すもの

`utils` package は当面消さない。

- 既存ユーザー、既存テスト、legacy Streamlit、customize docs の import を壊さないため。
- top-level `utils.*` も core 移行後は wrapper / alias として残す。
- 次フェーズで内部 import を `core.*` へ寄せても、外部互換は最後まで維持する。

## PR分割案

### PR0: 計画と現状固定

目的: 取り込み前の挙動とリスクを文書化し、現行 `dev` の健康状態を確認する。

対象:

- `customize_docs/v11_5_1_integration_plan.md`
- `customize_docs/upstream_sync_plan.md`

追加・確認するテスト:

- 既存 regression suite をそのまま実行する。
- `uv run pytest app_backend/tests customize_docs -q`
- `npm --prefix app_frontend test`
- `npm --prefix app_frontend run lint`
- `npm --prefix app_frontend run build`
- `uv run ruff format --check .`
- `uv run ruff check .`

### PR1: customize relocation baseline

目的: `utils/customize/*` を `core/src/core/customize/*` へ移す前に、旧 import と新 import の両方をテストで固定する。

対象:

- `app_backend/tests/test_upstream_compat_imports.py`
- `app_backend/tests/test_v1151_core_import_compat.py` 追加候補

先に追加する失敗テスト:

- `import core.customize.rest_api` が成功する。
- `import core.customize.api_endpoints.report` が成功する。
- `import core.customize.api_endpoints.question_refiner` が成功する。
- `import utils.customize.api_endpoints.report` が成功する。
- `import utils.customize.api_endpoints.question_refiner` が成功する。
- `utils.customize` 経由の feature flags / report domain / question refiner domain が従来どおり使える。

実装方針:

- 先にテストだけ追加して失敗させる。
- その後 `git mv utils/customize core/src/core/customize` を行う。
- `core/src/core/customize/*` 内部 import を `core.*` へ書き換える。
- `utils/customize` は thin compatibility package として残す。

確認:

- `uv run pytest app_backend/tests/test_v1151_core_import_compat.py app_backend/tests/test_feature_flag_config.py app_backend/tests/test_llm_timeout.py -q`
- `uv run pytest customize_docs/test_question_refiner.py customize_docs/test_report_questions_generator.py customize_docs/test_word_generation_llm.py -q`
- `uv run ruff check core/src/core/customize utils/customize`

実装メモ:

- 2026-06-12: `utils/customize/*` の実装本体を `core/src/core/customize/*` へ移動した。
- 旧 `utils.customize.*` は各ファイル単位の shim として残した。通常モジュールは `sys.modules` alias にし、旧 import への monkeypatch が新 canonical module に届くようにした。
- `utils/customize/__init__.py` は eager import しない互換 package にした。`utils.database_helpers -> utils.customize.prompts` の循環 import を避けるため。
- root の `core/__init__.py` で `core/src/core` を package path に追加し、editable install なしでも `core.customize` を import できるようにした。
- ApplicationSource の file manifest に `core/**/*.py` を追加し、`core/src/core/customize/**/*.py` が DataRobot app source に含まれることをテストで固定した。
- `core.customize.domain.report.__all__` から存在しない `ReportCreateRequest` を削除した。移動で package shim の `import *` がこの既存不整合を検出したため。
- PR1 時点では `core.customize` 内の top-level 依存 (`utils.analyst_db`, `utils.schema`, `utils.llm_client` など) は維持する。これらは PR2 の core package mechanical migration で `core.*` へ切り替える。

### PR2: core package mechanical migration

目的: behavior change を最小化して、upstream の `core/src/core` 構成を取り込む。PR1 で移動済みの `core.customize` と統合する。

対象:

- `core/pyproject.toml`
- `core/src/core/*`
- root / backend の dependency / path 設定
- `pytest.ini`

採用:

- upstream の core package 配置。
- `py.typed` と core tests のうち、pandas 方針に反しないもの。

不採用または要調整:

- pandas 公開挙動を Polars へ変える差分。
- `utils.customize` の直接削除。
- custom job / report builder / custom prompts / template selector の import 破壊。

確認:

- `uv run pytest app_backend/tests/test_upstream_compat_imports.py app_backend/tests/test_api_analysis_execution_v0424_compat.py -q`
- `uv run pytest customize_docs/test_question_refiner.py customize_docs/test_report_questions_generator.py customize_docs/test_word_generation_llm.py -q`
- `uv run ruff check core utils app_backend/tests customize_docs`

実装メモ:

- 2026-06-12: top-level `utils/*.py` と `utils/data_connections/**/*.py` の実装本体を `core/src/core/*` へ移動した。
- 旧 `utils.*` は通常モジュールを `sys.modules` alias shim、package `__init__.py` を eager import しない互換 package として残した。
- `core/src/core/**/*.py` 内の import は `core.*` に切り替えた。`openpyxl.utils` のような外部 package 名はそのまま維持した。
- `core.*` と `utils.*` の主要 export が同一 object になることを `app_backend/tests/test_upstream_compat_imports.py` で固定した。
- ApplicationSource manifest は PR1 の `core/**/*.py` 収集で top-level core 実装も同梱される。`core/src/core/rest_api.py` と `utils/rest_api.py` がそれぞれ1件ずつ含まれることをテストで固定した。
- pandas 公開挙動は変更しない。`AnalystDataset.to_df()` と `execute_python` の `polars` 非許可は既存互換テストで確認する。
- 2026-06-15: `utils.i18n` を `core.i18n` shim にした後も locale 資産が旧 `utils/locale` に残っていたため、Pulumi deploy の `LocaleSettings().setup_locale()` が `core/src/core/locale/ja_JP/LC_MESSAGES` 不在で失敗した。`base.po` の canonical location を `core/src/core/locale/ja_JP/LC_MESSAGES/base.po` に移し、ApplicationSource も `core/src/core/locale/.../base.mo` を同梱するよう更新した。

### PR3: FastAPI router / middleware integration

目的: `app_backend` を upstream の thin FastAPI app 構成に近づける。

対象:

- `app_backend/app/__init__.py`
- `app_backend/app/main.py`
- `app_backend/app/config.py`
- `app_backend/app/deps.py`
- `app_backend/app/telemetry/*`
- `core/src/core/rest_api.py`
- `core/src/core/middleware.py`

先に追加・更新するテスト:

- customize routes が引き続き mount される。
- static build output がない checkout でも backend import が失敗しない。
- scoped token / local dev session / Databricks datasource の `v11.5.0` 互換テストが通る。
- chat / dataset / dictionary / database endpoint の既存 backend tests が通る。

確認:

- `uv run pytest app_backend/tests/test_main.py app_backend/tests/test_v1150_compat.py app_backend/tests/test_rest_api_v0424_compat.py -q`
- `uv run pytest app_backend/tests customize_docs -q`

実装メモ:

- 2026-06-12: `core.rest_api.create_app()` を追加し、既存の configured singleton `app` を返す app factory 境界を導入した。
- `app_backend/app/main.py` は `utils.rest_api.app` の直接 import から `core.rest_api.create_app()` 呼び出しへ切り替えた。
- このPRでは router 分割や deps/middleware の本格移植は行わない。customize routes、static frontend fallback、既存 session middleware を保ったまま、後続PRで `app_backend/app/__init__.py` に upstream の thin app 構成を取り込める入口だけ固定する。
- 2026-06-12: static frontend / runtime env script / telemetry setup を `app_backend/app/__init__.py` の `create_app()` に移し、`app_backend/app/main.py` を `from app import create_app; app = create_app()` の thin entrypoint にした。
- 2026-06-12 時点では `create_app()` が既存の `core.rest_api` singleton を再利用し、重複 mount を避けるため app_backend 側でも configured app を cache していた。upstream の deps/lifespan と DataRobot ASGI middleware は、既存 session middleware と conflict しない形を確認してから後続で取り込む前提だった。
- 2026-06-15: `dev` 向けまとめPRの `FastAPI: app_backend` CI は `app_backend/` を cwd として実行するため、entrypoint 構造テストの source file path を `__file__` 起点に変更した。
- 2026-06-15: upstream `v11.5.1` の `Config` / `Deps` / lifespan 初期化を `app_backend/app` に追加した。`create_app(deps=...)` で injected deps を `app.state.deps` に設定できる。
- 2026-06-15: `/health` と DataRobot ASGI middleware 境界を `app_backend/app/__init__.py` に追加した。ローカルの未同期環境でも backend import が失敗しないよう、`datarobot-asgi-middleware` がない場合は警告に留める。
- 2026-06-15: session middleware を `core/src/core/middleware.py` に分離し、`utils.rest_api` / `core.rest_api` からの既存参照は re-export で維持した。upstream の `TEST_USER_EMAIL` 対応を取り込みつつ、`DEV_MODE` 時の `DATAROBOT_API_TOKEN` scoped token 互換は残した。
- 2026-06-15: `core.rest_api.create_app(lifespan=..., title=...)` は fresh FastAPI app を作れるようにし、引数なしでは従来どおり `core.rest_api.app` singleton を返す。backend 側 `create_app()` は lifespan 付き configured app を cache する。
- 2026-06-15: upstream `v11.5.1` の router split は実ファイル上 `core/src/core/routers/*` だが、既存 customize import (`get_initialized_db`, `run_complete_analysis_task`) と backend monkeypatch テストを壊さないため、今回のPRでは既存 monolithic router を factory に載せ替える形で統合した。

### PR4: LLM configuration / LiteLLM integration

目的: upstream `v11.5.1` の柔軟な LLM 設定を、既存 customize LLM と token tracking を壊さず取り込む。

対象:

- `core/src/core/llm_client.py` または互換 `utils/llm_client.py`
- `infra/configurations/llm/*`
- `infra/infra/libllm.py`
- `.datarobot/cli/llm.yml`
- `.env.template`

先に追加・更新するテスト:

- `AsyncLLMClient` が既存の呼び出し interface を維持する。
- question refiner / report question generation / report summary generation が timeout と token tracking を失わない。
- LLM Gateway / deployed LLM / registered model の設定 import が外部接続なしで評価できる。

確認:

- `uv run pytest app_backend/tests/test_llm_client.py app_backend/tests/test_llm_timeout.py -q`
- `uv run pytest customize_docs/test_question_refiner.py customize_docs/test_report_questions_generator.py customize_docs/test_word_generation_llm.py -q`
- `uv run ruff check utils/customize core/src/core infra`

実装メモ:

- 2026-06-15: PR4 用ブランチ `codex/pr4-llm-litellm-integration` を `origin/dev` から作成した。
- 2026-06-15: RED として `app_backend/tests/test_llm_client.py` に `AsyncLLMClient` の既存 OpenAI timeout 互換、LiteLLM Gateway 経路、deployed LLM `api_base` 注入、token tracking 互換テストを追加した。
- 2026-06-15: RED として `app_backend/tests/test_llm_configuration.py` を追加し、`infra.configurations.llm.*` が外部接続なしで import/evaluate できること、`.datarobot/cli/llm.yml` と `.env.template` が upstream v11.5.1 相当の LLM 選択肢を持つことを固定した。
- 2026-06-15: `core/src/core/llm_client.py` に `LLMClientConfig` を追加した。既定では既存の `AsyncOpenAI(timeout=180, max_retries=2)` 経路を維持し、`USE_DATAROBOT_LLM_GATEWAY` / `LLM_DEFAULT_MODEL` / `LLM_DEPLOYMENT_ID` / `TEXTGEN_DEPLOYMENT_ID` がある場合だけ `instructor.from_litellm(litellm.acompletion)` を使う。
- 2026-06-15: LiteLLM 経路では generic model alias (`datarobot-deployed-llm`, `custom-model`) を `LLM_DEFAULT_MODEL` に解決し、既存の `max_tokens` -> `max_completion_tokens` 変換、明示 timeout の尊重、token tracking を維持する。
- 2026-06-15: `infra/configurations/llm/*` は Pulumi resource を作らない import-safe 定義として追加した。実際の resource 統合は PR5 以降で行い、この PR では LLM Gateway / deployed LLM / registered model / external LLM の runtime parameter 定義を評価可能にする。
- 2026-06-15: `instructor[litellm]` と `litellm>=1.72.1` を root / backend dependencies に追加した。`uv lock` は実行したが、このリポジトリの lock file には差分が出なかった。
- 2026-06-26: PR #103 follow-upで、`infra/configurations/llm/*` は upstream `v11.5.3` と同じ Pulumi resource style へ戻した。import-safe helper は削除し、外部接続なしの確認は AST ベースの runtime parameter 契約テストへ置き換えた。

### PR5: Infra / Taskfile / deployment DX

目的: `quickstart.py` 中心から `task dev` / `task deploy` 中心へ寄せる。ただし既存運用を急に壊さない。

対象:

- `Taskfile.yaml`
- `.datarobot/cli/*`
- `infra/Taskfile.yaml`
- `infra/infra/*`
- `infra/Pulumi.yaml`
- `.github/workflows/*`

先に追加・更新するテスト:

- ApplicationSource file manifest に `utils/customize` または互換配置が重複なく含まれる。
- custom job / cleanup job / dashboard / report builder feature flags が Pulumi import で壊れない。
- `task --list --sort none` が成功する。
- workflow が `app_backend/tests customize_docs` を実行する。

確認:

- `uv run pytest customize_docs/test_application_source_file_manifest.py customize_docs/test_pulumi_workflow_refresh.py customize_docs/test_custom_job_schedule_resource.py -q`
- `uv run ruff check infra`
- `task --list --sort none`

実装メモ:

- 2026-06-15: PR5 用ブランチ `codex/pr5-infra-taskfile-deployment-dx` を `origin/dev` から作成した。
- 2026-06-15: RED として `customize_docs/test_taskfile_deployment_dx.py` を追加し、root `Taskfile.yaml` の `infra` include、`deploy` / `deploy-dev`、既存 root `Pulumi.yaml` を使う `infra/Taskfile.yaml`、CLI の `DATABASE_CONNECTION_TYPE` 選択を固定した。
- 2026-06-15: upstream `v11.5.1` の `infra/Pulumi.yaml` / `infra/infra/*` への大移動は、現行 `pulumi-up.yml` と既存 `infra/settings_*` 構成への影響が大きいためこの PR では見送る。代わりに `infra/Taskfile.yaml` の各 Pulumi タスクを `dir: ..` で実行し、既存 root Pulumi project を維持する。
- 2026-06-15: `.datarobot/cli/base.yml` は実際の infra が読む `DATABASE_CONNECTION_TYPE` を選択式にし、既存 use case を使う `DATAROBOT_DEFAULT_USE_CASE` を追加した。Snowflake / BigQuery / SAP の個別設定ブロックは維持する。
- 2026-06-15: workflow と Pulumi optional resource の回帰として、`python-unit-tests.yml` が `app_backend/tests customize_docs` を実行すること、report builder flag / monitoring / cleanup job guard が消えていないことをテストで固定した。

### PR6: React frontend small changes

目的: `v11.5.1` の React 側小差分を取り込み、custom UI を壊していないことを確認する。

対象:

- `app_frontend/src/api/apiClient.ts`
- `app_frontend/src/components/AddDataModal.tsx`
- markdown rendering / summary tab / Vite config / favicon

先に追加・更新するテスト:

- AddDataModal の upload / datasource 表示回帰。
- chat markdown / summary rendering の回帰。
- custom reports / prompts / template selector への導線が残る。

確認:

- `npm --prefix app_frontend test`
- `npm --prefix app_frontend run lint`
- `npm --prefix app_frontend run build`
- 必要なら `pnpm --dir app_frontend dev` で Add Data modal / Chat / Data / Reports をブラウザ確認する。

実装メモ:

- 2026-06-16: PR6 用ブランチ `codex/pr6-react-frontend-small-changes` を最新 `origin/dev` から作成した。
- 2026-06-16: RED として AddDataModal の local upload / database schema-table / remote data connection 表示、Markdown summary rendering、custom reports/prompts/template selector 導線、frontend URL helper の回帰テストを追加した。
- 2026-06-16: `apiClient.ts` の API URL 組み立てを `lib/utils.ts` に集約した。upstream `v11.5.1` の `getApiUrl()` 方針を採用しつつ、既存の `APP_BASE_URL` / `_dr_env.js` / static notebook frontend の `API_PORT` 対応は維持する。
- 2026-06-16: Summary tab の bottom line を `MarkdownContent` で描画するようにし、太字などの markdown 表示を有効にした。plot rendering は既存通り維持する。
- 2026-06-16: upstream との差分に含まれる custom reports / custom prompts / template / refiner の削除は採用しない。既存 customize 導線が残ることを frontend tests で固定する。
- 2026-06-16: Vite config と favicon は現行の `_dr_env.js` proxy / static build / `public/datarobot_favicon.png` 配置を維持する。upstream の `public/assets/datarobot_favicon.png` 追加は現行 `index.html` の参照パスと一致しないため、この PR では採用しない。

### PR7: v11.5.1 history baseline

目的: 内容差分の採用・見送りを記録し、Git 履歴上も `v11.5.1` を処理済みにする。

方針:

- PR1-PR6 で内容を移植した後、残差分を確認する。
- 残差分が意図した見送りだけなら、`git merge -s ours --no-ff v11.5.1^{commit}` で baseline merge を作る。
- もし core 化まで upstream と十分一致しているなら、通常 merge で解消する選択も可能。ただし `utils.customize` の互換 import は必ず残す。

確認:

- `git merge-base --is-ancestor v11.5.1 HEAD`
- `uv run pytest app_backend/tests customize_docs -q`
- `npm --prefix app_frontend test`
- `npm --prefix app_frontend run lint`
- `npm --prefix app_frontend run build`
- `uv run ruff format --check .`
- `uv run ruff check .`

実装メモ:

- 2026-06-16: PR3 相当の FastAPI integration は PR #90 (`codex/v1151-complete-fastapi-integration`) として `codex/v1151-fastapi-app-factory` に merge 済みで、PR #89 により `dev` へ取り込み済みであることを確認した。
- 2026-06-16: PR4 は PR #92、PR5 は PR #93、PR6 は PR #94 として `dev` に merge 済み。残作業は `v11.5.1` を履歴上の祖先にする baseline のみと判断した。
- 2026-06-16: `codex/v1151-history-baseline` を最新 `origin/dev` から作成し、`git merge -s ours --no-ff --no-commit v11.5.1^{commit}` で内容差分なしの history baseline を作成する。
- 2026-06-16: `v11.5.1` に残る差分は、upstream の router split、infra package 大移動、lock file / workflow 再編、Polars 前提差分、legacy Streamlit 寄りの配置など、PR1-PR6 で採用または見送り判断済みの差分として扱う。
- 2026-06-16: 検証は `git merge-base --is-ancestor v11.5.1 HEAD`, `uv run pytest app_backend/tests customize_docs -q` (105 passed, 2 skipped), `npm --prefix app_frontend test` (123 passed), `npm --prefix app_frontend run lint` (0 errors, 15 existing warnings), `npm --prefix app_frontend run build`, `uv run ruff format --check .`, `uv run ruff check .` が成功。

## pandas 維持ルール

- `AnalystDataset.to_df()` は `pd.DataFrame` を返す。
- CSV upload / database select / cleansing / dictionary / analysis execution は pandas 入出力を維持する。
- `execute_python` の allowed modules に `polars` を追加しない。
- upstream の修正が Polars 実装に閉じている場合は移植しない。
- 同じ不具合が現行 pandas 実装にも存在する場合だけ、pandas 実装として TDD で修正する。

## 今後解決する技術課題

v11.5.1 で意図的に残した router split、infra package 移動、workflow / lock 再編、pandas / Polars 境界の再評価は、完了済み integration plan ではなく `customize_docs/upstream_followup_backlog.md` で継続管理する。

## 完了条件

- `v11.5.1` が Git 履歴上の祖先になっている。
- `utils.*` / `utils.customize.*` の既存 import path が壊れていない。
- core package 採用後も pandas 公開挙動が維持されている。
- custom prompts / report builder / template selector / question refiner が backend tests と `customize_docs` tests で守られている。
- frontend build と lint が通る。
- 次の `v11.5.6` 以降へ進むための残差分が `customize_docs/upstream_sync_plan.md` に記録されている。
