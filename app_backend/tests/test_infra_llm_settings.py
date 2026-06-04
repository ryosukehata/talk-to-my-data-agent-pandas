import ast
from pathlib import Path


def test_llm_blueprint_does_not_force_max_completion_length() -> None:
    settings_path = Path(__file__).parents[2] / "infra" / "settings_generative.py"
    tree = ast.parse(settings_path.read_text())

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Name) or node.func.id != "LLMSettings":
            continue

        forced_length = [
            keyword
            for keyword in node.keywords
            if keyword.arg == "max_completion_length"
        ]
        assert forced_length == []
