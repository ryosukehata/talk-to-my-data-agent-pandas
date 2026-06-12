# v11.5.0 integration plan

## 目的

upstream `datarobot-community/talk-to-my-data-agent` の `v11.5.0` 差分を、既存の pandas 前提と `utils/customize/` 配下のカスタム機能を維持したまま `dev` へ統合する。

## 現在地

- 作成ブランチ: `codex/upstream-sync-v11.5.0`
- 起点: `origin/dev` `f6bb55e`
- upstream tag: `v11.5.0`
- `origin/dev` は `v0.5.3` を履歴上の祖先として含む。
- `v0.5.3..v11.5.0` の upstream 差分は 29 files, 590 insertions, 451 deletions。

## 採用方針

- `v11.5.0` は通常 merge で履歴に取り込む。
- Polars 実装を pandas へ移植しない。
- `utils/customize/` の API / report builder / custom prompts / template selector は維持する。
- `utils.database_helpers` と `utils.datarobot_dataset_handler` の互換 import path は維持する。
- legacy Streamlit `frontend/` は既存 fork 側を優先し、機能差し替えはしない。依存関係の DataRobot PySDK pin だけ `>=3.10.0` に揃える。

## 主な取り込み内容

| 項目 | 判断 | メモ |
| --- | --- | --- |
| DataRobot PySDK `>=3.10.0` | 採用 | root / backend / legacy frontend requirements を揃える。 |
| scoped token | 採用 | `datarobot_api_skoped_token` の誤字系 state を `datarobot_api_scoped_token` へ移行。frontend API 型も更新。 |
| DataBricks datasource | 採用 | `databricks-v1` driver, Databricks SQL prompt, Spark table quoting を追加。 |
| PySDK 3.10 preview API | 採用 | `retrieve_preview` から `get_preview` へ更新し、schema の `dataType` / `data_type` 両方を受ける。 |
| ApplicationSource admin scope | 採用 | `required_key_scope_level="admin"` を追加し、既存の `retain_on_delete=True` も維持。 |
| legacy Streamlit token UI | 見送り | React frontend が本線。既存 fork 実装を壊さないため大きな差し替えは避ける。 |
| Polars 差分 | 見送り | pandas 前提を維持。allowed modules に `polars` を追加しない。 |

## 追加テスト

- `app_backend/tests/test_v1150_compat.py`
  - scoped token helper が session token を優先し、header token に fallback すること。
  - local dev session が `datarobot_api_scoped_token` を使うこと。
  - preview schema が PySDK 3.10 の `data_type` と旧 `dataType` の両方を受けること。
  - `databricks-v1` datasource の prompt / warmup / table formatting が登録されること。
  - `PersistentStorage` が runtime credentials 不足を instance 作成時に検出すること。

## 実行する確認

- `uv run pytest app_backend/tests/test_v1150_compat.py -q`
- `uv run pytest app_backend/tests customize_docs -q`
- `npm --prefix app_frontend test`
- `npm --prefix app_frontend run lint`
- `npm --prefix app_frontend run build`
- `uv run ruff format --check .`
- `uv run ruff check .`

## 実装メモ

- 2026-06-10: `origin/dev` から `codex/upstream-sync-v11.5.0` を作成し、`v11.5.0` を merge した。
- 競合は `app_frontend/src/i18n/locales/ja.json`, legacy Streamlit `frontend/*`, `infra/__main__.py`, `utils/rest_api.py` で発生した。
- `utils/rest_api.py` は互換 import path を維持しつつ `get_visitors_token` を取り込んだ。
- `infra/__main__.py` は upstream の `required_key_scope_level="admin"` と fork 側の `retain_on_delete=True` を両方維持した。
- legacy Streamlit は fork 側を優先し、`frontend/requirements.txt` の DataRobot PySDK だけ `>=3.10.0` に更新した。
