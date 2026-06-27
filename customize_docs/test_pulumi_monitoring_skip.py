from pathlib import Path

REPO_ROOT = Path(__file__).parents[1]
APP_BACKEND_SOURCE = REPO_ROOT / "infra" / "infra" / "app_backend.py"
JOBS_CONFIGURATION_SOURCE = (
    REPO_ROOT / "infra" / "configurations" / "jobs" / "custom_jobs.py"
)


def test_pulumi_stack_can_skip_monitoring_resources_for_cd() -> None:
    stack_source = APP_BACKEND_SOURCE.read_text()
    jobs_source = JOBS_CONFIGURATION_SOURCE.read_text()

    assert 'DISALLOW_MONITORING_RESOURCES", "false"' in stack_source
    assert "Disallowing monitoring resources" in jobs_source
    assert "create_monitoring_resources(" in jobs_source
