import ast
import os
from pathlib import Path


def test_default_infra_llm_symlink_uses_deployed_llm_configuration() -> None:
    llm_module_path = Path(__file__).parents[2] / "infra" / "infra" / "llm.py"

    assert llm_module_path.is_symlink()
    assert os.readlink(llm_module_path) == "../configurations/llm/deployed_llm.py"


def test_default_gateway_configuration_does_not_force_max_completion_length() -> None:
    settings_path = (
        Path(__file__).parents[2]
        / "infra"
        / "configurations"
        / "llm"
        / "gateway_direct.py"
    )
    tree = ast.parse(settings_path.read_text())

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute):
            continue

        forced_length = [
            keyword
            for keyword in node.keywords
            if keyword.arg == "max_completion_length"
        ]
        assert forced_length == []
