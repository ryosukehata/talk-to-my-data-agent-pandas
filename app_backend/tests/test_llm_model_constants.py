from core import constants


def test_get_llm_model_adds_datarobot_provider_prefix() -> None:
    assert (
        constants.get_llm_model("datarobot-deployed-llm")
        == "datarobot/datarobot-deployed-llm"
    )
    assert (
        constants.get_llm_model("bedrock/anthropic.claude-test")
        == "datarobot/bedrock/anthropic.claude-test"
    )


def test_get_llm_model_preserves_existing_datarobot_provider_prefix() -> None:
    assert (
        constants.get_llm_model("datarobot/bedrock/anthropic.claude-test")
        == "datarobot/bedrock/anthropic.claude-test"
    )


def test_get_llm_model_uses_llm_default_model_env(
    monkeypatch,
) -> None:
    monkeypatch.setenv("LLM_DEFAULT_MODEL", "bedrock/anthropic.claude-test")

    assert constants.get_llm_model() == "datarobot/bedrock/anthropic.claude-test"
