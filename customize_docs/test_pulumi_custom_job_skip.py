from pathlib import Path

REPO_ROOT = Path(__file__).parents[1]
APP_BACKEND_SOURCE = REPO_ROOT / "infra" / "infra" / "app_backend.py"
JOBS_CONFIGURATION_SOURCE = (
    REPO_ROOT / "infra" / "configurations" / "jobs" / "custom_jobs.py"
)


def test_pulumi_stack_can_skip_custom_job_resources_for_cd() -> None:
    stack_source = APP_BACKEND_SOURCE.read_text()
    jobs_source = JOBS_CONFIGURATION_SOURCE.read_text()

    assert "SKIP_PULUMI_CUSTOM_JOBS" in stack_source
    assert "skip_custom_jobs=SKIP_PULUMI_CUSTOM_JOBS" in stack_source
    assert "Skipping usage export custom job creation" in jobs_source
    assert "Skipping cleanup custom job creation" in jobs_source
    assert "datarobot.CustomJob(" in jobs_source
