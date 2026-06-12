"""
LLM timeout configuration for customize services.
"""

from __future__ import annotations

import os

from core.logging_helper import get_logger

logger = get_logger(__name__)

DEFAULT_LLM_TIMEOUT_SECONDS = 60.0
SHARED_LLM_TIMEOUT_ENV = "CUSTOMIZE_LLM_TIMEOUT_SECONDS"


def get_llm_timeout_seconds(*specific_env_names: str) -> float:
    """Return a positive timeout in seconds for LLM calls."""
    for env_name in (*specific_env_names, SHARED_LLM_TIMEOUT_ENV):
        raw_value = os.getenv(env_name)
        if raw_value is None:
            continue

        try:
            timeout_seconds = float(raw_value)
        except ValueError:
            logger.warning(
                "Invalid %s=%r; using default %.0f seconds",
                env_name,
                raw_value,
                DEFAULT_LLM_TIMEOUT_SECONDS,
            )
            return DEFAULT_LLM_TIMEOUT_SECONDS

        if timeout_seconds <= 0:
            logger.warning(
                "Invalid %s=%r; timeout must be positive. Using default %.0f seconds",
                env_name,
                raw_value,
                DEFAULT_LLM_TIMEOUT_SECONDS,
            )
            return DEFAULT_LLM_TIMEOUT_SECONDS

        return timeout_seconds

    return DEFAULT_LLM_TIMEOUT_SECONDS
