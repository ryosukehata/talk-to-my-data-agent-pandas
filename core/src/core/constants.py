# Copyright 2025 DataRobot, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import os
from typing import Final

DEFAULT_DEPLOYED_LLM_MODEL = "datarobot-deployed-llm"


def _normalize_model_name(raw_model: str) -> str:
    """Add the DataRobot provider prefix expected by LiteLLM."""
    if raw_model.startswith("datarobot/"):
        return raw_model
    return f"datarobot/{raw_model}"


def get_llm_model(preferred_model: str | None = None) -> str:
    """Return the runtime LLM model name using upstream provider-prefix rules."""
    raw_model = (
        preferred_model
        or os.environ.get("LLM_DEFAULT_MODEL")
        or DEFAULT_DEPLOYED_LLM_MODEL
    )
    return _normalize_model_name(raw_model)


# LLM Model Configuration
ALTERNATIVE_LLM_BIG = get_llm_model()
ALTERNATIVE_LLM_SMALL = get_llm_model()
DEFAULT_LLM_GATEWAY_MODEL = "azure/gpt-4o"
DEFAULT_LLM_GATEWAY_MODEL_SMALL = "azure/gpt-4o-mini"

# Dictionary Generation Configuration
DICTIONARY_BATCH_SIZE = 10
DICTIONARY_PARALLEL_BATCH_SIZE = 2
DICTIONARY_TIMEOUT = 45.0

# Dataset Size Limits
MAX_REGISTRY_DATASET_SIZE = 400e6  # 400MB upload size limit
REGISTRY_DATASET_SIZE_CUTOFF: Final[float] = (
    200e6  # at 200MB we move from downloading to analyzing remotely with dataset
)
DISK_CACHE_LIMIT_BYTES = 512e6

# Token and Context Limits
MAX_PROMPT_LENGTH = 4096  # max characters allowed in a single user prompt
MAX_CSV_TOKENS = 50000  # limit for data analyst csv sended to llm
MODEL_CONTEXT_WINDOW = 128000  # GPT-4o context window
CONTEXT_WARNING_THRESHOLD = int(MODEL_CONTEXT_WINDOW * 0.8)

# Tiktoken Encoding Configuration
DEFAULT_TIKTOKEN_ENCODING = "o200k_base"

TIKTOKEN_ENCODING_MAP = {
    ALTERNATIVE_LLM_BIG: DEFAULT_TIKTOKEN_ENCODING,
    ALTERNATIVE_LLM_SMALL: DEFAULT_TIKTOKEN_ENCODING,
    DEFAULT_LLM_GATEWAY_MODEL: DEFAULT_TIKTOKEN_ENCODING,
    DEFAULT_LLM_GATEWAY_MODEL_SMALL: DEFAULT_TIKTOKEN_ENCODING,
}

# Error Messages
VALUE_ERROR_MESSAGE = "Input data cannot be empty (no dataset provided)"
