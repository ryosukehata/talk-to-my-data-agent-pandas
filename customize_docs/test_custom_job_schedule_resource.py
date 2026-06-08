from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest


@pytest.fixture()
def settings_job_infra(monkeypatch: pytest.MonkeyPatch):
    from datarobot_pulumi_utils.schema import exec_envs

    monkeypatch.setenv("PULUMI_STACK_CONTEXT", "test-stack")
    monkeypatch.setattr(
        exec_envs.RuntimeEnvironment,
        "id",
        property(lambda self: "test-runtime-environment-id"),
    )
    sys.modules.pop("infra.settings_job_infra", None)
    module = importlib.import_module("infra.settings_job_infra")
    yield module
    sys.modules.pop("infra.settings_job_infra", None)


def test_pulumi_stack_does_not_manage_custom_job_schedule() -> None:
    stack_source = (Path(__file__).parents[1] / "infra" / "__main__.py").read_text()

    assert "CustomJobPostActions" not in stack_source
    assert "create_job_schedule" not in stack_source
    assert "schedule=" not in stack_source
    assert "CUSTOM_JOB_SCHEDULE_ID" not in stack_source


def test_settings_job_infra_does_not_build_deploy_schedule(settings_job_infra) -> None:
    assert not hasattr(settings_job_infra, "get_job_schedule")
    assert not hasattr(settings_job_infra, "create_job_schedule")
