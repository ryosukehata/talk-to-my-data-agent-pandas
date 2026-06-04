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
| `v0.3.21` | 未作成 | 取り込む候補 | `.env.template`, `README.md`, i18n, `utils/api.py`, `utils/rest_api.py`, dataset handling | 読み取り専用マージでは `CHANGELOG.md` のみ競合。README/env/API差分は確認してからPR化する。 | 未実行 |
| `v0.3.22` | 未作成 | 取り込む候補 | frontend select UI, `utils/base_telemetry.py` | 読み取り専用マージでは `CHANGELOG.md` のみ競合。UI差分のためfrontend検証を追加する。 | 未実行 |
| `v0.3.23` | 未作成 | 取り込む候補 | `infra/__main__.py`, `requirements.txt`, dataset handling | 読み取り専用マージでは `CHANGELOG.md` のみ競合。infra差分はPulumi設定への影響を確認する。 | 未実行 |
| `v0.4.24` 以降 | 未作成 | 別判断 | 大きな構成変更を含む可能性 | `utils -> core/src/core` の移植判断が必要。専用PRで扱う。 | 未実行 |
