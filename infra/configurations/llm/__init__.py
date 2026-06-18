"""Import-safe LLM configuration definitions.

These modules describe DataRobot LLM integration choices without creating
Pulumi resources or opening DataRobot/LiteLLM connections at import time.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field

DEFAULT_GATEWAY_MODEL = "datarobot/bedrock/anthropic.claude-sonnet-4-5-20250929-v1:0"
DEFAULT_DEPLOYED_MODEL = "datarobot/datarobot-deployed-llm"
DEFAULT_EXTERNAL_MODEL = "bedrock/anthropic.claude-sonnet-4-5-20250929-v1:0"
DEFAULT_EXTERNAL_LLM_ID = "amazon-anthropic-claude-sonnet-4-5-20250929-v1"
DEFAULT_EXTERNAL_LLM_NAME = "Claude Sonnet 4.5"
DEFAULT_USE_BUILDER_API_TOKEN = "false"

REQUIRED_LLM_FEATURE_FLAGS: dict[str, bool] = {
    "ENABLE_MLOPS": True,
    "ENABLE_CUSTOM_INFERENCE_MODEL": True,
    "ENABLE_PUBLIC_NETWORK_ACCESS_FOR_ALL_CUSTOM_MODELS": True,
    "ENABLE_MLOPS_TEXT_GENERATION_TARGET_TYPE": True,
}

REQUIRED_GATEWAY_FEATURE_FLAGS: dict[str, bool] = {
    **REQUIRED_LLM_FEATURE_FLAGS,
    "ENABLE_MLOPS_RESOURCE_REQUEST_BUNDLES": True,
}


@dataclass(frozen=True)
class RuntimeParameterDefinition:
    key: str
    type: str = "string"
    value: str | None = None


@dataclass(frozen=True)
class LLMConfigurationDefinition:
    name: str
    module_name: str
    default_model: str
    app_runtime_parameters: tuple[RuntimeParameterDefinition, ...]
    custom_model_runtime_parameters: tuple[RuntimeParameterDefinition, ...]
    required_env_vars: tuple[str, ...] = ()
    required_feature_flags: Mapping[str, bool] = field(default_factory=dict)


def resolve_env(env: Mapping[str, str] | None = None) -> Mapping[str, str]:
    return os.environ if env is None else env


def runtime_parameter(
    key: str,
    value: str | None = None,
    type: str = "string",
) -> RuntimeParameterDefinition:
    return RuntimeParameterDefinition(key=key, type=type, value=value)


def configured_model(env: Mapping[str, str], default: str) -> str:
    return env.get("LLM_DEFAULT_MODEL") or default


def configured_builder_api_token(env: Mapping[str, str]) -> str:
    return env.get("USE_BUILDER_API_TOKEN") or DEFAULT_USE_BUILDER_API_TOKEN
