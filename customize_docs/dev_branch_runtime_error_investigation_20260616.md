# dev ブランチ実行時エラー調査メモ

## 対象ログ

- `AttributeError: 'coroutine' object has no attribute '_raw_response'`
- `RuntimeWarning: coroutine 'acompletion' was never awaited`
- `opentelemetry.context: Failed to detach context`
- `litellm.BadRequestError: LLM Provider NOT provided`
- `litellm.APIConnectionError: DatarobotException - Cannot send a request, as the client has been closed`

## 調査方針

- LLM 呼び出しは `AsyncLLMClient` の LiteLLM 経路を中心に確認する。
- OpenTelemetry は async generator の計測ラッパーが `yield` をまたいで context を保持していないか確認する。
- 再発防止のため、提示されたログに対応する回帰テストを `app_backend/tests` に追加する。

## 原因

### LiteLLM / Instructor

`core.llm_client.AsyncLLMClient` の LiteLLM 経路で `instructor.from_litellm(litellm.acompletion, ...)` を使っていた。
このリポジトリで固定されている `instructor==1.3.4` の `from_litellm()` は `inspect.isawaitable(completion)` で非同期判定するため、coroutine function である `litellm.acompletion` を同期クライアントとして扱ってしまう。

その結果、`create_with_completion()` 内で LiteLLM の coroutine が await されず、coroutine オブジェクトに対して `_raw_response` を読みに行き、以下が発生する。

- `AttributeError: 'coroutine' object has no attribute '_raw_response'`
- `RuntimeWarning: coroutine 'acompletion' was never awaited`

現行の Instructor ドキュメントでは LiteLLM の async 利用は `from_provider(..., async_client=True)` が推奨されているが、固定版 `1.3.4` では既存構成との互換を優先し、`AsyncInstructor` と `instructor.patch(create=litellm.acompletion, ...)` を明示的に組み立てる。

### DataRobot deployed LLM model name

upstream v11.5.1 / v11.8.2 は `LLM_DEFAULT_MODEL` を app runtime parameter に渡し、`core.constants.get_llm_model()` で `datarobot/` provider prefix を補完する。
fork 側の旧 `infra/__main__.py` では app runtime parameter に `LLM_DEFAULT_MODEL` が含まれていなかったため、`TEXTGEN_DEPLOYMENT_ID` / `LLM_DEPLOYMENT_ID` のみがある環境では generic alias の `datarobot-deployed-llm` が LiteLLM にそのまま渡る可能性があった。
LiteLLM の DataRobot provider は provider prefix 付き model 名を routing に使うため、`model=datarobot-deployed-llm` のままだと以下が発生する。

- `litellm.BadRequestError: LLM Provider NOT provided`

### LiteLLM async client lifecycle

upstream v11.5.1 / v11.8.2 は `AsyncLLMClient.__aexit__()` で LiteLLM の async HTTP client を明示 close しない。
fork 側では `close_litellm_async_clients()` を context exit ごとに呼んでいたため、初期分析などで複数の LLM 呼び出しが連続・並行すると、別の LiteLLM リクエストが使う共有 client を先に閉じる可能性があった。
その場合、以下が発生する。

- `litellm.APIConnectionError: DatarobotException - Cannot send a request, as the client has been closed`

### OpenTelemetry

`BaseTelemetry.trace()` の async generator ラッパーが `with tracer.start_as_current_span(...):` を開いたまま `yield` していた。
HTTP streaming やクライアント切断などで async generator が別の asyncio context から close されると、OpenTelemetry の `ContextVar` token を作成元と異なる context で detach し、以下が発生する。

- `opentelemetry.context: Failed to detach context`
- `ValueError: Token was created in a different Context`

## 対応

- `core/src/core/llm_client.py`
  - LiteLLM 経路では `from_litellm()` を使わず、`instructor.AsyncInstructor` を明示構築する。
  - `instructor.patch(create=litellm.acompletion, mode=Mode.MD_JSON)` により、LiteLLM coroutine を await する adapter を使う。
  - `LLM_DEFAULT_MODEL` が未設定の既存環境でも DataRobot deployment alias を `datarobot/datarobot-deployed-llm` に解決する。
  - upstream と同様に、context exit では LiteLLM の共有 async client を閉じない。OpenAI legacy 経路の `AsyncOpenAI.close()` のみ維持する。
- `core/src/core/constants.py`
  - upstream と同様に `get_llm_model()` を追加し、`LLM_DEFAULT_MODEL` または既定 alias に `datarobot/` provider prefix を補完する。
- `infra/__main__.py`
  - 旧 infra 構成でも app runtime parameter に `LLM_DEFAULT_MODEL` を渡す。
- `core/src/core/base_telemetry.py`
  - async generator の span は `tracer.start_span()` で作成する。
  - `trace.use_span(..., end_on_exit=False)` は `__anext__()` 実行中だけ有効にし、`yield` をまたいで OpenTelemetry context を保持しない。
- `core/src/core/api.py`
  - `summarize_conversation()` が upstream v11.5.1 では `client.chat.completions.create(..., timeout=900)` を使うのに対し、fork 側では `create_with_completion()` へ変わっていた。
  - 会話要約の LLM リクエストが成功した直後に tuple を Pydantic model として扱うリスクがあるため、upstream と同じ `create()` 呼び出しへ戻した。

## 追加テスト

- `app_backend/tests/test_llm_client.py`
  - LiteLLM Gateway 経路で `from_litellm()` に戻らないこと。
  - `create_with_completion()` が async adapter 経由で `_raw_response` を取得できること。
  - model 解決、timeout、retry、token 引数変換、DataRobot deployment `api_base` 注入が維持されること。
  - `LLM_DEFAULT_MODEL` 未設定でも deployed LLM alias が provider prefix 付きに正規化されること。
  - LiteLLM 経路の context exit で `close_litellm_async_clients()` に戻らないこと。
  - ローカルの OpenAI 互換 HTTP server を DataRobot deployment に見立て、`AsyncLLMClient` が `/api/v2/deployments/{id}/chat/completions/` に bearer token 付きで POST し、structured response を返せること。
- `app_backend/tests/test_llm_model_constants.py`
  - `get_llm_model()` が upstream と同じ `datarobot/` provider prefix 補完を行うこと。
- `customize_docs/test_llm_runtime_parameters.py`
  - `infra/__main__.py` の app runtime parameter に `LLM_DEFAULT_MODEL` が含まれること。
- `app_backend/tests/test_base_telemetry.py`
  - async generator を別 context で close しても `Failed to detach context` が出ないこと。
- `app_backend/tests/test_api_analysis_execution_v0424_compat.py`
  - `summarize_conversation()` が upstream と同じ `create()` 呼び出しで summary 文字列を返し、`timeout=900` を渡すこと。
  - `core/src/core/api.py` 内の `create_with_completion()` 呼び出しがすべて `(response, raw)` 形式で2値 unpack されること。

## テスト結果

- `uv run pytest app_backend/tests/test_llm_client.py app_backend/tests/test_llm_timeout.py app_backend/tests/test_base_telemetry.py`
  - 14 passed
  - 既存の deprecation warning は今回変更外
- `uv run pytest app_backend/tests/test_api_analysis_execution_v0424_compat.py -q`
  - 11 passed
  - 既存の deprecation warning は今回変更外
- `uv run pytest app_backend/tests/test_llm_client.py app_backend/tests/test_llm_timeout.py app_backend/tests/test_api_analysis_execution_v0424_compat.py -q`
  - 25 passed
  - DataRobot deployment 互換 endpoint への round-trip smoke を含む。
- `uv run pytest app_backend/tests/test_llm_model_constants.py app_backend/tests/test_llm_client.py::test_async_llm_client_deployed_llm_uses_provider_when_default_model_missing customize_docs/test_llm_runtime_parameters.py -q`
  - RED: 5 failed
  - GREEN: 5 passed
- `uv run pytest app_backend/tests/test_llm_client.py app_backend/tests/test_llm_model_constants.py app_backend/tests/test_llm_configuration.py app_backend/tests/test_api_analysis_execution_v0424_compat.py app_backend/tests/test_llm_timeout.py app_backend/tests/test_base_telemetry.py customize_docs/test_llm_runtime_parameters.py -q`
  - 34 passed
- `uv run pytest app_backend/tests/test_llm_client.py::test_async_llm_client_litellm_exit_does_not_close_shared_async_clients -q`
  - RED: `close_litellm_async_clients()` が呼ばれて失敗。
  - GREEN: context exit で LiteLLM の共有 async client を閉じず、1 passed。
- `uv run pytest app_backend/tests customize_docs -q`
  - 108 passed, 2 skipped

## upstream 取り込み時の注意

このリポジトリは基本的に upstream を優先して取り込む方針。今回の 2 点は、現 dev で見つかった実行時エラーの再発確認ポイントとして扱う。ローカル差分を固定的に守る前提にはしない。

- LiteLLM 経路
  - upstream 側で Instructor / LiteLLM の使い方や依存バージョンが更新されている場合は upstream 実装を採用する。
  - 採用後に LiteLLM Gateway 経路のテストを実行し、`_raw_response` エラーや `acompletion` の await 漏れが再発しないことを確認する。
  - 同じエラーが再現した場合のみ、現 dev の `AsyncInstructor` 明示構築のような補正を再検討する。
- OpenTelemetry async generator tracing
  - upstream 側で telemetry wrapper が整理されている場合は upstream 実装を採用する。
  - 採用後に streaming / client disconnect 相当のテストを実行し、`Failed to detach context` が再発しないことを確認する。
  - 同じエラーが再現した場合のみ、`yield` をまたいで OTel context を保持しない補正を再検討する。

upstream 同期PRでは最低限以下を実行する。

- `uv run pytest app_backend/tests/test_llm_client.py::test_async_llm_client_litellm_create_with_completion_uses_async_adapter`
- `uv run pytest app_backend/tests/test_base_telemetry.py::test_trace_async_generator_close_does_not_detach_in_different_context`
