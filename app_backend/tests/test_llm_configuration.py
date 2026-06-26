import ast
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).parents[2]
LLM_CONFIG_DIR = ROOT / "infra" / "configurations" / "llm"


def _runtime_parameter_keys(module_name: str, args_class_name: str) -> set[str]:
    source = (LLM_CONFIG_DIR / f"{module_name}.py").read_text()
    tree = ast.parse(source)
    keys: set[str] = set()

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != args_class_name:
            continue
        for keyword in node.keywords:
            if keyword.arg == "key" and isinstance(keyword.value, ast.Constant):
                keys.add(keyword.value.value)

    return keys


def test_llm_configuration_modules_match_upstream_runtime_contracts() -> None:
    expected_modules = {
        "gateway_direct": {
            "app": {
                "USE_DATAROBOT_LLM_GATEWAY",
                "LLM_DEFAULT_MODEL",
                "USE_BUILDER_API_TOKEN",
            },
            "custom": {"USE_DATAROBOT_LLM_GATEWAY", "LLM_DEFAULT_MODEL"},
        },
        "deployed_llm": {
            "app": {
                "LLM_DEPLOYMENT_ID",
                "LLM_DEFAULT_MODEL",
                "LLM_DEFAULT_MODEL_FRIENDLY_NAME",
                "USE_BUILDER_API_TOKEN",
            },
            "custom": {"LLM_DEPLOYMENT_ID", "LLM_DEFAULT_MODEL"},
        },
        "registered_model": {
            "app": {
                "LLM_DEPLOYMENT_ID",
                "LLM_DEFAULT_MODEL",
                "LLM_DEFAULT_MODEL_FRIENDLY_NAME",
                "USE_BUILDER_API_TOKEN",
            },
            "custom": {"LLM_DEPLOYMENT_ID", "LLM_DEFAULT_MODEL"},
        },
        "blueprint_with_llm_gateway": {
            "app": {
                "LLM_DEPLOYMENT_ID",
                "USE_DATAROBOT_LLM_GATEWAY",
                "LLM_DEFAULT_MODEL",
                "USE_BUILDER_API_TOKEN",
            },
            "custom": {"LLM_DEPLOYMENT_ID", "LLM_DEFAULT_MODEL"},
        },
        "blueprint_with_external_llm": {
            "app": {
                "LLM_DEPLOYMENT_ID",
                "LLM_DEFAULT_MODEL",
                "LLM_default_llm_friendly_name",
                "USE_BUILDER_API_TOKEN",
            },
            "custom": {"LLM_DEPLOYMENT_ID", "LLM_DEFAULT_MODEL"},
        },
    }

    for module_name, expected_keys in expected_modules.items():
        app_keys = _runtime_parameter_keys(
            module_name, "ApplicationSourceRuntimeParameterValueArgs"
        )
        custom_model_keys = _runtime_parameter_keys(
            module_name, "CustomModelRuntimeParameterValueArgs"
        )

        assert app_keys == expected_keys["app"]
        assert custom_model_keys == expected_keys["custom"]


def test_llm_configuration_modules_use_upstream_pulumi_shape() -> None:
    for module_path in LLM_CONFIG_DIR.glob("*.py"):
        source = module_path.read_text()

        assert "get_configuration" not in source
        assert "LLMConfigurationDefinition" not in source
        assert "datarobot.ApplicationSourceRuntimeParameterValueArgs" in source


def test_datarobot_cli_llm_yaml_exposes_upstream_configuration_choices() -> None:
    llm_cli_path = ROOT / ".datarobot" / "cli" / "llm.yml"
    llm_cli = yaml.safe_load(llm_cli_path.read_text())

    root_entries: list[dict[str, Any]] = llm_cli["root"]
    llm_selector = next(
        entry for entry in root_entries if entry.get("env") == "INFRA_ENABLE_LLM"
    )
    option_values = {option["value"] for option in llm_selector["options"]}

    assert llm_selector["default"] == "deployed_llm.py"
    assert {
        "gateway_direct.py",
        "deployed_llm.py",
        "registered_model.py",
        "blueprint_with_llm_gateway.py",
        "blueprint_with_external_llm.py",
    } <= option_values
    assert "deployed_llm" in llm_cli
    assert "registered_model" in llm_cli
    assert "external_llm" in llm_cli


def test_env_template_documents_flexible_llm_configuration() -> None:
    env_template = (ROOT / ".env.template").read_text()

    for expected in (
        "INFRA_ENABLE_LLM=",
        "LLM_DEFAULT_MODEL=",
        "LLM_DEFAULT_LLM_ID=",
        "LLM_DEFAULT_LLM_NAME=",
        "TEXTGEN_DEPLOYMENT_ID=",
        "TEXTGEN_REGISTERED_MODEL_ID=",
        "USE_DATAROBOT_LLM_GATEWAY=",
    ):
        assert expected in env_template
