"""
Configuration helper for reading environment variables and feature flags
"""

import os
from typing import Any, Dict


def get_feature_flags() -> Dict[str, Any]:
    """
    Get feature flags from environment variables

    Returns:
        Dictionary containing feature flag values
    """
    print("🚀 Loading feature flags from environment variables...")

    feature_flags = {
        "templateEditEnabled": _get_bool_env(
            "VITE_ENABLE_TEMPLATE_EDIT", default=False
        ),
        "customPromptsEnabled": _get_bool_env(
            "VITE_ENABLE_CUSTOM_PROMPTS", default=True
        ),
        # Add more feature flags here as needed
    }
    return feature_flags


def _get_bool_env(env_name: str, default: bool = False) -> bool:
    """
    Get boolean value from environment variable

    Checks for environment variables in the following order:
    1. env_name (e.g., VITE_ENABLE_TEMPLATE_EDIT)
    2. MLOPS_RUNTIME_PARAM_{env_name} (e.g., MLOPS_RUNTIME_PARAM_VITE_ENABLE_TEMPLATE_EDIT)

    Args:
        env_name: Environment variable name
        default: Default value if environment variable is not set

    Returns:
        Boolean value
    """
    print(f"🔍 Checking environment variable: {env_name}")

    # List of possible environment variable names to check
    possible_env_names = [env_name, f"MLOPS_RUNTIME_PARAM_{env_name}"]

    # Check each possible environment variable name
    for candidate_name in possible_env_names:
        env_value = os.getenv(candidate_name)
        if env_value is not None:
            print(f"✅ Found {candidate_name} = '{env_value}'")
            # Convert string to boolean
            result = env_value.lower() in ("true", "1", "yes", "on")
            print(f"📊 Converted to boolean: {result}")
            return result
        else:
            print(f"❌ {candidate_name} not found")

    # No environment variable found, return default
    print(f"🔧 Using default value: {default}")
    return default
