# v11.5.2 integration plan

## 目的

upstream `datarobot-community/talk-to-my-data-agent` の `v11.5.2` 差分を、現行の pandas 前提と既存 infra 構成を変えずに取り込む。

## upstream 差分

- `.datarobot/cli/base.yml`
  - `DATABASE_CONNECTION_TYPE` の default を `None` から `no_database` へ変更。
  - 表示名 `None` の選択肢が `.env` へ `no_database` を書き出すように `value: no_database` を追加。
- `CHANGELOG.md`
  - `v11.5.2` の修正内容を追記。

## 実装方針

- CLI dotenv セットアップの bugfix のみを採用する。
- infra 側は既に `DATABASE_CONNECTION_TYPE=no_database` を標準値として扱っているため、infra 実装は変更しない。
- `v11.5.1` は history baseline で処理済みのため、`CHANGELOG.md` は現行 changelog の先頭へ `v11.5.2` を追記する。

## TDD

- RED: `customize_docs/test_taskfile_deployment_dx.py` で `DATABASE_CONNECTION_TYPE.default == "no_database"` と option value 集合を固定し、既存設定で失敗することを確認した。
- GREEN: `.datarobot/cli/base.yml` を upstream `v11.5.2` 相当に修正する。

## 検証

- `uv run pytest customize_docs/test_taskfile_deployment_dx.py -q`: 3 passed
- `uv run pytest customize_docs -q`: 21 passed, 2 skipped
- `task --list --sort none`: 成功
