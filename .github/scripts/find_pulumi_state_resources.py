from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def find_resource_urns(
    stack_state: dict[str, Any],
    resource_types: set[str],
) -> list[str]:
    resources = stack_state.get("deployment", {}).get("resources", [])
    urns: list[str] = []
    for resource in resources:
        if resource.get("type") not in resource_types:
            continue
        urn = resource.get("urn")
        if isinstance(urn, str):
            urns.append(urn)
    return urns


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("stack_state", type=Path)
    parser.add_argument("resource_types", nargs="+")
    args = parser.parse_args()

    stack_state = json.loads(args.stack_state.read_text())
    urns = find_resource_urns(
        stack_state=stack_state,
        resource_types=set(args.resource_types),
    )
    for urn in urns:
        print(urn)


if __name__ == "__main__":
    main()
