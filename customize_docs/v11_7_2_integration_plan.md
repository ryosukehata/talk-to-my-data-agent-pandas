# v11.7.2 integration notes

## Scope

`v11.7.0..v11.7.2` から、pandas公開挙動と既存custom導線を維持できる差分だけを移植する。

取り込む:

- assistant message feedback API / UI
- `message_feedback` 永続テーブル
- dictionary generation failure persistence
- `core:transfer-database` と永続ストレージ転送
- pre-built execution environment hooks
- LLM call span の GenAI semantic attributes
- `ja`, `es_419`, `fr`, `ko`, `pt_BR` のfeedback i18n

維持する:

- `core/src/core/customize`
- custom prompts
- question refiner
- report builder
- template selector
- pandas `AnalystDataset.to_df()` 公開挙動

見送る:

- PR3対象の `v11.8.0..v11.8.2` transfer database hang修正
- upstream のPolars前提差分
- PR2必須ではない broad theme/docs scaffold

## Implementation decisions

- Feedback API は FastAPI の request body 標準に寄せ、`UserFeedbackUpdate` を Pydantic model として path operation parameter にした。`user_rating` は `Literal[-1, 1]` で422 validationに委ねる。
- Feedback は `chat_messages.message` JSON へ埋め込まず、`message_feedback` テーブルで別管理する。message更新では保持し、message/chat削除時に明示削除する。
- Dictionary failure は `dictionary_errors` に保存する。batch単位の部分失敗は placeholder row で継続し、全batch失敗またはdataset単位の失敗だけを永続化する。
- `/v1/dictionaries` は失敗済みdatasetに `in_progress=false` と `error` を返す。これでfrontend pollingが stuck しない。
- `PersistentStorage(global_user=True)` を追加し、`transfer_database` ではsource/target `APPLICATION_ID` を切り替えてアプリ全体のファイルを扱う。
- `transfer_database` は dry-run default、stopped/paused確認、名前解決、衝突保護を入れた。paginationの次ページ取得では追加paramsを渡さない。
- LLM telemetry は OpenTelemetry GenAI semantic conventions の属性名に合わせる。`gen_ai.request.model`, `gen_ai.provider.name`, `gen_ai.system`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens` を best effort で設定し、prompt/completion本文は `LLM_CAPTURE_CONTENT=true` のときだけ設定する。
- FastAPI / OTel 判断の参考:
  - https://fastapi.tiangolo.com/tutorial/body/
  - https://github.com/open-telemetry/semantic-conventions-genai
  - https://opentelemetry.io/docs/specs/semconv/gen-ai/

## TDD notes

REDで追加したテスト:

- `app_backend/tests/test_v1172_compat.py`
  - feedback request validation
  - feedback DB round-trip / update preservation / delete cleanup
  - feedback endpoint 404
  - dictionary error persist / clear / response exposure
  - execution environment script / infra settings
  - LLM GenAI semantic attributes
- `core/tests/scripts/test_transfer_database.py`
  - dry-run
  - pagination
  - stopped/paused validation
  - conflict protection
  - non-dry-run copy
- `app_frontend/tests/api/chat-messages/hooks.test.ts`
  - feedback hook cache update
  - feedback failure toast
- `app_frontend/tests/components/MessageHeader.test.tsx`
  - user message actions remain
  - assistant feedback actions
  - positive feedback payload
  - negative feedback dialog submit
  - dialog close sends `-1`

RED確認:

- `uv run pytest app_backend/tests/test_v1172_compat.py -q`
  - `UserFeedbackUpdate` 未実装で import error
- `uv run --project core pytest core/tests/scripts/test_transfer_database.py -q`
  - `core.scripts` 未実装で import error
- `pnpm --dir app_frontend test ... --run`
  - repoはnpm構成のため、pnpm側のbuild approvalで失敗。実装後はnpmで対象テストを実行する。

GREEN確認:

- `uv run pytest app_backend/tests/test_v1172_compat.py -q`: 9 passed
- `uv run --project core pytest core/tests/scripts/test_transfer_database.py -q`: 4 passed
- `npm --prefix app_frontend test -- tests/api/chat-messages/hooks.test.ts tests/components/MessageHeader.test.tsx`: 30 passed
- `uv run pytest app_backend/tests customize_docs/test_question_refiner.py customize_docs/test_report_questions_generator.py customize_docs/test_word_generation_llm.py`: 123 passed, 2 skipped
- `uv run --project core pytest core/tests`: 5 passed
- `npm --prefix app_frontend test`: 25 files / 159 tests passed
- `npm --prefix app_frontend run lint`: 0 errors, 4 existing warnings
- `task --list --sort none`: passed
- `uv run --project infra ruff check`: passed
- `task infra:unit`: skipped because `infra/tests/units/` does not exist

Infra pytest note:

- `uv run --project infra pytest` still picks up the repository root `pytest.ini`, collects backend/custom tests with the infra venv, and fails on missing backend-only dependencies (`datarobot_asgi_middleware`). This is the same project-level collection issue recorded during v11.6.3.
- Running from `infra/` directly collects 0 tests and exits with pytest code 5. The Taskfile-supported infra unit path handles this by skipping when `tests/units/` is absent.
