# upstream sync plan

## 目的

`datarobot-community/talk-to-my-data-agent` の upstream 差分を、カスタム機能を壊さないように `dev` へ段階的に取り込む。
一括マージは避け、タグ単位で小さいPRを積む。

## 現在地

- 取り込み元: `upstream/main`
- fetch確認日: 2026-06-08
- upstream次候補: `v0.5.2`
- upstream 0系最新: `v0.5.3`
- upstream最新タグ: `v11.8.1`
- `origin/dev` 最新: `b424579` (`v0.5.1` 取り込みPR #74 merge済み)
- `origin/dev` は内容上 `v0.5.1` 済みだが、履歴上は `v0.5.1` タグを祖先に持たない。
- 退避ブランチ: `backup/dev-before-upstream-sync-20260604`, `backup/dev-before-v0.4.24-sync-20260604`

## 方針

1. `dev` を起点に、タグ単位で小さいPRとして取り込む。
2. 競合が軽微な場合はPR内で解消し、判断が必要な競合は作業を止めて確認する。
3. `utils/customize/*` を守るため、各PRで backend の characterization test を実行する。
4. `utils -> core/src/core` の構成変更は、タグ同期PRとは分離して専用PRで移植する。
5. 各段階で「取り込む / 見送る / 手動移植する」をこのファイルへ記録する。
6. すでに手動移植済みの upstream タグは、内容差分なしの `ours` baseline merge で履歴上も取り込み済みにする。

## upstream 追従時の検証注意点

基本方針は upstream を優先して取り込むこと。以下は「ローカル差分を固定的に維持する」ためのメモではなく、upstream 取り込み時に同種の実行時エラーが再発しないか確認するための注意点。

- `core/src/core/llm_client.py`
  - 現 dev では `instructor==1.3.4` と `litellm.acompletion` の組み合わせで、`AttributeError: 'coroutine' object has no attribute '_raw_response'` / `coroutine 'acompletion' was never awaited` が発生した。
  - upstream 取り込み時は upstream 実装を優先する。upstream 側で Instructor / LiteLLM の使い方や依存バージョンが更新されている場合は、その実装を採用する。
  - 採用後、LiteLLM Gateway 経路の回帰確認として `app_backend/tests/test_llm_client.py::test_async_llm_client_litellm_create_with_completion_uses_async_adapter` または同等の upstream 向けテストを実行する。
  - テストで同じエラーが再現した場合のみ、現 dev の `AsyncInstructor` 明示構築のような補正を再検討する。
- `core/src/core/base_telemetry.py`
  - 現 dev では async generator の tracing で、別 asyncio context から generator が close された場合に `opentelemetry.context: Failed to detach context` が発生した。
  - upstream 取り込み時は upstream 実装を優先する。upstream 側で telemetry wrapper が整理されている場合は、その実装を採用する。
  - 採用後、streaming / client disconnect 相当の回帰確認として `app_backend/tests/test_base_telemetry.py::test_trace_async_generator_close_does_not_detach_in_different_context` または同等の upstream 向けテストを実行する。
  - テストで同じエラーが再現した場合のみ、`yield` をまたいで OpenTelemetry context を保持しない補正を再検討する。

## テスト方針

各同期PRで最低限以下を実行する。

- `uv run pytest app_backend/tests customize_docs/test_question_refiner.py customize_docs/test_report_questions_generator.py customize_docs/test_word_generation_llm.py`

フロントエンドやUI差分があるタグでは追加で以下を実行する。

- `pnpm --dir app_frontend test` または既存のCI相当コマンド
- 必要に応じて `pnpm --dir app_frontend lint`

## 取り込みログ

| タグ | ブランチ | 判断 | 主な差分 | 競合/注意点 | テスト |
| --- | --- | --- | --- | --- | --- |
| `v0.3.20` | `codex/upstream-sync-v0.3.20` | 取り込む | `utils/analyst_db.py`, `utils/api.py`, `utils/datarobot_dataset_handler.py`, `utils/prompts.py` | `CHANGELOG.md` のみ競合。内容を両方残して解消済み。カスタムAPIのcharacterization test追加時に `python-docx` が `app_backend/pyproject.toml` に不足していることを検知し、依存関係を追加。 | `uv run pytest app_backend/tests customize_docs/test_question_refiner.py customize_docs/test_report_questions_generator.py customize_docs/test_word_generation_llm.py`: 16 passed, 2 skipped |
| `v0.3.21` | `codex/upstream-sync-v0.3.21` | 取り込む | `.env.template`, `README.md`, i18n, `utils/api.py`, `utils/rest_api.py`, dataset handling | 実マージでは競合なし。upstream追加の `pytest.ini` が既存 `pyproject.toml` の pytest 設定を上書きし `app` import を壊したため、既存設定を `pytest.ini` に統合。 | `uv run pytest app_backend/tests customize_docs/test_question_refiner.py customize_docs/test_report_questions_generator.py customize_docs/test_word_generation_llm.py`: 16 passed, 2 skipped; `npm --prefix app_frontend test`: 103 passed; `npm --prefix app_frontend run lint`: passed |
| `v0.3.22` | `codex/upstream-sync-v0.3.22` | 取り込む | frontend select UI, `utils/base_telemetry.py` | 実マージでは競合なし。UI差分のためfrontend検証を実施。 | `uv run pytest app_backend/tests customize_docs/test_question_refiner.py customize_docs/test_report_questions_generator.py customize_docs/test_word_generation_llm.py`: 16 passed, 2 skipped; `npm --prefix app_frontend test`: 103 passed; `npm --prefix app_frontend run lint`: passed |
| `v0.3.23` | `codex/upstream-sync-v0.3.23` | 取り込む | `infra/__main__.py`, `requirements.txt`, dataset handling | 実マージでは競合なし。`pulumi-datarobot>=0.10.22` 前提の `app_source.resources` 参照へ変更。ローカル解決で `ApplicationSource.resources` が存在することを確認。 | `uv run pytest app_backend/tests customize_docs/test_question_refiner.py customize_docs/test_report_questions_generator.py customize_docs/test_word_generation_llm.py`: 16 passed, 2 skipped; `uv run ruff check infra/__main__.py utils/datarobot_dataset_handler.py`: passed |
| `v0.4.24` | `codex/upstream-sync-v0.4.24` | 一部取り込む | data connection層の土台、React chat message metadata、依存関係、schema補助差分 | `git merge --no-commit --no-ff v0.4.24` で `frontend/01_connect_and_explore.py`, `frontend/02_chat_with_data.py`, `utils/analyst_db.py`, `utils/api.py`, `utils/data_connections/database/database_implementations.py`, `utils/rest_api.py` が競合。Streamlit は破棄方針のため `frontend/*` 差分は除外。自動適用できた差分から、既存importを壊す `utils/database_helpers.py` 削除、`utils/datarobot_dataset_handler.py` 移動、`notebooks/testing.ipynb` 削除も除外。 | `uv run pytest app_backend/tests customize_docs/test_question_refiner.py customize_docs/test_report_questions_generator.py customize_docs/test_word_generation_llm.py`: 16 passed, 2 skipped; `npm --prefix app_frontend test`: 103 passed; `npm --prefix app_frontend run lint`: passed; `uv run ruff check utils/data_connections utils/schema.py utils/credentials.py infra/settings_app_infra.py`: passed |
| `v0.5.1` | `codex/upstream-sync-v0.5.1` | 取り込む | DataRobot CLI設定、Taskfile、quickstartのstack名省略対応、READMEのCLI quickstart化、DataSourceSelectorの説明文改善 | `v0.4.24` タグは履歴上の祖先ではないため、`v0.4.24..v0.5.1` の差分を手動適用。polars移植なし。upstream READMEの未閉じコードフェンスは本PRで補正する。 | `npm --prefix app_frontend test`: 104 passed; `npm --prefix app_frontend run lint`: passed; `uv run pytest app_backend/tests customize_docs/test_question_refiner.py customize_docs/test_report_questions_generator.py customize_docs/test_word_generation_llm.py`: 43 passed, 2 skipped; `uv run ruff check quickstart.py`: passed; YAML parse + `task --list --sort none`: passed |
| `v11.5.0` | `codex/upstream-sync-v11.5.0` | 取り込む | DataRobot PySDK 3.10対応、scoped token、DataBricks datasource、ApplicationSource admin scope | `v0.5.3` から通常merge。legacy Streamlitは既存fork側を優先し、DataRobot PySDK pinのみ更新。`utils/rest_api.py` は互換import pathを維持。polars移植なし。 | 詳細は `customize_docs/v11_5_0_integration_plan.md` |
| `v11.5.1` | `codex/v1151-history-baseline` | 取り込み済み | `utils` -> `core/src/core` 移行、`utils/customize` -> `core/src/core/customize` 移行、LiteLLM/LLM構成刷新、Taskfile/CLI中心のDX、React小差分、history baseline | `utils.*` / `utils.customize.*` は互換importとして残し、pandas公開挙動を維持。upstream の router split / infra 大移動 / Polars 前提差分は全面採用せず、既存構成に必要な挙動だけ移植。`v11.5.1` は ours merge で履歴上の処理済みにする。router split / infra package 移動 / workflow-lock 再編は `customize_docs/upstream_followup_backlog.md` で継続管理する。 | 詳細は `customize_docs/v11_5_1_integration_plan.md` |
| `v11.5.2` | `codex/upstream-sync-v11.5.2` | 取り込む | CLI dotenv の `DATABASE_CONNECTION_TYPE` default 修正 | `None` 表示の選択肢は残しつつ、書き出し値を infra 標準の `no_database` にする。backend/frontend 挙動変更なし。 | 詳細は `customize_docs/v11_5_2_integration_plan.md` |

## `v0.4.24` の次アクション

1. `utils/database_helpers.py` と `utils/datarobot_dataset_handler.py` の旧importを保ったまま、新しい data connection 層へ段階移行する。PR1では `utils.data_connections.database.database_implementations` を互換ファサードとして追加し、旧パス・新パスのimport回帰テストを追加する。
2. PR2では `analyst_db.py` の `DatasetMetadata` モデル化、保存時ロック、メタデータJSON decode、ログ/例外処理の小差分を移植する。pandas前提は維持し、upstreamのpandas→polars差分は取り込まない。
3. PR3では `utils/rest_api.py` のCSV decode/validationとdatabase endpointのbackground化を移植する。pandas前提は維持し、CSV loaderは `pd.DataFrame` を返す。
4. PR4では `utils/api.py` の分析実行まわりから、`RunCompleteAnalysisRequestContext` と分析step更新 (`GENERATING_QUERY` / `RUNNING_QUERY`) を移植する。pandas前提は維持し、upstreamの `polars` allowed module追加や `pd.DataFrame` 置換は取り込まない。
5. PR5では `utils/api.py` のLLM応答validation/error handling差分を小さく移植する。チャート生成、ビジネス分析、database SQL生成で `ValidationError` をユーザー向けの `AnalysisError` に変換する。
6. PR6では `run_complete_analysis()` のdatabase分析経路で `telemetry_json` を `run_database_analysis()` へ渡す。External Data Store の `data_source` telemetryは `.value` ではなく `.name` を使う。
7. `utils/api.py` と `utils/rest_api.py` の残り差分は upstream 版を全面採用せず、既存カスタムAPIのcharacterization testを通しながら必要差分だけ移植する。
8. Streamlit (`frontend/*`) は破棄方針のため、upstream同期では衝突解消せず別途削除・整理する。

## PR2 CI対応メモ

- 2026-06-07: PR2のCIで `tests/test_analyst_db_upstream_compat.py` が失敗。原因はCI環境に `pytest-asyncio` が入っておらず、`@pytest.mark.asyncio` の async test を実行できなかったこと。
- 実装差分ではなくテスト起動方法の問題のため、既存テストと同じく `asyncio.run(...)` で非同期処理を呼び出す同期テストへ変更する。
- 追加でPython 3.11のCIにより、`str in Enum` が `TypeError` になる互換性問題を検出。`get_data_source_type()` は `Enum(value)` 変換と `ValueError` 捕捉に変更し、Python 3.10/3.11/3.12で同じ挙動にする。
- 2026-06-07: upstream `v0.4.24` の残り小差分から、`_save_to_storage()` 簡略化、`get_dataframe()` debugログ化、`register_dataset()` の `exc_info=True`、`get_data_dictionary()` の `ValueError` 分離を追加移植。`register_dataset()` の成功/失敗dict返却とpandas DataFrame返却は維持する。
- pandas前提の回帰確認は維持する。pandas→polars差分は引き続き取り込まない。

## PR3 実装メモ

- 2026-06-07: `utils/rest_api.py` にCSVのencoding検出、UTF-8 BOM除去、delimiter検出、header-only CSVの検証を追加。upstreamはpolars loaderだが、このリポジトリでは `pd.read_csv` を使い `pd.DataFrame` を返す。
- `/database/select` は選択table名を即時返し、空のpandas datasetを `InternalDataSourceType.DATABASE` として登録してから、実データ取得と cleansing/dictionary 生成をbackground taskへ移す。schema指定は既存仕様を維持する。
- `chardet` は既にrequirementsにあるが、CIのbackend testは `app_backend/pyproject.toml` から `uv sync` するため、同ファイルにも依存を追加する。

## PR4 実装メモ

- 2026-06-07: `utils/api.py` に `RunCompleteAnalysisRequestContext` を追加し、assistant/user message更新を順序付きbackground taskとしてstageできるようにする。保存前に message と step を浅くコピーし、後続のstep変更で先に積んだ更新内容が変わらないようにする。
- ローカル分析の `_run_analysis()` / `run_analysis()` は新しいcontext経由でも呼べるようにし、コード生成前に `GENERATING_QUERY`、Python実行前に `RUNNING_QUERY` を保存する。既存の `analyst_db` / `token_tracker` 引数の呼び出し互換は残す。
- `run_complete_analysis()` はローカル分析経路でcontextを渡す。既存のpandas DataFrame入力、`execute_python` の allowed modules、`AnalystDataset.to_df()` は維持する。
- legacy `utils.database_helpers.DatabaseOperator` に no-op `warmup_query()` / `warmup()` を追加し、upstreamの接続テスト呼び出しに備える。DB実装階層や `utils.data_connections` への全面差し替えはしない。
- 追加テスト: `app_backend/tests/test_api_analysis_execution_v0424_compat.py`。staged updateの順序、`run_analysis` のstep更新、pandas DataFrame維持、no-op warmupを検証する。

## PR5 実装メモ

- 2026-06-07: `utils/api.py` の LLM response parsing failure を個別に扱う。`run_analysis()`、`run_charts()`、`get_business_analysis()`、`_generate_database_analysis_code()` で `ValidationError` を raw のまま返さず、ユーザー向けの `AnalysisError` / `ValueError` へ変換する。
- `get_business_analysis()` は `ValueError` とその他例外も分離し、ユーザーに返すmetadataでは `exception=AnalysisError.from_value_error(...)` を使う。既存の成功レスポンスとpandas DataFrame入力は変更しない。
- `_generate_database_analysis_code()` は LLM応答のvalidation失敗を database SQL生成用の説明メッセージに変換する。SQL sample生成は既存のpandas `.to_df()` 経路を維持する。
- 追加テスト: `app_backend/tests/test_api_validation_errors_v0424_compat.py`。analysis/charts/business/database SQL生成の4経路で raw `ValidationError` が外に出ず、ユーザー向けメッセージに変換されることを検証する。

## PR6 実装メモ

- 2026-06-07: `run_complete_analysis()` のdatabase分析3経路 (`DATABASE`, External Data Store, Remote Registry) から `run_database_analysis()` へ `telemetry_json` が渡ることを回帰テストで固定する。
- Direct database経路は既に `telemetry_json` を渡していたため、External Data Store と Remote Registry の `database_override` 経路に追加する。
- External Data Store は `ExternalDataStoreNameDataSourceType` で `.value` を持たないため、telemetryの `data_source` には `.name` を使う。Internal sourceは従来どおり `.value` を使う。
- 2026-06-08: `run_database_analysis()` の内側も確認し、`_run_database_analysis()` から `_generate_database_analysis_code()` への呼び出しで `database` が余分に1つ渡されていた問題を修正する。`run_database_analysis` / `_run_database_analysis` / `_generate_database_analysis_code` の全呼び出しに `telemetry_json` keyword があることをASTテストで固定する。

## v0.5.x 以降の更新計画

### 確認日

- 2026-06-08
- `git ls-remote --tags --refs upstream 'refs/tags/v*'` で、`v0.4.24` の次は `v0.5.0`、0系の最新は `v0.5.3`。
- `v11.5.0` は upstream CHANGELOG 上で「validated DataRobot platform versions に合わせる」ための採番変更。`v0.5.3` までを先に取り込み、その後 `v11.5.0+` は別フェーズで評価する。

### 履歴上の注意点

- 現在のこちら側の履歴では `v0.4.24` タグ自体は祖先に含まれていない。`v0.4.24` は pandas 前提を維持するために必要差分のみ手動移植している。
- この状態で `git merge v0.5.0` を直接実行すると、`v0.4.24` で見送った polars 化、Streamlit 変更、`utils` 全面置換が再び衝突する。
- `v0.4.24` の全PRが `dev` に入った後、次のどちらかを選ぶ。
  - 推奨: `dev` から `v0.4.24` に対する ours merge ベースラインを1PRで作り、履歴上も「v0.4.24 までは判断済み」とする。その後 `v0.5.0` 以降をタグ単位で通常マージする。
  - 代替: `v0.4.24..v0.5.0` の差分を cherry-pick / patch 移植する。履歴は単純だが、以降のタグでも同じ問題が残るため、継続同期には不向き。

### pandas 維持ルール

- upstream の polars 移植は pandas に再移植しない。
- `utils/api.py`, `utils/rest_api.py`, `utils/analyst_db.py`, `utils/data_cleansing_helpers.py`, `utils/schema.py` の公開挙動は `pd.DataFrame` 前提を維持する。
- upstream の修正が polars 実装に含まれる場合は、挙動だけを pandas 実装へ手動移植する。
- `execute_python` の allowed modules に `polars` を追加しない。既存テスト `test_run_analysis_updates_execution_steps_and_preserves_pandas` の検証を継続する。

### PR分割案

| フェーズ | タグ/範囲 | 取り込み方針 | 主な対象 | 注意点 |
| --- | --- | --- | --- | --- |
| 0 | `v0.5.1` baseline | 先に入れる | Git履歴のみ | `origin/dev` から `git merge -s ours --no-ff v0.5.1^{commit}`。内容差分は出さず、以降の `v0.5.2` merge-base を正常化する。 |
| 1 | `v0.5.2` frontend | 取り込む | theme provider, UI primitives, `DataSourceSelector`, frontend tests | 既存の custom prompt / report builder / template UI と衝突しないか重点確認する。 |
| 2 | `v0.5.2` backend/infra | 一部取り込む | `utils/analyst_db.py`, `requirements.txt`, `pytest.ini`, Python unit workflow | `utils/analyst_db.py` の Polars 型変更は pandas へ移植しない。DB lock/storageなど、現在の pandas 実装に必要な挙動だけ別途判断する。 |
| 3 | `v0.5.3` frontend | 分割して評価 | sidebar刷新, light asset, chat UI, component registry | 変更量が大きいため `v0.5.2` 完了後に専用PRで扱う。 |
| 4 | `v0.5.3` backend | 原則見送り寄り | `utils/api.py`, `utils/data_cleansing_helpers.py` | upstream差分は Polars cleansing 前提。Polars を pandas に移植しないため、明確なバグ修正だけ別PRで採否判断する。 |
| 5 | `v11.5.0+` | 別フェーズ | core package再編、FastAPI router分割、PySDK互換、DataBricks/scoped token | `utils -> core/src/core` の大規模移動は単純マージしない。専用設計PRで判断する。 |

### TDD / テスト方針

- 各PRの最初に、取り込む上流挙動を1つ以上の失敗する回帰テストで固定してから実装する。
- backend 共通テスト:
  - `uv run pytest app_backend/tests customize_docs/test_question_refiner.py customize_docs/test_report_questions_generator.py customize_docs/test_word_generation_llm.py`
- pandas 維持テスト:
  - `app_backend/tests/test_analyst_db_upstream_compat.py`
  - `app_backend/tests/test_rest_api_v0424_compat.py`
  - `app_backend/tests/test_api_analysis_execution_v0424_compat.py`
  - `app_backend/tests/test_api_validation_errors_v0424_compat.py`
- frontend UI差分のあるPR:
  - `npm --prefix app_frontend test`
  - `npm --prefix app_frontend run lint`
  - 必要に応じて `pnpm --dir app_frontend dev` で起動し、ブラウザで Add Data modal / Settings / Chat / Data page を確認する。
- infra/CLI差分のあるPR:
  - `uv run ruff check infra quickstart.py`
  - `task --list` または `task --dry` 相当で Taskfile の構文確認を行う。
  - `.datarobot/cli/state.yaml` などローカル状態ファイルが追跡対象外であることを確認する。

## v0.5.1 実装メモ

- 2026-06-08: `codex/upstream-sync-v0.5.1` を `dev` (`7a0eb57`) から作成。`v0.4.24` は丸ごとマージせず必要差分のみ移植済みのため、`git merge v0.5.1` は使わず `v0.4.24..v0.5.1` の差分を手動適用する。
- `DataSourceSelector` は upstream `v0.5.0` の4つの説明文を表示する。先に `app_frontend/tests/components/DataSourceSelector.test.tsx` を追加し、説明文が未表示で失敗することを確認してから実装した。
- `v0.5.1` の DataRobot CLI quickstart と Taskfile 構成を追加する。`.datarobot/cli/state.yaml` はローカル状態として `.gitignore` に追加する。
- `quickstart.py` は `stack_name` を任意引数にし、未指定時に対話入力する upstream 挙動を移植する。`app_backend/tests/test_quickstart_v051.py` で引数パースを固定する。
- READMEは upstream のCLI優先構成へ更新するが、upstream `v0.5.1` にある未閉じコードフェンスはこのリポジトリ側で補正する。

## v0.5.2 実行プラン

詳細な実装計画は `customize_docs/v0_5_2_implementation_plan.md` を参照する。

### 事前確認

- 2026-06-08: `git ls-remote --refs --tags upstream 'refs/tags/v*'` で、`v0.5.1` の次は `v0.5.2`、0系最新は `v0.5.3`、最新タグは `v11.8.1` と確認した。
- `git merge-base --is-ancestor v0.5.1 origin/dev` は `1`。つまり `v0.5.1` は履歴上まだ `origin/dev` の祖先ではない。
- baseline なしで `v0.5.2` を merge すると、`CHANGELOG.md`, `README.md`, `app_frontend/*`, `frontend/*`, `pytest.ini`, `utils/api.py`, `utils/rest_api.py`, `utils/data_connections/*` まで過去差分が再衝突する。
- 仮想 `v0.5.1` ours baseline 後の `v0.5.2` merge-tree では、主な衝突候補は `app_frontend/package.json`, `app_frontend/src/App.tsx`, `app_frontend/src/components/SettingsModal.tsx`, `frontend/01_connect_and_explore.py`, `pytest.ini`, `utils/analyst_db.py` に縮小する。

### PR0: v0.5.1 baseline

- `origin/dev` から `codex/upstream-sync-v0.5.1-baseline` を作る。
- `git merge -s ours --no-ff v0.5.1^{commit}` で内容差分なしの merge commit を作る。
- 確認:
  - `git merge-base --is-ancestor v0.5.1 HEAD`
  - `git diff --stat HEAD^1..HEAD` が空、またはドキュメント更新のみ
  - `uv run pytest app_backend/tests customize_docs/test_question_refiner.py customize_docs/test_report_questions_generator.py customize_docs/test_word_generation_llm.py`

### PR1: v0.5.2 frontend/UI

- `codex/upstream-sync-v0.5.2-frontend` を baseline 後の `dev` から作る。
- `v0.5.1..v0.5.2` の frontend UI primitive / screen integration 差分を取り込む。
- upstream `ThemeProvider`, `app_frontend/src/theme/*`, `app_frontend/src/index.css` を採用し、ライトテーマは upstream token/preset 構成へ合わせる。
- 対象:
  - `app_frontend/src/App.tsx`
  - `app_frontend/src/index.css`
  - `app_frontend/src/theme/*`
  - `app_frontend/src/components/ui/*`
  - `app_frontend/src/components/DataSourceSelector.tsx`
  - `app_frontend/src/components/SettingsModal.tsx`
  - `app_frontend/package.json`
- 既存のカスタム画面に影響しやすい箇所:
  - custom prompts
  - report builder
  - template selector
  - chat / data source selector
- 先に追加・更新するテスト:
  - `app_frontend/tests/components/button.test.tsx`
  - `app_frontend/tests/components/input.test.tsx`
  - 必要なら `DataSourceSelector` / `SettingsModal` の表示回帰テスト
- 実行テスト:
  - `npm --prefix app_frontend test`
  - `npm --prefix app_frontend run lint`
  - UI差分が大きい場合は `pnpm --dir app_frontend dev` で Add Data modal / Settings / Chat / Data page をブラウザ確認する。

### PR2: v0.5.2 backend/infra

- `codex/upstream-sync-v0.5.2-backend` を PR1 後の `dev` から作る。
- 対象:
  - `.github/workflows/python-unit-tests.yml`
  - `requirements.txt`
  - `pytest.ini`
  - `utils/analyst_db.py`
- Polars 方針:
  - `utils/analyst_db.py` の `pl.DataFrame` 化は pandas に移植しない。
  - `execute_python` の allowed modules に `polars` を追加しない。
  - 現在の pandas `AnalystDataset.to_df()` 公開挙動を維持する。
  - DB write lock / storage save / enum判定など、pandas実装でも必要な非Polars挙動だけをテスト付きで採用する。
- 先に追加・更新するテスト:
  - `app_backend/tests/test_analyst_db_upstream_compat.py`
  - `app_backend/tests/test_api_analysis_execution_v0424_compat.py`
  - 必要なら `pytest.ini` の `pythonpath` / marker 設定が壊れないことを固定する小テスト
- 実行テスト:
  - `uv run pytest app_backend/tests customize_docs/test_question_refiner.py customize_docs/test_report_questions_generator.py customize_docs/test_word_generation_llm.py`
  - `uv run ruff check utils/analyst_db.py`

### PR3以降

- `v0.5.2` が `dev` に入ったら、同じ手順で `v0.5.2` の ours baseline が不要か確認する。通常 merge で `v0.5.2` タグが祖先になっていれば追加baselineは不要。
- 次に `v0.5.3` を frontend と backend に分ける。
- `v0.5.3` の backend差分は `utils/api.py` の cleansing sample size と `utils/data_cleansing_helpers.py` の first-column threshold だが、upstream側は Polars 前提。Polars を pandas に移植しないため、現行pandas実装へ同等ロジックを写す作業は原則しない。
- `v0.5.3` まで完了後、`v11.5.0+` は package再編と router分割を含む別フェーズとして設計レビューから始める。

### v0.5.3 実行プラン

詳細な実装計画は `customize_docs/v0_5_3_integration_plan.md` を参照する。

- 2026-06-08: `codex/v0.5.3-integration-plan` を `origin/dev` (`7e994ec`) から作成。
- `v0.5.2..v0.5.3` の upstream 差分は 64 files, 1810 insertions, 588 deletions。主差分は frontend sidebar / UI registry component / chat persistence / cleansing sample size。
- `main` 向け open PR は #77 (`requests`), #78 (`streamlit`), #79 (`pillow`) を確認済み。v0.5.3 本体PRとは別の dependency rollup PR として巻き込む。
- upstream main 向け open PR は #14 を採用候補、#26 と upstream Dependabot PR は見送り寄りとして記録した。

### v0.5.2 実装メモ

- 2026-06-08: `codex/upstream-sync-v0.5.2-frontend` で `v0.5.2` までの差分を実装。`dev` がすぐ `v0.5.3` へ進む前提に変更されたため、upstream `ThemeProvider` / `theme/*` / `preset.css` も採用し、独自 AppState theme 管理は削除した。
- `DataSourceSelector` は説明文を常時表示から tooltip 表示へ変更し、`app_frontend/tests/components/DataSourceSelector.test.tsx` で hover 後に説明文へアクセスできることを固定した。
- `utils/analyst_db.py` は pandas 公開挙動を維持したまま、`_write_connection()` の例外時 close と storage save 順序を v0.5.2 に合わせた。`pl.DataFrame` 化と `DatasetMetadata.created_at` serializer変更は採用していない。
- `.github/workflows/python-unit-tests.yml` は upstream の `pytest tests -q` ではなく、このリポジトリの `pytest app_backend/tests customize_docs -q` に合わせた。
- `CHANGELOG.md`, `README.md`, `frontend/01_connect_and_explore.py` に v0.5.2 の Streamlit 非推奨案内を追加した。Streamlit の機能改修はしていない。
- PR #75 の CI 対応として、`app_backend/static/index.html` がない checkout では SPA routes と `StaticFiles` mount を登録しないようにした。`python-unit-tests.yml` は frontend build をしないため、API import と customize tests が static build output に依存しないようにする。
- `app_backend/pyproject.toml` に `aiologic` を追加し、`customize_docs` の infra import テストは `PULUMI_STACK_CONTEXT=test-stack` を固定する。
- 検証: `npm --prefix app_frontend test` 111 passed, `npm --prefix app_frontend run lint` passed with Fast Refresh warnings, `npm --prefix app_frontend run build` passed, `uv run pytest app_backend/tests customize_docs -q` 59 passed / 2 skipped, `app_backend/static` 一時退避時 `56 passed / 5 skipped`, `uv run ruff format --check .` passed, `uv run ruff check .` passed, `app_backend` working directory で `uv sync --all-extras --dev` passed, `uv run pytest --cov --cov-report=html --cov-report=term --cov-report xml:.coverage.xml` 44 passed。
