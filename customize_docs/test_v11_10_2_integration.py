from __future__ import annotations

import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).parents[1]


def _dependencies(project_path: str) -> set[str]:
    pyproject = tomllib.loads((REPO_ROOT / project_path / "pyproject.toml").read_text())
    return set(pyproject["project"]["dependencies"])


def test_changelog_includes_v11_10_2_release_notes() -> None:
    changelog = (REPO_ROOT / "CHANGELOG.md").read_text()

    assert "## [11.10.2] - 2026-07-09" in changelog
    assert (
        "- Added `SESSION_SECRET_KEY` runtime parameter for app_backend." in changelog
    )
    assert "- Loosened core OTel dependency pins." in changelog
    assert (
        "- Patched HIGH/CRITICAL CVEs in `aiohttp`, `urllib3`, `tornado`, "
        "`requests`, `python-multipart`, and `cryptography`."
    ) in changelog


def test_v11_10_2_dependency_constraints_keep_security_and_snowflake_compat() -> None:
    app_backend_deps = _dependencies("app_backend")
    core_deps = _dependencies("core")
    root_requirements = (REPO_ROOT / "requirements.txt").read_text()

    assert "cryptography>=48.0.1,<49.0" in app_backend_deps
    assert "itsdangerous>=2.2.0" in app_backend_deps
    assert "pyinstrument>=4.6.0" in app_backend_deps

    for dependencies in (app_backend_deps, core_deps):
        assert "requests>=2.33.0,<3.0" in dependencies
        assert "python-multipart>=0.0.31,<1.0" in dependencies
        assert "snowflake-connector-python>=4.5.0,<5.0" in dependencies
        assert "snowflake-sqlalchemy>=1.11.0,<2.0" in dependencies
        assert (
            "opentelemetry-instrumentation-logging>=0.43b0,<2.0.0" in dependencies
            or ("opentelemetry-instrumentation-logging>=0.45b0,<2.0.0" in dependencies)
        )
        assert (
            "opentelemetry-instrumentation-sqlalchemy>=0.43b0,<2.0.0" in dependencies
            or (
                "opentelemetry-instrumentation-sqlalchemy>=0.45b0,<2.0.0"
                in dependencies
            )
        )

    for requirement in (
        "cryptography>=48.0.1,<49.0",
        "pyinstrument>=4.6.0",
        "requests>=2.33.0,<3.0",
        "python-multipart>=0.0.31,<1.0",
        "snowflake-connector-python>=4.5.0,<5.0",
        "snowflake-sqlalchemy>=1.11.0,<2.0",
    ):
        assert requirement in root_requirements


def test_app_backend_targets_python_312_runtime() -> None:
    pyproject = tomllib.loads(
        (REPO_ROOT / "app_backend" / "pyproject.toml").read_text()
    )

    assert pyproject["project"]["requires-python"] == ">=3.12, <3.14"
    assert pyproject["tool"]["ruff"]["target-version"] == "py312"
    assert pyproject["tool"]["mypy"]["python_version"] == "3.12"


def test_session_secret_runtime_parameter_is_declared_for_cli_and_infra() -> None:
    cli_config = (REPO_ROOT / ".datarobot" / "cli" / "app_backend.yaml").read_text()
    infra_source = (REPO_ROOT / "infra" / "infra" / "app_backend.py").read_text()

    assert "env: SESSION_SECRET_KEY" in cli_config
    assert "generate: true" in cli_config
    assert 'key="SESSION_SECRET_KEY"' in infra_source
    assert "datarobot.ApiTokenCredential" in infra_source
    assert "pulumi_datarobot.ApiTokenCredential" not in infra_source
