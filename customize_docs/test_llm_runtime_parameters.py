from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).parents[1]


def _keyword_constant(call: ast.Call, name: str) -> str | None:
    for keyword in call.keywords:
        if keyword.arg == name and isinstance(keyword.value, ast.Constant):
            return keyword.value.value if isinstance(keyword.value.value, str) else None
    return None


def test_app_runtime_parameters_include_llm_default_model() -> None:
    app_backend_source = (REPO_ROOT / "infra" / "infra" / "app_backend.py").read_text()
    assert "llm_app_runtime_parameters" in app_backend_source

    deployed_llm_source = (
        REPO_ROOT / "infra" / "configurations" / "llm" / "deployed_llm.py"
    ).read_text()
    tree = ast.parse(deployed_llm_source)

    runtime_parameter_keys = {
        key
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        for key in [_keyword_constant(node, "key")]
        if key is not None
    }

    assert "LLM_DEFAULT_MODEL" in runtime_parameter_keys
