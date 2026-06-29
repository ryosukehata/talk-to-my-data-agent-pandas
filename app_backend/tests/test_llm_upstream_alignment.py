import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_core_api_create_with_completion_calls_keep_upstream_timeout() -> None:
    tree = ast.parse((REPO_ROOT / "core/src/core/api.py").read_text())
    missing_timeout_lines: list[int] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute):
            continue
        if func.attr != "create_with_completion":
            continue

        timeout_keyword = next(
            (keyword for keyword in node.keywords if keyword.arg == "timeout"),
            None,
        )
        if not (
            timeout_keyword is not None
            and isinstance(timeout_keyword.value, ast.Constant)
            and timeout_keyword.value.value == 900
        ):
            missing_timeout_lines.append(node.lineno)

    assert missing_timeout_lines == []
