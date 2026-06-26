from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).parents[1]
LLM_CONFIG_DIR = REPO_ROOT / "infra" / "configurations" / "llm"
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


def _runtime_parameter_calls(module_name: str, args_class_name: str) -> list[ast.Call]:
    source = (LLM_CONFIG_DIR / f"{module_name}.py").read_text()
    tree = ast.parse(source)

    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == args_class_name
    ]


def test_env_template_documents_builder_token_toggle() -> None:
    env_template = (REPO_ROOT / ".env.template").read_text()

    assert "USE_BUILDER_API_TOKEN=false" in env_template
    assert "app builder's token" in env_template


def test_llm_configurations_pass_builder_token_to_application_runtime() -> None:
    for module_name in LLM_MODULES:
        app_parameters = {
            _keyword_constant(call, "key"): call
            for call in _runtime_parameter_calls(
                module_name, "ApplicationSourceRuntimeParameterValueArgs"
            )
        }
        custom_model_keys = {
            _keyword_constant(call, "key")
            for call in _runtime_parameter_calls(
                module_name, "CustomModelRuntimeParameterValueArgs"
            )
        }

        assert "USE_BUILDER_API_TOKEN" in app_parameters
        assert "USE_BUILDER_API_TOKEN" not in custom_model_keys


def test_pulumi_app_runtime_parameters_include_builder_token_toggle() -> None:
    source = (REPO_ROOT / "infra" / "infra" / "app_backend.py").read_text()

    assert "llm_app_runtime_parameters" in source
    assert "*list(llm_app_runtime_parameters)" in source


def test_app_source_accepts_existing_app_environment_pulumi_output() -> None:
    source = (REPO_ROOT / "infra" / "infra" / "app_backend.py").read_text()

    assert "base_environment_id: pulumi.Input[str]" in source
    assert "app_backend_app_source_args: dict[str, pulumi.Input[str]]" in source
    assert "app_backend_app_source_args = ApplicationSourceArgs" not in source


def test_custom_application_waits_for_application_source() -> None:
    source = (REPO_ROOT / "infra" / "infra" / "app_backend.py").read_text()

    assert (
        "required_key_scope_level=app_backend_app_source.required_key_scope_level"
        in source
    )
    assert "opts=pulumi.ResourceOptions(depends_on=[app_backend_app_source])" in source


def test_start_script_supports_uv_and_prebuilt_python_environments() -> None:
    start_script = (REPO_ROOT / "app_backend" / "start-app.sh").read_text()

    assert "command -v uv" in start_script
    assert "exec uv run uvicorn" in start_script
    assert "exec python3 -m uvicorn" in start_script
    assert "PYTHONPATH" in start_script


def test_app_source_writes_version_file_for_deployed_runtime() -> None:
    settings_source = (REPO_ROOT / "infra" / "infra" / "app_backend.py").read_text()
    gitignore = (REPO_ROOT / "app_backend" / ".gitignore").read_text()

    assert "def _write_version_file()" in settings_source
    assert "_write_version_file()" in settings_source
    assert "/VERSION" in gitignore.splitlines()


def test_infra_directory_uses_upstream_split_layout() -> None:
    expected_paths = [
        "Pulumi.yaml",
        "__main__.py",
        "configurations/README.md",
        "configurations/llm/gateway_direct.py",
        "feature_flags/README.md",
        "feature_flags/feature_flag_requirements.yaml",
        "infra/__init__.py",
        "infra/app_backend.py",
        "infra/app_frontend.py",
        "infra/components/dr_credential.py",
        "infra/libllm.py",
        "infra/llm.py",
    ]
    legacy_paths = [
        "__init__.py",
        "app_frontend.py",
        "components/dr_credential.py",
        "configurations/__init__.py",
        "feature_flag_requirements.yaml",
        "feature_flag_requirements_llm_gateway.yaml",
        "feature_flag_requirements_on_prem.yaml",
        "settings_app_infra.py",
        "settings_database.py",
        "settings_generative.py",
        "settings_job_infra.py",
        "settings_main.py",
        "settings_proxy_llm.py",
    ]

    for path in expected_paths:
        assert (REPO_ROOT / "infra" / path).exists(), path
    for path in legacy_paths:
        assert not (REPO_ROOT / "infra" / path).exists(), path
    assert (REPO_ROOT / "infra" / "infra" / "llm.py").is_symlink()
