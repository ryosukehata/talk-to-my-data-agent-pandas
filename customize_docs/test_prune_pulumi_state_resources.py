from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT_PATH = (
    Path(__file__).parents[1]
    / ".github"
    / "scripts"
    / "prune_pulumi_state_resources.py"
)
SPEC = importlib.util.spec_from_file_location(
    "prune_pulumi_state_resources",
    SCRIPT_PATH,
)
assert SPEC is not None
prune_pulumi_state_resources = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(prune_pulumi_state_resources)


def test_prune_resources_removes_matching_types_and_references() -> None:
    command_urn = (
        "urn:pulumi:dev::dataanalyst::command:local:Command::"
        "Data Analyst Build Frontend [dev]"
    )
    app_source_urn = (
        "urn:pulumi:dev::dataanalyst::datarobot:index/applicationSource:"
        "ApplicationSource::Data Analyst App Source [dev]"
    )
    stack_state = {
        "deployment": {
            "resources": [
                {
                    "type": "command:local:Command",
                    "urn": command_urn,
                },
                {
                    "type": "command:local:Command",
                    "urn": command_urn,
                    "delete": True,
                },
                {
                    "type": "datarobot:index/applicationSource:ApplicationSource",
                    "urn": app_source_urn,
                    "dependencies": [command_urn],
                    "propertyDependencies": {"files": [command_urn]},
                },
            ]
        }
    }

    pruned_state, removed_urns = prune_pulumi_state_resources.prune_resources(
        stack_state=stack_state,
        resource_types={"command:local:Command"},
        resource_names=set(),
    )

    assert removed_urns == [command_urn, command_urn]
    resources = pruned_state["deployment"]["resources"]
    assert [resource["urn"] for resource in resources] == [app_source_urn]
    assert resources[0]["dependencies"] == []
    assert resources[0]["propertyDependencies"]["files"] == []


def test_prune_resources_removes_matching_resource_names() -> None:
    dashboard_urn = (
        "urn:pulumi:dev::dataanalyst::datarobot:index/customApplication:"
        "CustomApplication::Data Analyst Dashboard [dev]"
    )
    app_urn = (
        "urn:pulumi:dev::dataanalyst::datarobot:index/customApplication:"
        "CustomApplication::Data Analyst Application [dev]"
    )
    stack_state = {
        "deployment": {
            "resources": [
                {
                    "type": "datarobot:index/customApplication:CustomApplication",
                    "urn": dashboard_urn,
                },
                {
                    "type": "datarobot:index/customApplication:CustomApplication",
                    "urn": app_urn,
                },
            ]
        }
    }

    pruned_state, removed_urns = prune_pulumi_state_resources.prune_resources(
        stack_state=stack_state,
        resource_types=set(),
        resource_names={"Data Analyst Dashboard [dev]"},
    )

    assert removed_urns == [dashboard_urn]
    assert pruned_state["deployment"]["resources"] == [
        {
            "type": "datarobot:index/customApplication:CustomApplication",
            "urn": app_urn,
        }
    ]
