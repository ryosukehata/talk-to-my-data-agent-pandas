import importlib
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).parents[2]


def test_llm_configuration_modules_evaluate_without_external_connections() -> None:
    env = {
        "DATAROBOT_ENDPOINT": "https://app.datarobot.example/api/v2",
        "LLM_DEFAULT_MODEL": "datarobot/bedrock/test-model",
        "TEXTGEN_DEPLOYMENT_ID": "deployment-123",
        "TEXTGEN_REGISTERED_MODEL_ID": "registered-model-123",
    }
    expected_modules = {
        "gateway_direct": {"USE_DATAROBOT_LLM_GATEWAY", "LLM_DEFAULT_MODEL"},
        "deployed_llm": {"LLM_DEPLOYMENT_ID", "LLM_DEFAULT_MODEL"},
        "registered_model": {"LLM_DEPLOYMENT_ID", "LLM_DEFAULT_MODEL"},
        "blueprint_with_llm_gateway": {
            "LLM_DEPLOYMENT_ID",
            "USE_DATAROBOT_LLM_GATEWAY",
            "LLM_DEFAULT_MODEL",
        },
        "blueprint_with_external_llm": {
            "LLM_DEPLOYMENT_ID",
            "LLM_DEFAULT_MODEL",
            "LLM_DEFAULT_MODEL_FRIENDLY_NAME",
        },
    }

    for module_name, expected_app_keys in expected_modules.items():
        module = importlib.import_module(f"infra.configurations.llm.{module_name}")
        definition = module.get_configuration(env)
        app_keys = {parameter.key for parameter in definition.app_runtime_parameters}
        custom_model_keys = {
            parameter.key for parameter in definition.custom_model_runtime_parameters
        }

        assert definition.name
        assert definition.default_model == env["LLM_DEFAULT_MODEL"]
        assert expected_app_keys <= app_keys
        assert "LLM_DEFAULT_MODEL" in custom_model_keys


def test_datarobot_cli_llm_yaml_exposes_upstream_configuration_choices() -> None:
    llm_cli_path = ROOT / ".datarobot" / "cli" / "llm.yml"
    llm_cli = yaml.safe_load(llm_cli_path.read_text())

    root_entries: list[dict[str, Any]] = llm_cli["root"]
    llm_selector = next(
        entry for entry in root_entries if entry.get("env") == "INFRA_ENABLE_LLM"
    )
    option_values = {option["value"] for option in llm_selector["options"]}

    assert llm_selector["default"] == "gateway_direct.py"
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
