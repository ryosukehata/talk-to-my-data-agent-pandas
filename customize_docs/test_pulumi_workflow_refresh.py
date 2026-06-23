from __future__ import annotations

from pathlib import Path

import yaml

WORKFLOWS_DIR = Path(__file__).parents[1] / ".github" / "workflows"


def _load_workflow(name: str) -> dict:
    return yaml.safe_load((WORKFLOWS_DIR / name).read_text())


def _step_by_name(steps: list[dict], name: str) -> dict:
    return next(step for step in steps if step.get("name") == name)


def test_removed_legacy_python_workflows_stay_removed() -> None:
    assert not (WORKFLOWS_DIR / "pulumi-up.yml").exists()
    assert not (WORKFLOWS_DIR / "python-unit-tests.yml").exists()


def test_infra_python_workflow_runs_split_infra_checks() -> None:
    workflow = _load_workflow("infra-python.yml")
    job = workflow["jobs"]["python-checks"]
    steps = job["steps"]

    assert job["defaults"]["run"]["working-directory"] == "infra"
    assert _step_by_name(steps, "Setup uv")["with"]["working-directory"] == "infra"
    assert _step_by_name(steps, "Install Dependencies") == {
        "name": "Install Dependencies",
        "working-directory": "infra",
        "run": "task install",
    }
    assert _step_by_name(steps, "Run Static Checks") == {
        "name": "Run Static Checks",
        "working-directory": "infra",
        "run": "task lint-check",
    }


def test_backend_workflow_builds_static_frontend_before_tests() -> None:
    workflow = _load_workflow("app_backend-test.yml")
    job = workflow["jobs"]["tests"]
    steps = job["steps"]
    build_frontend_step = _step_by_name(steps, "Build static Frontend files")
    test_step = _step_by_name(steps, "Test")

    assert job["defaults"]["run"]["working-directory"] == "app_backend"
    assert _step_by_name(steps, "Install Dependencies")["run"] == "task install"
    assert _step_by_name(steps, "Install Frontend Dependencies") == {
        "name": "Install Frontend Dependencies",
        "working-directory": "app_frontend",
        "run": "npm install",
    }
    assert build_frontend_step == {
        "name": "Build static Frontend files",
        "working-directory": "app_frontend",
        "run": "npm run build",
    }
    assert test_step == {
        "name": "Test",
        "working-directory": "app_backend",
        "run": "task test",
    }
    assert steps.index(build_frontend_step) < steps.index(test_step)
