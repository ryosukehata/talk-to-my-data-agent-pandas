from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT_PATH = (
    Path(__file__).parents[1] / ".github" / "scripts" / "find_pulumi_state_resources.py"
)
SPEC = importlib.util.spec_from_file_location(
    "find_pulumi_state_resources",
    SCRIPT_PATH,
)
assert SPEC is not None
find_pulumi_state_resources = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(find_pulumi_state_resources)


def test_find_resource_urns_returns_only_matching_types() -> None:
    stack_state = {
        "deployment": {
            "resources": [
                {
                    "type": "custom:resource:CustomJobPostActions",
                    "urn": "urn:pulumi:dev::dataanalyst::custom:resource:CustomJobPostActions::custom-job-post-actions",
                },
                {
                    "type": "custom:resource:CustomJobScheduleCleanup",
                    "urn": "urn:pulumi:dev::dataanalyst::custom:resource:CustomJobScheduleCleanup::custom-job-schedule-cleanup",
                },
                {
                    "type": "datarobot:index/customJob:CustomJob",
                    "urn": "urn:pulumi:dev::dataanalyst::datarobot:index/customJob:CustomJob::Usage Export Job [dev]",
                },
            ]
        }
    }

    urns = find_pulumi_state_resources.find_resource_urns(
        stack_state=stack_state,
        resource_types={
            "custom:resource:CustomJobPostActions",
            "custom:resource:CustomJobScheduleCleanup",
        },
    )

    assert urns == [
        "urn:pulumi:dev::dataanalyst::custom:resource:CustomJobPostActions::custom-job-post-actions",
        "urn:pulumi:dev::dataanalyst::custom:resource:CustomJobScheduleCleanup::custom-job-schedule-cleanup",
    ]
