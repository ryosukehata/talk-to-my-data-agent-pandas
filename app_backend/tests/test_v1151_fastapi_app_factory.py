import ast
from pathlib import Path

import pytest

APP_MAIN_PATH = Path(__file__).resolve().parents[1] / "app" / "main.py"


def _set_required_import_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATAROBOT_API_TOKEN", "test-token")
    monkeypatch.setenv("DATAROBOT_ENDPOINT", "https://example.com")
    monkeypatch.setenv("OTEL_SDK_DISABLED", "true")


def test_core_rest_api_exposes_app_factory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_required_import_env(monkeypatch)

    from core import rest_api

    created_app = rest_api.create_app()

    assert created_app is rest_api.app
    assert any(
        getattr(route, "path", "") == "/api/v1/config/feature-flags"
        for route in created_app.routes
    )


def test_backend_main_starts_from_core_app_factory() -> None:
    tree = ast.parse(APP_MAIN_PATH.read_text(encoding="utf-8"))

    imported_from_app_package = False
    imported_from_legacy_utils = False
    imported_from_core = False
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        imported_names = {alias.name for alias in node.names}
        if node.module == "app" and "create_app" in imported_names:
            imported_from_app_package = True
        if node.module == "core.rest_api" and "create_app" in imported_names:
            imported_from_core = True
        if node.module == "utils.rest_api":
            imported_from_legacy_utils = True

    assert imported_from_app_package
    assert not imported_from_core
    assert not imported_from_legacy_utils


def test_backend_main_is_thin_factory_entrypoint() -> None:
    tree = ast.parse(APP_MAIN_PATH.read_text(encoding="utf-8"))

    top_level_definitions = [
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef)
    ]
    app_assignments = [
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "app"
            for target in node.targets
        )
    ]

    assert top_level_definitions == []
    assert len(app_assignments) == 1
    assert isinstance(app_assignments[0].value, ast.Call)
    assert isinstance(app_assignments[0].value.func, ast.Name)
    assert app_assignments[0].value.func.id == "create_app"


def test_backend_package_exposes_app_factory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_required_import_env(monkeypatch)

    from core.rest_api import app as core_app

    from app import create_app

    assert create_app() is core_app


def test_backend_main_app_uses_core_factory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_required_import_env(monkeypatch)

    from app import create_app, main

    assert main.app is create_app()
