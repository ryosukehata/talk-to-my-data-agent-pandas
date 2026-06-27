from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).parents[1]
LLM_CONFIG_DIR = REPO_ROOT / "infra" / "configurations" / "llm"
LLM_CUSTOM_MODEL_MODULES = (
    "blueprint_with_external_llm",
    "blueprint_with_llm_gateway",
    "registered_model",
)


def _module_source(module_name: str) -> str:
    return (LLM_CONFIG_DIR / f"{module_name}.py").read_text()


def test_llm_guardrails_keep_fork_moderation_settings_separate() -> None:
    guardrails_source = (LLM_CONFIG_DIR / "guardrails.py").read_text()

    assert "CustomModelGuardConfigurationArgs" in guardrails_source
    assert 'name="Prompt Tokens"' in guardrails_source
    assert 'template_name="Prompt Tokens"' in guardrails_source
    assert "stages=[Stage.PROMPT]" in guardrails_source
    assert 'name="Response Tokens"' in guardrails_source
    assert 'template_name="Response Tokens"' in guardrails_source
    assert "stages=[Stage.RESPONSE]" in guardrails_source
    assert "llm_guard_configurations = [prompt_tokens, response_tokens]" in guardrails_source


def test_llm_custom_models_import_guardrails_from_fork_module() -> None:
    for module_name in LLM_CUSTOM_MODEL_MODULES:
        source = _module_source(module_name)

        assert "from .guardrails import llm_guard_configurations" in source
        assert "guard_configurations=llm_guard_configurations" in source


def test_only_custom_model_llm_configurations_use_guardrails() -> None:
    for module_name in LLM_CUSTOM_MODEL_MODULES:
        tree = ast.parse(_module_source(module_name))
        custom_model_calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "CustomModel"
        ]

        assert custom_model_calls, module_name
        assert any(
            keyword.arg == "guard_configurations"
            and isinstance(keyword.value, ast.Name)
            and keyword.value.id == "llm_guard_configurations"
            for call in custom_model_calls
            for keyword in call.keywords
        ), module_name
