from __future__ import annotations

import tomllib
from pathlib import Path

import yaml

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
    env_template = (REPO_ROOT / ".env.template").read_text()
    infra_source = (REPO_ROOT / "infra" / "infra" / "app_backend.py").read_text()
    pulumi_workflow = yaml.safe_load(
        (REPO_ROOT / ".github" / "workflows" / "pulumi-up.yml").read_text()
    )

    assert "SESSION_SECRET_KEY=<long_random_string>" in env_template
    assert "env: SESSION_SECRET_KEY" in cli_config
    assert "generate: true" in cli_config
    assert 'key="SESSION_SECRET_KEY"' in infra_source
    assert "datarobot.ApiTokenCredential" in infra_source
    assert "pulumi_datarobot.ApiTokenCredential" not in infra_source
    assert (
        pulumi_workflow["jobs"]["update"]["env"]["SESSION_SECRET_KEY"]
        == "${{ secrets.SESSION_SECRET_KEY }}"
    )


def test_test_user_email_is_scoped_to_dev_task_only() -> None:
    taskfile = yaml.safe_load((REPO_ROOT / "app_backend" / "Taskfile.yaml").read_text())

    assert "TEST_USER_EMAIL" not in taskfile.get("env", {})
    assert taskfile["tasks"]["dev"]["env"]["TEST_USER_EMAIL"] == "dev@example.com"


def test_env_template_documents_snowflake_values() -> None:
    env_template = (REPO_ROOT / ".env.template").read_text()

    assert "jdbc:snowflake://<account_identifier>.snowflakecomputing.com/" in (
        env_template
    )
    assert "SNOWFLAKE_SAMPLE_DATA" in env_template
    assert "TPCH_SF1" in env_template
    for expected in (
        'snowflake_authentication="key file authentication"',
        'SNOWFLAKE_USER="<snowflake_user>"',
        'SNOWFLAKE_PASSWORD="<snowflake_password>"',
        'SNOWFLAKE_KEY_PATH="rsa_key.p8"',
        'SNOWFLAKE_ACCOUNT="<account_identifier>"',
        'SNOWFLAKE_WAREHOUSE="COMPUTE_WH"',
        'SNOWFLAKE_DATABASE="SNOWFLAKE_SAMPLE_DATA"',
        'SNOWFLAKE_SCHEMA="TPCH_SF1"',
        'SNOWFLAKE_ROLE="PUBLIC"',
    ):
        assert expected in env_template
