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
    pulumi_steps = [step for step in steps if step.get("uses") == "pulumi/actions@v6"]

    assert prepare_manifest_step is not None
    assert "app_backend/app_infra.json" in prepare_manifest_step["run"]
    assert '"database":"no_database"' in prepare_manifest_step["run"]
    assert build_frontend_step is not None
    assert "cd app_frontend" in build_frontend_step["run"]
    assert "npm install" in build_frontend_step["run"]
    assert "npm run build" in build_frontend_step["run"]
    assert steps.index(build_frontend_step) < steps.index(pulumi_steps[0])
    assert len(pulumi_steps) == 2
    assert {
        step["with"]["stack-name"]: step["with"].get("refresh") for step in pulumi_steps
    } == {
        "ryosukehata/dataanalyst/ttmd-pandas-react": True,
        "ryosukehata/dataanalyst/dev": True,
    }
