from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).parents[1]


def _load_yaml(relative_path: str) -> dict[str, Any]:
    return yaml.safe_load((REPO_ROOT / relative_path).read_text())


def test_root_taskfile_exposes_infra_deploy_entrypoints() -> None:
    taskfile = _load_yaml("Taskfile.yaml")

    assert taskfile["includes"]["infra"] == {
        "taskfile": "./infra/Taskfile.yaml",
        "dir": "./infra",
    }
    assert taskfile["tasks"]["deploy"]["cmds"] == [{"task": "infra:deploy"}]
    assert taskfile["tasks"]["deploy-dev"]["cmds"] == [{"task": "infra:deploy-dev"}]


def test_infra_taskfile_uses_split_infra_project_entrypoints() -> None:
    taskfile = _load_yaml("infra/Taskfile.yaml")
    pulumi_project = _load_yaml("infra/Pulumi.yaml")
    tasks = taskfile["tasks"]

    assert pulumi_project["runtime"]["name"] == "python"
    assert "main" not in pulumi_project
    assert "deploy" in tasks["up"]["aliases"]
    assert tasks["deploy-dev"]["aliases"] == ["up-dev"]
    assert any(
        "run pulumi up" in command
        for command in tasks["up"]["cmds"]
        if isinstance(command, str)
    )
    assert any(
        "--target" in command
        for command in tasks["deploy-dev"]["cmds"]
        if isinstance(command, str)
    )
    assert any(
        "run pulumi refresh" in command
        for command in tasks["refresh"]["cmds"]
        if isinstance(command, str)
    )
    assert any(
        "run pulumi stack select" in command
        for command in tasks["select"]["cmds"]
        if isinstance(command, str)
    )


def test_cli_base_uses_runtime_database_connection_selection() -> None:
    cli_base = _load_yaml(".datarobot/cli/base.yml")
    root_entries = cli_base["root"]
    env_entries = {
        entry["env"]: entry
        for entry in root_entries
        if isinstance(entry, dict) and "env" in entry
    }
    key_entries = {
        entry["key"]: entry
        for entry in root_entries
        if isinstance(entry, dict) and "key" in entry
    }

    assert "DATAROBOT_DEFAULT_USE_CASE" in env_entries
    assert env_entries["DATAROBOT_DEFAULT_USE_CASE"]["optional"] is True
    assert "DATABASE_CONNECTION_TYPE" in env_entries
    assert env_entries["DATABASE_CONNECTION_TYPE"]["default"] == "no_database"
    assert {
        option.get("value", option["name"])
        for option in env_entries["DATABASE_CONNECTION_TYPE"]["options"]
    } == {"no_database", "snowflake", "bigquery", "sap"}
    assert "enable_snowflake" not in key_entries
    assert "enable_bigquery" not in key_entries
    assert "enable_sap_datasphere" not in key_entries
