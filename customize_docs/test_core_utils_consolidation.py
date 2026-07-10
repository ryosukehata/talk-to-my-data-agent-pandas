from __future__ import annotations

import ast
import configparser
from pathlib import Path

REPO_ROOT = Path(__file__).parents[1]

RUNTIME_SOURCE_ROOTS = [
    REPO_ROOT / "app_backend" / "app",
    REPO_ROOT / "core" / "src" / "core",
    REPO_ROOT / "infra" / "infra",
]

NON_COMPAT_TEST_ROOTS = [
    REPO_ROOT / "app_backend" / "tests",
    REPO_ROOT / "customize_docs",
]

LEGACY_IMPORT_ALLOWED_TESTS = {
    Path("app_backend/tests/test_analyst_db_upstream_compat.py"),
    Path("app_backend/tests/test_api_analysis_execution_v0424_compat.py"),
    Path("app_backend/tests/test_api_validation_errors_v0424_compat.py"),
    Path("app_backend/tests/test_data_cleansing_v053_compat.py"),
    Path("app_backend/tests/test_rest_api_v0424_compat.py"),
    Path("app_backend/tests/test_schema_pandas_compat.py"),
    Path("app_backend/tests/test_upstream_compat_imports.py"),
    Path("app_backend/tests/test_v1150_compat.py"),
    Path("app_backend/tests/test_v1151_core_customize_imports.py"),
    Path("app_backend/tests/test_v1151_fastapi_app_factory.py"),
    Path("app_backend/tests/test_v1153_backend_compat.py"),
}


def _python_files(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*.py")
        if "__pycache__" not in path.parts
        and ".venv" not in path.parts
        and path.is_file()
    )


def _imports_legacy_utils(path: Path) -> bool:
    tree = ast.parse(path.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(
                alias.name == "utils" or alias.name.startswith("utils.")
                for alias in node.names
            ):
                return True
        elif isinstance(node, ast.ImportFrom):
            if node.module == "utils" or (node.module or "").startswith("utils."):
                return True
    return False


def test_runtime_code_uses_core_not_legacy_utils() -> None:
    offenders = [
        path.relative_to(REPO_ROOT).as_posix()
        for root in RUNTIME_SOURCE_ROOTS
        for path in _python_files(root)
        if _imports_legacy_utils(path)
    ]

    assert offenders == []


def test_non_compat_tests_use_core_not_legacy_utils() -> None:
    offenders = []
    for root in NON_COMPAT_TEST_ROOTS:
        for path in _python_files(root):
            relative_path = path.relative_to(REPO_ROOT)
            if relative_path in LEGACY_IMPORT_ALLOWED_TESTS:
                continue
            if _imports_legacy_utils(path):
                offenders.append(relative_path.as_posix())

    assert offenders == []


def test_legacy_utils_package_contains_only_core_shims() -> None:
    offenders = []
    for path in _python_files(REPO_ROOT / "utils"):
        source = path.read_text()
        stripped_source = source.strip()
        is_empty_or_marker = stripped_source == "" or stripped_source.startswith(
            '"""Compatibility package for ``core.'
        )
        is_module_alias = (
            "import_module(" in source
            and '"core.' in source
            and "sys.modules[__name__] = _module" in source
        )
        is_star_alias = "from core." in source and "import *" in source
        is_lazy_alias = (
            "__getattr__" in source
            and "from core.customize.usecase import report as core_report" in source
        )

        if not (is_empty_or_marker or is_module_alias or is_star_alias or is_lazy_alias):
            offenders.append(path.relative_to(REPO_ROOT).as_posix())

    assert offenders == []


def test_core_customize_is_documented_as_canonical_location() -> None:
    agents = (REPO_ROOT / "AGENTS.md").read_text()
    utils_readme = (REPO_ROOT / "utils" / "README.md").read_text()

    assert "core/src/core/customize/" in agents
    assert "domain logic under `utils/customize/`" not in agents
    assert "Compatibility shims" in utils_readme
    assert "core/src/core" in utils_readme


def test_root_pytest_does_not_collect_core_project_tests() -> None:
    config = configparser.ConfigParser()
    config.read(REPO_ROOT / "pytest.ini")

    ignored_directories = set(config["pytest"]["norecursedirs"].split())

    assert "core" in ignored_directories
