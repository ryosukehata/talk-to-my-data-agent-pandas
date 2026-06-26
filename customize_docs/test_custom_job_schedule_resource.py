from __future__ import annotations

from pathlib import Path

APP_BACKEND_SOURCE = Path(__file__).parents[1] / "infra" / "infra" / "app_backend.py"


def test_pulumi_stack_does_not_manage_custom_job_schedule() -> None:
    stack_source = APP_BACKEND_SOURCE.read_text()

    assert "CustomJobPostActions" not in stack_source
    assert "create_job_schedule" not in stack_source
    assert "schedule=" not in stack_source
    assert "CUSTOM_JOB_SCHEDULE_ID" not in stack_source


def test_pulumi_stack_keeps_optional_resource_guards() -> None:
    stack_source = APP_BACKEND_SOURCE.read_text()

    assert "FEATURE_FLAG_ENV_VARS.values()" in stack_source
    assert "DISALLOW_MONITORING_RESOURCES" in stack_source
    assert "SKIP_PULUMI_CUSTOM_JOBS" in stack_source
    assert "DISALLOW_APP_CLEANUP_JOB" in stack_source
    assert "create_monitoring_resources()" in stack_source
    assert "create_cleanup_job()" in stack_source


def test_app_backend_module_does_not_build_deploy_schedule_helpers() -> None:
    stack_source = APP_BACKEND_SOURCE.read_text()

    assert "def get_job_schedule" not in stack_source
    assert "def create_job_schedule" not in stack_source
