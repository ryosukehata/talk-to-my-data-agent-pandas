from __future__ import annotations

from pathlib import Path

import yaml

WORKFLOWS_DIR = Path(__file__).parents[1] / ".github" / "workflows"


def _load_workflow(name: str) -> dict:
    return yaml.safe_load((WORKFLOWS_DIR / name).read_text())


def _step_by_name(steps: list[dict], name: str) -> dict:
    return next(step for step in steps if step.get("name") == name)


def _workflow_triggers(workflow: dict) -> dict:
    return workflow.get("on") or workflow[True]


def test_legacy_python_unit_workflow_stays_removed() -> None:
    assert not (WORKFLOWS_DIR / "python-unit-tests.yml").exists()


def test_pulumi_up_workflow_deploys_from_split_infra_project() -> None:
    workflow = _load_workflow("pulumi-up.yml")
    triggers = _workflow_triggers(workflow)
    job = workflow["jobs"]["update"]
    steps = job["steps"]

    assert triggers["push"]["branches"] == ["main", "dev"]
    assert "workflow_dispatch" in triggers
    assert workflow["permissions"] == {"contents": "read"}
    assert workflow["concurrency"] == {
        "group": "pulumi-up-${{ github.ref_name }}",
        "cancel-in-progress": False,
    }
    assert job["environment"] == "main"
    assert job["env"]["PULUMI_STACK_NAME"] == (
        "${{ github.ref == 'refs/heads/main' && "
        "'ryosukehata/dataanalyst/ttmd-pandas-react' || "
        "'ryosukehata/dataanalyst/dev' }}"
    )
    assert job["env"]["INFRA_ENABLE_LLM"] == "blueprint_with_external_llm.py"
    assert job["env"]["LLM_DEFAULT_MODEL"] == (
        "${{ vars.LLM_DEFAULT_MODEL || secrets.LLM_DEFAULT_MODEL || 'azure/gpt-4o' }}"
    )
    assert job["env"]["LLM_DEFAULT_LLM_ID"] == (
        "${{ vars.LLM_DEFAULT_LLM_ID || secrets.LLM_DEFAULT_LLM_ID || "
        "'azure-openai-gpt-4-o' }}"
    )
    assert job["env"]["LLM_DEFAULT_LLM_NAME"] == (
        "${{ vars.LLM_DEFAULT_LLM_NAME || secrets.LLM_DEFAULT_LLM_NAME || "
        "'Azure OpenAI GPT-4o' }}"
    )
    assert "TEXTGEN_DEPLOYMENT_ID" not in job["env"]
    assert job["env"]["OPENAI_API_KEY"] == "${{ secrets.OPENAI_API_KEY }}"
    assert job["env"]["APPLICATION_EXECUTION_ENVIRONMENT_ID"] == (
        "${{ github.ref == 'refs/heads/main' && "
        "secrets.APPLICATION_EXECUTION_ENVIRONMENT_ID || '' }}"
    )
    assert job["env"]["APPLICATION_EXECUTION_ENVIRONMENT_VERSION_ID"] == (
        "${{ github.ref == 'refs/heads/main' && "
        "secrets.APPLICATION_EXECUTION_ENVIRONMENT_VERSION_ID || '' }}"
    )

    node_step = _step_by_name(steps, "Set up Node.js")
    assert node_step["with"] == {"node-version": "22"}

    install_step = _step_by_name(steps, "Install infra dependencies")
    assert install_step == {
        "name": "Install infra dependencies",
        "working-directory": "infra",
        "run": "task install",
    }

    manifest_step = _step_by_name(
        steps, "Prepare application infra manifest for Pulumi refresh"
    )
    assert '{"llm":"llm","database":"no_database"}' in manifest_step["run"]

    build_step = _step_by_name(steps, "Build frontend assets for Pulumi refresh")
    assert build_step["working-directory"] == "app_frontend"
    assert "npm install" in build_step["run"]
    assert "npm ci" not in build_step["run"]
    assert "cache-dependency-path" not in build_step["run"]
    assert "for attempt in 1 2 3" in build_step["run"]
    assert "--fetch-retries=5" in build_step["run"]
    assert "--fetch-retry-mintimeout=20000" in build_step["run"]
    assert "--fetch-retry-maxtimeout=120000" in build_step["run"]
    assert "npm run build" in build_step["run"]

    restore_step = _step_by_name(
        steps, "Restore ApplicationSource files for Pulumi refresh"
    )
    assert restore_step["working-directory"] == "infra"
    assert "uv run pulumi stack export" in restore_step["run"]
    assert "../.github/scripts/prepare_pulumi_refresh_files.py" in restore_step["run"]

    prune_step = _step_by_name(steps, "Remove stale Pulumi state resources")
    assert prune_step["working-directory"] == "infra"
    assert "../.github/scripts/prune_pulumi_state_resources.py" in prune_step["run"]
    assert "uv run pulumi stack import" in prune_step["run"]

    pulumi_step = _step_by_name(steps, "Run Pulumi Up")
    assert pulumi_step["uses"] == "pulumi/actions@v6"
    assert pulumi_step["with"] == {
        "command": "up",
        "stack-name": "${{ env.PULUMI_STACK_NAME }}",
        "work-dir": "infra",
        "refresh": True,
    }


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
