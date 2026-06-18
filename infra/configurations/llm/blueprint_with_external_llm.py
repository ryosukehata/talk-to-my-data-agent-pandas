from __future__ import annotations

from collections.abc import Mapping

from infra.configurations.llm import (
    DEFAULT_EXTERNAL_LLM_ID,
    DEFAULT_EXTERNAL_LLM_NAME,
    DEFAULT_EXTERNAL_MODEL,
    REQUIRED_LLM_FEATURE_FLAGS,
    LLMConfigurationDefinition,
    configured_builder_api_token,
    configured_model,
    resolve_env,
    runtime_parameter,
)


def get_configuration(
    env: Mapping[str, str] | None = None,
) -> LLMConfigurationDefinition:
    resolved_env = resolve_env(env)
    default_model = configured_model(resolved_env, DEFAULT_EXTERNAL_MODEL)
    deployment_id = resolved_env.get("LLM_DEPLOYMENT_ID") or "${LLM_DEPLOYMENT_ID}"
    app_runtime_parameters = (
        runtime_parameter("LLM_DEPLOYMENT_ID", deployment_id),
        runtime_parameter("LLM_DEFAULT_MODEL", default_model),
        runtime_parameter(
            "LLM_DEFAULT_LLM_ID",
            resolved_env.get("LLM_DEFAULT_LLM_ID") or DEFAULT_EXTERNAL_LLM_ID,
        ),
        runtime_parameter(
            "LLM_DEFAULT_MODEL_FRIENDLY_NAME",
            resolved_env.get("LLM_DEFAULT_LLM_NAME") or DEFAULT_EXTERNAL_LLM_NAME,
        ),
        runtime_parameter("USE_BUILDER_API_TOKEN", configured_builder_api_token(resolved_env)),
    )
    custom_model_runtime_parameters = (
        runtime_parameter("LLM_DEPLOYMENT_ID", deployment_id),
        runtime_parameter("LLM_DEFAULT_MODEL", default_model),
    )
    return LLMConfigurationDefinition(
        name="External LLM",
        module_name="blueprint_with_external_llm.py",
        default_model=default_model,
        app_runtime_parameters=app_runtime_parameters,
        custom_model_runtime_parameters=custom_model_runtime_parameters,
        required_feature_flags=REQUIRED_LLM_FEATURE_FLAGS,
    )
