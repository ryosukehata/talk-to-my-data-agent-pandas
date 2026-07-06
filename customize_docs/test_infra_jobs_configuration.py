from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).parents[1]
APP_BACKEND_SOURCE = REPO_ROOT / "infra" / "infra" / "app_backend.py"
JOBS_CONFIGURATION_SOURCE = (
    REPO_ROOT / "infra" / "configurations" / "jobs" / "custom_jobs.py"
)


def test_fork_specific_job_resources_live_in_jobs_configuration() -> None:
    source = JOBS_CONFIGURATION_SOURCE.read_text()

    assert "def create_optional_job_resources(" in source
    assert "def create_monitoring_resources(" in source
    assert "def create_cleanup_job(" in source
    assert "datarobot.CustomJob(" in source
    assert 'project_root / "resources" / "job_telemetry_exporter"' in source
    assert 'project_root / "resources" / "job_cleanup"' in source
    assert 'project_root / "resources" / "app_usage_dashboard"' in source


def test_app_backend_imports_jobs_configuration_without_owning_job_definitions() -> None:
    source = APP_BACKEND_SOURCE.read_text()

    assert (
        "from configurations.jobs.custom_jobs import create_optional_job_resources"
        in source
    )
    assert "create_optional_job_resources(" in source
    assert "def get_job_files(" not in source
    assert "def create_monitoring_resources(" not in source
    assert "def create_cleanup_job(" not in source
    assert "datarobot.CustomJob(" not in source
