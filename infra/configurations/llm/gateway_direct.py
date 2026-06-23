from __future__ import annotations

from collections.abc import Mapping

from infra.configurations.llm import (
    DEFAULT_GATEWAY_MODEL,
    REQUIRED_GATEWAY_FEATURE_FLAGS,
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
    default_model = configured_model(resolved_env, DEFAULT_GATEWAY_MODEL)
    runtime_parameters = (
        runtime_parameter("USE_DATAROBOT_LLM_GATEWAY", "1"),
        runtime_parameter("LLM_DEFAULT_MODEL", default_model),
    )
    app_runtime_parameters = (
        *runtime_parameters,
        runtime_parameter(
            "USE_BUILDER_API_TOKEN", configured_builder_api_token(resolved_env)
        ),
    )
    return LLMConfigurationDefinition(
        name="LLM Gateway",
        module_name="gateway_direct.py",
        default_model=default_model,
        app_runtime_parameters=app_runtime_parameters,
        custom_model_runtime_parameters=runtime_parameters,
        required_feature_flags=REQUIRED_GATEWAY_FEATURE_FLAGS,
    )
