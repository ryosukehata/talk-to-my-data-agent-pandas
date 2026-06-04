# upstream sync plan

## 目的

`datarobot-community/talk-to-my-data-agent` の upstream 差分を、カスタム機能を壊さないように `dev` へ段階的に取り込む。
一括マージは避け、タグ単位で小さいPRを積む。

## 現在地

- 取り込み元: `upstream/main`
- fetch確認日: 2026-06-04
- upstream最新: `5abdbe1` (`v11.8.1` 後の追加修正を含む)
- 現在の `dev` との共通祖先: `v0.3.19`
- 退避ブランチ: `backup/dev-before-upstream-sync-20260604`

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
| `v0.4.24` 以降 | 未作成 | 別判断 | data connection層の再編、frontend/Streamlit、API、schema変更 | `v0.4.24` の読み取り専用マージで `frontend/01_connect_and_explore.py`, `frontend/02_chat_with_data.py`, `utils/analyst_db.py`, `utils/api.py`, `utils/data_connections/database/database_implementations.py`, `utils/rest_api.py` が競合。`utils/database_helpers.py -> utils/data_connections/database/database_implementations.py`, `utils/datarobot_dataset_handler.py -> utils/data_connections/datarobot/datarobot_dataset_handler.py` の移動を含むため、専用PRで扱う。 | 未実行 |
