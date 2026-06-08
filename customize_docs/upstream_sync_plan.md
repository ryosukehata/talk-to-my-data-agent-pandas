# upstream sync plan

## 目的

`datarobot-community/talk-to-my-data-agent` の upstream 差分を、カスタム機能を壊さないように `dev` へ段階的に取り込む。
一括マージは避け、タグ単位で小さいPRを積む。

## 現在地

- 取り込み元: `upstream/main`
- fetch確認日: 2026-06-04
- upstream最新: `5abdbe1` (`v11.8.1` 後の追加修正を含む)
- `dev` 最新: `c4d6152` (`v0.3.20` から `v0.3.23` まで取り込み済み)
- 現在の `dev` と `v0.4.24` の共通祖先: `v0.3.23`
- 退避ブランチ: `backup/dev-before-upstream-sync-20260604`, `backup/dev-before-v0.4.24-sync-20260604`

## 方針

1. `dev` を起点に、まず `v0.3.20` からタグ単位で取り込む。
2. 競合が軽微な場合はPR内で解消し、判断が必要な競合は作業を止めて確認する。
3. `utils/customize/*` を守るため、各PRで backend の characterization test を実行する。
4. `utils -> core/src/core` の構成変更は、タグ同期PRとは分離して専用PRで移植する。
5. 各段階で「取り込む / 見送る / 手動移植する」をこのファイルへ記録する。

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
| 0 | baseline | `v0.4.24` ours merge または同等の履歴整理 | `CHANGELOG.md`, docs only | `v0.4.24` の未採用差分を再混入させない。 |
| 1 | `v0.5.0` | 取り込む | `DataSourceSelector.tsx`, `CHANGELOG.md`, `README.md` | UI文言改善のみ。polars対象なし。 |
| 2 | `v0.5.1` | 原則取り込むが設定系を確認 | `.datarobot/cli/*`, `Taskfile.yaml`, `quickstart.py`, `README.md` | CLI/Taskfile導入が既存Pulumi/CI/ローカル運用と衝突しないか確認。 |
| 3 | `v0.5.2` | 分割して評価 | frontend theme/ui, `utils/analyst_db.py`, `requirements.txt`, `pytest.ini` | `aiologic.Lock` や DB persist 競合修正は pandas維持で必要部分だけ移植。 |
| 4 | `v0.5.3` | frontend大変更とbackend小修正を分ける | light theme, sidebar/ui registry, chat persistence, `utils/api.py`, `utils/data_cleansing_helpers.py` | UI刷新は既存カスタムUI/Report Builder/Prompt Template と衝突しやすい。data cleansing の polars 変更は取り込まない。 |
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
