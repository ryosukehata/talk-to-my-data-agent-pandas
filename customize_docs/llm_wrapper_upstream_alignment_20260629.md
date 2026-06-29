# LLM Wrapper Upstream Alignment

## Scope

2026-06-29 に、association_id 取得のための `create_with_completion` は維持したまま、LLM 呼び出し条件を upstream に寄せた。

## Changes

- `core/src/core/api.py` の `create_with_completion` 呼び出しに `timeout=900` を明示した。
- `LLMClientConfig.from_env()` が `core.config.Config` の既定値を fallback として使うようにした。
  - `LLM_DEFAULT_MODEL` が未指定でも upstream と同じ `custom-model` を使う。
  - DataRobot endpoint / token / deployment id も Config 由来の値を利用する。
- LiteLLM adapter は `instructor.from_litellm()` を優先する。
  - 現在の instructor は coroutine function を sync と誤判定する場合があるため、`AsyncInstructor` fallback は維持する。
- `AsyncLLMClient` の OpenAI fallback 経路を削除し、upstream と同じく LiteLLM 経路に一本化した。
- `create_with_completion` の token tracking は、Pydantic response ではなく raw completion を使うようにした。

## Tests

- `app_backend/tests/test_llm_client.py`
  - `create_with_completion` が raw completion を token tracking に渡すこと。
  - Config 既定値から `custom-model` / timeout 900 が解決されること。
  - 空の `LLMClientConfig()` でも OpenAI fallback に落ちず LiteLLM を使うこと。
  - LiteLLM 経路で `from_litellm()` を優先し、必要時のみ async fallback すること。
- `app_backend/tests/test_llm_upstream_alignment.py`
  - `core/src/core/api.py` の `create_with_completion` 呼び出しが `timeout=900` を明示していること。

## Notes

- association_id 取得のため、`create_with_completion` 自体は残す。
- JSON EOF の直接対策ではなく、upstream と異なる LLM wrapper 条件を減らすための PR。
