from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest


@pytest.fixture()
def settings_job_infra(monkeypatch: pytest.MonkeyPatch):
    from datarobot_pulumi_utils.schema import exec_envs

    monkeypatch.setattr(
        exec_envs.RuntimeEnvironment,
        "id",
        property(lambda self: "test-runtime-environment-id"),
    )
    sys.modules.pop("infra.settings_job_infra", None)
    module = importlib.import_module("infra.settings_job_infra")
    yield module
    sys.modules.pop("infra.settings_job_infra", None)


def test_usage_export_job_schedule_uses_provider_args(settings_job_infra) -> None:
    original_hour = settings_job_infra.SCHEDULER_HOUR
    settings_job_infra.SCHEDULER_HOUR = 7
    try:
        schedule = settings_job_infra.get_job_schedule()
    finally:
        settings_job_infra.SCHEDULER_HOUR = original_hour

    assert schedule.minutes == ["0"]
    assert schedule.hours == ["7"]
    assert schedule.day_of_months == ["*"]
    assert schedule.months == ["*"]
    assert schedule.day_of_weeks == ["0", "1", "2", "3", "4"]


def test_pulumi_stack_does_not_use_manual_schedule_post_actions() -> None:
    stack_source = (Path(__file__).parents[1] / "infra" / "__main__.py").read_text()

    assert "CustomJobPostActions" not in stack_source
    assert "create_job_schedule" not in stack_source
    assert "schedule=settings_job_infra.get_job_schedule()" in stack_source
    assert "CUSTOM_JOB_SCHEDULE_ID" not in stack_source
