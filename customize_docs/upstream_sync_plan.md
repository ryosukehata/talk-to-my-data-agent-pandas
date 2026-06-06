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
| `v0.5.0` 以降 | 未作成 | 別判断 | `v0.4.24` の再編後に積まれた追加差分 | `v0.4.24` の手動移植が完了してから、タグ単位で再評価する。 | 未実行 |

## `v0.4.24` の次アクション

1. `utils/database_helpers.py` と `utils/datarobot_dataset_handler.py` の旧importを保ったまま、新しい data connection 層へ段階移行する。PR1では `utils.data_connections.database.database_implementations` を互換ファサードとして追加し、旧パス・新パスのimport回帰テストを追加する。
2. PR2では `analyst_db.py` の `DatasetMetadata` モデル化と保存時ロックのみを移植する。pandas前提は維持し、upstreamのpandas→polars差分は取り込まない。
3. `utils/api.py` と `utils/rest_api.py` は upstream 版を全面採用せず、既存カスタムAPIのcharacterization testを通しながら必要差分だけ移植する。
4. Streamlit (`frontend/*`) は破棄方針のため、upstream同期では衝突解消せず別途削除・整理する。

## PR2 CI対応メモ

- 2026-06-07: PR2のCIで `tests/test_analyst_db_upstream_compat.py` が失敗。原因はCI環境に `pytest-asyncio` が入っておらず、`@pytest.mark.asyncio` の async test を実行できなかったこと。
- 実装差分ではなくテスト起動方法の問題のため、既存テストと同じく `asyncio.run(...)` で非同期処理を呼び出す同期テストへ変更する。
- 追加でPython 3.11のCIにより、`str in Enum` が `TypeError` になる互換性問題を検出。`get_data_source_type()` は `Enum(value)` 変換と `ValueError` 捕捉に変更し、Python 3.10/3.11/3.12で同じ挙動にする。
- pandas前提の回帰確認は維持する。pandas→polars差分は引き続き取り込まない。
