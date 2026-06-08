# v0.5.2 implementation plan

## 目的

upstream `datarobot-community/talk-to-my-data-agent` の `v0.5.2` 差分を、pandas 前提と既存カスタム機能を維持したまま `dev` へ取り込む。

## 前提

- 対象範囲: `v0.5.1..v0.5.2`
- upstream差分: 47 files, 1143 insertions, 280 deletions
- `origin/dev` は内容上 `v0.5.1` 取り込み済みだが、履歴上は `v0.5.1` タグを祖先に持たない。
- Polars 化は pandas に移植しない。
- Streamlit (`frontend/*`) は機能改修対象外。ただし `v0.5.2` の非推奨警告のみ採用する。

## 標準方針

- 一括マージではなく、小さいPRで段階的に取り込む。
- 先に失敗する回帰テストを書き、Red -> Green -> Refactor の順で実装する。
- upstream差分のうち、既存仕様を壊すものは採用しない。
- `utils/customize/*` のクリーンアーキテクチャ構成は変更しない。
- フロントエンドは UI primitive と画面コンポーネントを分けて確認し、既存カスタム画面の表示回帰を防ぐ。

## 採用判断

| 項目 | 判断 | 理由 |
| --- | --- | --- |
| `v0.5.1` baseline merge | 採用 | 以降の merge-base を正常化し、過去に判断済みの差分再衝突を減らす。 |
| frontend UI primitive | 採用 | `v0.5.2` の主差分。既存UIテストを更新して取り込む。 |
| upstream `ThemeProvider` / `app_frontend/src/theme/*` | 採用 | `dev` はすぐ `v0.5.3` へ進めるため、ライトテーマは upstream の theme provider / token 構成へ合わせる。 |
| `DataSourceSelector` tooltip化 | 採用。ただしテスト更新必須 | `v0.5.1` で表示していた説明文が tooltip 内へ移動するため、hover前提のテストへ変更する。 |
| `SettingsModal` checkbox/button variant変更 | 採用 | UI primitive更新に合わせる。既存設定保存の回帰テストを確認する。 |
| `.github/workflows/python-unit-tests.yml` | 部分採用 | upstreamは `pytest tests -q` だが、このリポジトリは `app_backend/tests` と `customize_docs` テストを使う。CIコマンドは現行構成に合わせる。 |
| `pytest.ini` | 部分採用 | `integration` marker は追加する。既存の `pythonpath`, `norecursedirs`, `filterwarnings` は維持する。 |
| `requirements.txt` の `pulumi>=3.153.0` | 採用候補 | 既存CI/quickstartに影響がないことを確認して採用する。 |
| `utils/analyst_db.py` の write connection close/storage修正 | 採用候補 | Polars非依存の安全性改善。失敗時 close をテストで固定してから移植する。 |
| `utils/analyst_db.py` の `pl.DataFrame` 化 | 不採用 | pandas前提維持のため。 |
| `DatasetMetadata.created_at` serializer変更 | 不採用 | 既存テストで UTC `Z` 表記を固定済み。 |
| `frontend/01_connect_and_explore.py` | 部分採用 | legacy Streamlit の機能改修はしないが、`v0.5.2` の非推奨 warning のみ追加する。 |

## 実装結果

2026-06-08 に `v0.5.2` までの差分を一括で実装した。

- UI primitive: `Button`, `Badge`, `Input`, `Label`, `Separator`, `Switch` を更新し、`Checkbox`, `Tooltip`, `Skeleton`, `use-mobile` を追加した。
- 画面統合: `DataSourceSelector` を tooltip 表示へ変更し、`AddDataModal`, `NewChatModal`, `SettingsModal`, data table, `ui-custom` の variant 差分を適用した。
- theme: `ThemeProvider`, `theme/*`, upstream `preset.css` を追加し、`App` / `SettingsModal` / `Toaster` を `useTheme()` に接続した。独自の AppState theme 管理は削除し、upstream と同じ `app-theme` localStorage key を使う。
- backend/infra: `_write_connection()` の例外時 close をテストで固定し、`aiologic.Lock` と v0.5.2 の storage save 順序を採用した。pandas DataFrame 公開挙動と `DatasetMetadata.created_at` の `Z` 表記は維持する。
- CI/docs: `.github/workflows/python-unit-tests.yml`, `pytest.ini`, `requirements.txt`, `CHANGELOG.md`, `README.md`, Streamlit 非推奨 warning を追加/更新した。

検証:

- `npm --prefix app_frontend test`: 17 files / 111 tests passed
- `npm --prefix app_frontend run lint`: passed with existing Fast Refresh warnings in `badge.tsx` / `button.tsx`
- `npm --prefix app_frontend run build`: passed with existing `_dr_env.js`, Browserslist, chunk-size warnings
- `uv run pytest app_backend/tests customize_docs -q`: 59 passed, 2 skipped
- `uv run ruff format --check .`: passed
- `uv run ruff check .`: passed

## PR #75 CI対応

2026-06-08 に PR #75 の CI 失敗へ対応した。

- Ruff format check が `app_backend/tests/test_analyst_db_upstream_compat.py` と `frontend/01_connect_and_explore.py` を未整形として検出したため、`ruff format` を適用した。
- 新規 `python-unit-tests.yml` は frontend build を行わず `pytest app_backend/tests customize_docs -q` を実行する。一方 `app_backend/app/main.py` は `app_backend/static` が存在する前提で `StaticFiles` を無条件 mount していたため、CI の checkout で import 時に失敗していた。
- FastAPI/Starlette の `StaticFiles` は存在する静的ファイルディレクトリを mount する前提のため、`app_backend/static/index.html` が存在する場合だけ SPA routes と static mount を登録する。`/_dr_env.js` は実際の static 可用性を `IS_STATIC_FRONTEND` に返す。
- `app_backend/tests/test_main.py` に static build output の有無を判定する回帰テストを追加し、static なしの CI 状態では SPA/static file テストだけ skip する。

検証:

- `uv run pytest app_backend/tests customize_docs -q`: 59 passed, 2 skipped
- `app_backend/static` を一時退避した CI 再現: 56 passed, 5 skipped
- `uv run ruff format --check .`: passed
- `uv run ruff check .`: passed
- `app_backend` working directory で `uv run ruff format --check .`: passed
- `app_backend` working directory で `uv run ruff check .`: passed

## PR分割

### PR0: `v0.5.1` baseline

目的: 履歴上も `v0.5.1` を取り込み済みにする。

手順:

1. `origin/dev` から `codex/upstream-sync-v0.5.1-baseline` を作成する。
2. `git merge -s ours --no-ff v0.5.1^{commit}` を実行する。
3. 内容差分が出ていないことを確認する。

確認:

- `git merge-base --is-ancestor v0.5.1 HEAD`
- `git diff --stat HEAD^1..HEAD`
- `uv run pytest app_backend/tests customize_docs/test_question_refiner.py customize_docs/test_report_questions_generator.py customize_docs/test_word_generation_llm.py`

完了条件:

- merge commit 以外の実装差分がない。
- `v0.5.1` が `HEAD` の祖先になっている。

### PR1: frontend UI primitive

目的: `v0.5.2` の UI primitive 差分と upstream theme provider / token 構成を取り込む。

対象:

- `app_frontend/components.json`
- `app_frontend/package.json`
- `app_frontend/src/App.tsx`
- `app_frontend/src/theme/*`
- `app_frontend/src/components/ui/*`
- `app_frontend/src/hooks/use-mobile.ts`
- `app_frontend/src/index.css`
- `app_frontend/tests/components/button.test.tsx`
- `app_frontend/tests/components/input.test.tsx`

TDD:

1. `button.test.tsx` / `input.test.tsx` を upstream期待に合わせて先に更新し、現行UI classで失敗することを確認する。
2. `Badge` に clickable badge のテストを追加する。`onClick` がある場合は `button`、ない場合は `div` として描画されることを固定する。
3. `Checkbox` / `Tooltip` の最小レンダリングテストを追加する。
4. UI primitive と theme provider を移植して Green にする。

実装メモ:

- `package-lock.json` は `.gitignore` 対象で Git管理外のため、`package.json` だけ更新する。
- `ThemeProvider` / `theme/*` / `index.css` は upstream `v0.5.3` と同じ構成へ寄せる。独自 AppState theme は削除する。
- `components.json` の `@dr-ui` registry は採用する。ただし外部registryからの自動生成はこのPRでは行わない。

確認:

- `npm --prefix app_frontend test`
- `npm --prefix app_frontend run lint`
- 必要なら `pnpm --dir app_frontend dev` で起動し、Chat / Data / Settings をブラウザ確認する。

完了条件:

- UI primitive テストが通る。
- 既存の custom prompts / report builder / template selector の import が壊れていない。

### PR2: frontend screen integration

目的: `v0.5.2` の画面側差分を既存カスタム機能へ安全に統合する。

対象:

- `app_frontend/src/components/DataSourceSelector.tsx`
- `app_frontend/src/components/SettingsModal.tsx`
- `app_frontend/src/components/AddDataModal.tsx`
- `app_frontend/src/components/data/*`
- `app_frontend/src/components/ui-custom/*`

TDD:

1. `DataSourceSelector.test.tsx` を削除せず、tooltip前提に更新する。
   - 各 data source label が表示されること。
   - `MessageCircleQuestion` 相当の tooltip trigger が4つあること。
   - hover後に upstream説明文が表示されること。
2. `SettingsModal` は checkbox変更後も `collapsiblePanelDefaultOpen` の local state が切り替わることを固定する。
3. `AddDataModal` は data source選択と保存導線が壊れていないことを既存テストまたは新規テストで確認する。

実装メモ:

- `DataSourceSelector.test.tsx` は upstreamでは削除扱いになるが、このリポジトリでは回帰テストとして維持する。
- tooltip化により説明文が常時表示ではなくなるため、UX変更として受け入れるかをPR内で明記する。
- 既存の日本語 i18n key は削除しない。

確認:

- `npm --prefix app_frontend test`
- `npm --prefix app_frontend run lint`
- ブラウザで Add Data modal / Settings modal / Data page を確認する。

完了条件:

- tooltip化後も data source説明文にアクセスできる。
- Settings の保存挙動が変わらない。

### PR3: backend / infra

目的: `v0.5.2` の非Polars backend差分と CI 設定を取り込む。

対象:

- `.github/workflows/python-unit-tests.yml`
- `pytest.ini`
- `requirements.txt`
- `utils/analyst_db.py`
- `app_backend/tests/test_analyst_db_upstream_compat.py`

TDD:

1. `pytest.ini` の既存設定維持を確認する。
   - `pythonpath` に `app_backend` と `.` が残ること。
   - `remote_datasource_concurrency` と `integration` が通常実行から除外されること。
2. `_write_connection()` の失敗時 close をテストで固定する。
   - `duckdb.connect` を fake connection に差し替える。
   - context内で例外を発生させても `close()` が呼ばれること。
3. 成功時に persistent storage save が呼ばれることを固定する。
4. pandas公開挙動を維持する。
   - `AnalystDataset.to_df()` が `pd.DataFrame` を返す。
   - `DatasetMetadata.created_at` は `Z` 表記を維持する。
   - `execute_python` allowed modules に `polars` を追加しない。

実装メモ:

- `utils/analyst_db.py` の `import polars as pl` 差分は採用しない。
- `register_dataframe()` / `get_dataframe()` の `pl.DataFrame` 型変更は採用しない。
- `get_data_source_type()` は現行の `InternalDataSourceType(value)` + `ValueError` 捕捉で Python 3.10/3.11/3.12 互換を維持する。
- `asyncio.Lock` から `aiologic.Lock` への変更は、テストで必要性を確認してから採用する。依存関係自体は既に `requirements.txt` / `app_backend/requirements.txt` に存在する。
- workflowのテストコマンドは upstreamの `pytest tests -q` ではなく、このリポジトリの実行対象に合わせる。

確認:

- `uv run pytest app_backend/tests customize_docs/test_question_refiner.py customize_docs/test_report_questions_generator.py customize_docs/test_word_generation_llm.py`
- `uv run ruff check utils/analyst_db.py`
- 必要なら GitHub Actions の matrix が Python 3.10 / 3.11 / 3.12 で成立するか確認する。

完了条件:

- pandas回帰テストが通る。
- integration marker追加で通常テスト対象が意図せず変わらない。
- CI workflowが存在する場合は、このリポジトリのテストパスを使っている。

## 実装しないもの

- Polars を pandas に移植する作業。
- `utils/api.py` / `utils/data_cleansing_helpers.py` の `v0.5.3` 差分の先行取り込み。
- Streamlit の機能改修。非推奨 warning のみ採用済み。
- `utils -> core/src/core` の構成変更。

## 最終確認

`v0.5.2` 全PRが `dev` に入った後に確認する。

- `git merge-base --is-ancestor v0.5.2 dev`
- `npm --prefix app_frontend test`
- `npm --prefix app_frontend run lint`
- `uv run pytest app_backend/tests customize_docs/test_question_refiner.py customize_docs/test_report_questions_generator.py customize_docs/test_word_generation_llm.py`
- `uv run ruff check utils/analyst_db.py`

## 次フェーズ

`v0.5.2` 完了後に `v0.5.3` を評価する。`v0.5.3` は frontend sidebar刷新が大きく、backend差分は Polars cleansing 前提のため、別計画として扱う。
