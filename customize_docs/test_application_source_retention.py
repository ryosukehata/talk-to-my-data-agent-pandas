from __future__ import annotations

import ast
from pathlib import Path


def _application_source_assignments(tree: ast.AST) -> dict[str, ast.Call]:
    assignments: dict[str, ast.Call] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            continue
        if not isinstance(node.value, ast.Call):
            continue
        if not isinstance(node.value.func, ast.Attribute):
            continue
        if node.value.func.attr != "ApplicationSource":
            continue
        assignments[node.targets[0].id] = node.value
    return assignments


def _has_retain_on_delete_true(call: ast.Call) -> bool:
    opts_keyword = next(
        (keyword for keyword in call.keywords if keyword.arg == "opts"),
        None,
    )
    if opts_keyword is None or not isinstance(opts_keyword.value, ast.Call):
        return False
    if not isinstance(opts_keyword.value.func, ast.Attribute):
        return False
    if opts_keyword.value.func.attr != "ResourceOptions":
        return False

    retain_keyword = next(
        (
            keyword
            for keyword in opts_keyword.value.keywords
            if keyword.arg == "retain_on_delete"
        ),
        None,
    )
    return (
        retain_keyword is not None
        and isinstance(retain_keyword.value, ast.Constant)
        and retain_keyword.value.value is True
    )


def test_application_sources_are_retained_on_delete() -> None:
    infra_main = Path(__file__).parents[1] / "infra" / "__main__.py"
    tree = ast.parse(infra_main.read_text())

    assignments = _application_source_assignments(tree)

    assert set(assignments) >= {"app_source", "dashboard_source"}
    assert _has_retain_on_delete_true(assignments["app_source"])
    assert _has_retain_on_delete_true(assignments["dashboard_source"])
