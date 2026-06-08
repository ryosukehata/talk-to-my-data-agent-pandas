from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any, Iterable

APPLICATION_SOURCE_TYPE = "datarobot:index/applicationSource:ApplicationSource"
GENERATED_METADATA = """---
name: runtime-params

runtimeParameterDefinitions: []
"""


def _iter_files_values(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
        return

    if isinstance(value, list):
        for item in value:
            if isinstance(item, str):
                yield item
            elif isinstance(item, list | tuple) and item:
                if isinstance(item[0], str):
                    yield item[0]
            elif isinstance(item, dict):
                yield from _iter_files_values(item)
        return

    if isinstance(value, dict):
        for key in ("source", "sourcePath", "source_path", "localPath", "path"):
            candidate = value.get(key)
            if isinstance(candidate, str):
                yield candidate
                return
        for nested_value in value.values():
            yield from _iter_files_values(nested_value)


def _iter_application_source_files(stack_state: dict[str, Any]) -> Iterable[str]:
    resources = stack_state.get("deployment", {}).get("resources", [])
    for resource in resources:
        if resource.get("type") != APPLICATION_SOURCE_TYPE:
            continue
        for property_name in ("inputs", "outputs"):
            files = resource.get(property_name, {}).get("files")
            if files is not None:
                yield from _iter_files_values(files)


def _workspace_relative_path(path: Path, workspace: Path) -> Path | None:
    if not path.is_absolute():
        return path

    try:
        return path.relative_to(workspace)
    except ValueError:
        pass

    parts = path.parts
    for top_level in (".github", "app_backend", "app_frontend", "frontend", "utils"):
        if top_level in parts:
            index = parts.index(top_level)
            return Path(*parts[index:])

    return None


def _resolve_workspace_path(raw_path: str, workspace: Path) -> Path | None:
    path = Path(raw_path)
    relative_path = _workspace_relative_path(path, workspace)
    if relative_path is None:
        return None
    return workspace / relative_path


def _find_asset_replacement(path: Path) -> Path | None:
    if path.exists() or path.parent.name != "assets":
        return None

    stem = path.stem
    if "-" not in stem:
        return None

    prefix = stem.rsplit("-", 1)[0]
    matches = sorted(path.parent.glob(f"{prefix}-*{path.suffix}"))
    return next((match for match in matches if match.is_file()), None)


def _write_placeholder(path: Path) -> None:
    if path.name == "metadata.yaml":
        path.write_text(GENERATED_METADATA)
    else:
        path.write_bytes(b"")


def prepare_refresh_files(stack_state: dict[str, Any], workspace: Path) -> list[Path]:
    created_files: list[Path] = []
    seen_paths: set[Path] = set()

    for raw_path in _iter_application_source_files(stack_state):
        path = _resolve_workspace_path(raw_path, workspace)
        if path is None or path in seen_paths or path.exists():
            continue

        seen_paths.add(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        replacement = _find_asset_replacement(path)
        if replacement is not None:
            shutil.copyfile(replacement, path)
        else:
            _write_placeholder(path)
        created_files.append(path)

    return created_files


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("stack_state", type=Path)
    parser.add_argument(
        "--workspace",
        type=Path,
        default=Path.cwd(),
        help="Repository workspace root. Defaults to the current directory.",
    )
    args = parser.parse_args()

    stack_state = json.loads(args.stack_state.read_text())
    created_files = prepare_refresh_files(
        stack_state=stack_state,
        workspace=args.workspace.resolve(),
    )

    for path in created_files:
        print(f"prepared {path}")
    print(f"prepared {len(created_files)} missing ApplicationSource files")


if __name__ == "__main__":
    main()
