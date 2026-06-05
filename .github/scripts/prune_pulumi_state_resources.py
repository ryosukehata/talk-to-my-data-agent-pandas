from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any


def _remove_urns(value: Any, removed_urns: set[str]) -> Any:
    if not isinstance(value, list):
        return value
    return [item for item in value if item not in removed_urns]


def _resource_name(resource: dict[str, Any]) -> str | None:
    urn = resource.get("urn")
    if not isinstance(urn, str):
        return None
    return urn.rsplit("::", maxsplit=1)[-1]


def _should_prune(
    resource: dict[str, Any],
    resource_types: set[str],
    resource_names: set[str],
) -> bool:
    return (
        resource.get("type") in resource_types
        or _resource_name(resource) in resource_names
    )


def prune_resources(
    stack_state: dict[str, Any],
    resource_types: set[str],
    resource_names: set[str],
) -> tuple[dict[str, Any], list[str]]:
    pruned_state = copy.deepcopy(stack_state)
    deployment = pruned_state.get("deployment", {})
    resources = deployment.get("resources", [])

    removed_urns = [
        resource["urn"]
        for resource in resources
        if _should_prune(resource, resource_types, resource_names)
        and isinstance(resource.get("urn"), str)
    ]
    removed_urn_set = set(removed_urns)
    if not removed_urn_set:
        return pruned_state, []

    kept_resources = [
        resource
        for resource in resources
        if not _should_prune(resource, resource_types, resource_names)
    ]
    for resource in kept_resources:
        if "dependencies" in resource:
            resource["dependencies"] = _remove_urns(
                resource.get("dependencies", []),
                removed_urn_set,
            )
        property_dependencies = resource.get("propertyDependencies")
        if isinstance(property_dependencies, dict):
            for property_name, dependencies in property_dependencies.items():
                property_dependencies[property_name] = _remove_urns(
                    dependencies,
                    removed_urn_set,
                )
        for field_name in ("parent", "deletedWith"):
            if resource.get(field_name) in removed_urn_set:
                resource.pop(field_name, None)

    deployment["resources"] = kept_resources
    return pruned_state, removed_urns


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("stack_state", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("resource_types", nargs="*")
    parser.add_argument("--resource-name", action="append", default=[])
    args = parser.parse_args()

    stack_state = json.loads(args.stack_state.read_text())
    pruned_state, removed_urns = prune_resources(
        stack_state=stack_state,
        resource_types=set(args.resource_types),
        resource_names=set(args.resource_name),
    )
    args.output.write_text(json.dumps(pruned_state, indent=2) + "\n")
    for urn in removed_urns:
        print(urn)


if __name__ == "__main__":
    main()
