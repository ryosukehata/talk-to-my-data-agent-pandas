from __future__ import annotations

import ast
import importlib
from pathlib import Path

REPO_ROOT = Path(__file__).parents[1]
LLM_MODULES = (
    "blueprint_with_external_llm",
    "blueprint_with_llm_gateway",
    "deployed_llm",
    "gateway_direct",
    "registered_model",
)


def _keyword_constant(call: ast.Call, name: str) -> str | None:
    for keyword in call.keywords:
        if keyword.arg == name and isinstance(keyword.value, ast.Constant):
            return keyword.value.value if isinstance(keyword.value.value, str) else None
    return None


def test_env_template_documents_builder_token_toggle() -> None:
    env_template = (REPO_ROOT / ".env.template").read_text()

    assert "USE_BUILDER_API_TOKEN=false" in env_template
    assert "app builder's token" in env_template


def test_llm_configurations_pass_builder_token_to_application_runtime() -> None:
    env = {"USE_BUILDER_API_TOKEN": "true"}

    for module_name in LLM_MODULES:
        module = importlib.import_module(f"infra.configurations.llm.{module_name}")
        definition = module.get_configuration(env)
        app_parameters = {
            parameter.key: parameter.value
            for parameter in definition.app_runtime_parameters
        }
        custom_model_keys = {
            parameter.key for parameter in definition.custom_model_runtime_parameters
        }

        assert app_parameters["USE_BUILDER_API_TOKEN"] == "true"
        assert "USE_BUILDER_API_TOKEN" not in custom_model_keys


def test_pulumi_app_runtime_parameters_include_builder_token_toggle() -> None:
    source = (REPO_ROOT / "infra" / "__main__.py").read_text()
    tree = ast.parse(source)

    runtime_parameter_keys = {
        key
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        for key in [_keyword_constant(node, "key")]
        if key is not None
    }

    assert "USE_BUILDER_API_TOKEN" in runtime_parameter_keys


def test_start_script_supports_uv_and_prebuilt_python_environments() -> None:
    start_script = (REPO_ROOT / "app_backend" / "start-app.sh").read_text()

    assert "command -v uv" in start_script
    assert "exec uv run uvicorn" in start_script
    assert "exec python3 -m uvicorn" in start_script
    assert "PYTHONPATH" in start_script


def test_app_source_writes_version_file_for_deployed_runtime() -> None:
    settings_source = (REPO_ROOT / "infra" / "settings_app_infra.py").read_text()
    gitignore = (REPO_ROOT / "app_backend" / ".gitignore").read_text()

    assert "def _write_version_file()" in settings_source
    assert "_write_version_file()" in settings_source
    assert "/VERSION" in gitignore.splitlines()
