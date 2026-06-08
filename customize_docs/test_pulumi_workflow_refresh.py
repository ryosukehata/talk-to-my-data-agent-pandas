from __future__ import annotations

from pathlib import Path

import yaml


def test_pulumi_up_workflow_refreshes_stack_before_update() -> None:
    workflow_path = (
        Path(__file__).parents[1] / ".github" / "workflows" / "pulumi-up.yml"
    )
    workflow = yaml.safe_load(workflow_path.read_text())

    steps = workflow["jobs"]["update"]["steps"]
    prepare_manifest_step = next(
        (
            step
            for step in steps
            if step.get("name")
            == "Prepare application infra manifest for Pulumi refresh"
        ),
        None,
    )
    build_frontend_step = next(
        (
            step
            for step in steps
            if step.get("name") == "Build frontend assets for Pulumi refresh"
        ),
        None,
    )
    restore_files_step = next(
        (
            step
            for step in steps
            if step.get("name") == "Restore ApplicationSource files for Pulumi refresh"
        ),
        None,
    )
    remove_stale_components_step = next(
        (
            step
            for step in steps
            if step.get("name") == "Remove stale Pulumi state resources"
        ),
        None,
    )
    pulumi_steps = [step for step in steps if step.get("uses") == "pulumi/actions@v6"]

    assert prepare_manifest_step is not None
    assert "app_backend/app_infra.json" in prepare_manifest_step["run"]
    assert '"database":"no_database"' in prepare_manifest_step["run"]
    assert build_frontend_step is not None
    assert "cd app_frontend" in build_frontend_step["run"]
    assert "npm install" in build_frontend_step["run"]
    assert "npm run build" in build_frontend_step["run"]
    assert steps.index(build_frontend_step) < steps.index(pulumi_steps[0])
    assert restore_files_step is not None
    assert "pulumi stack export" in restore_files_step["run"]
    assert "prepare_pulumi_refresh_files.py" in restore_files_step["run"]
    assert steps.index(restore_files_step) < steps.index(pulumi_steps[0])
    assert remove_stale_components_step is not None
    assert "prune_pulumi_state_resources.py" in remove_stale_components_step["run"]
    assert (
        "custom:resource:CustomJobPostActions" in (remove_stale_components_step["run"])
    )
    assert (
        "custom:resource:CustomJobScheduleCleanup"
        in (remove_stale_components_step["run"])
    )
    assert "command:local:Command" in remove_stale_components_step["run"]
    assert "datarobot:index/customJob:CustomJob" in remove_stale_components_step["run"]
    assert 'project_name="dev"' in remove_stale_components_step["run"]
    assert 'project_name="ttmd-pandas-react"' in remove_stale_components_step["run"]
    assert (
        "Data Analyst App Source [$project_name]" in remove_stale_components_step["run"]
    )
    assert "Data Analyst Dashboard Source" in remove_stale_components_step["run"]
    assert "Data Analyst Dashboard" in remove_stale_components_step["run"]
    assert "Dataset Trace" in remove_stale_components_step["run"]
    assert "Dataset Access Log" in remove_stale_components_step["run"]
    assert "pulumi stack import" in remove_stale_components_step["run"]
    assert "pulumi state delete" not in remove_stale_components_step["run"]
    assert steps.index(remove_stale_components_step) < steps.index(pulumi_steps[0])
    assert len(pulumi_steps) == 2
    assert {
        step["with"]["stack-name"]: step["with"].get("refresh") for step in pulumi_steps
    } == {
        "ryosukehata/dataanalyst/ttmd-pandas-react": True,
        "ryosukehata/dataanalyst/dev": True,
    }
    for step in pulumi_steps:
        assert step["env"]["SKIP_PULUMI_FRONTEND_BUILD"] == "true"
        assert step["env"]["SKIP_PULUMI_CUSTOM_JOBS"] == "true"
        assert step["env"]["DISALLOW_MONITORING_RESOURCES"] == "true"
        assert "SCHEDULER_HOUR" not in step["env"]
