from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT_PATH = (
    Path(__file__).parents[1]
    / ".github"
    / "scripts"
    / "prepare_pulumi_refresh_files.py"
)
SPEC = importlib.util.spec_from_file_location(
    "prepare_pulumi_refresh_files",
    SCRIPT_PATH,
)
assert SPEC is not None
prepare_pulumi_refresh_files = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(prepare_pulumi_refresh_files)


def test_prepare_refresh_files_restores_missing_state_assets(
    tmp_path: Path,
) -> None:
    workspace = tmp_path
    current_asset = workspace / "app_backend/static/assets/utils-current.js"
    current_asset.parent.mkdir(parents=True)
    current_asset.write_text("current chunk")

    missing_asset = workspace / "app_backend/static/assets/utils-old.js"
    missing_metadata = workspace / "app_backend/metadata.yaml"
    stack_state = {
        "deployment": {
            "resources": [
                {
                    "type": "datarobot:index/applicationSource:ApplicationSource",
                    "inputs": {
                        "files": [
                            [str(missing_asset), "static/assets/utils-old.js"],
                            [str(missing_metadata), "metadata.yaml"],
                        ]
                    },
                }
            ]
        }
    }

    created_files = prepare_pulumi_refresh_files.prepare_refresh_files(
        stack_state=stack_state,
        workspace=workspace,
    )

    assert sorted(path.name for path in created_files) == [
        "metadata.yaml",
        "utils-old.js",
    ]
    assert missing_asset.read_text() == "current chunk"
    assert "runtimeParameterDefinitions: []" in missing_metadata.read_text()


def test_prepare_refresh_files_remaps_absolute_runner_paths(
    tmp_path: Path,
) -> None:
    current_asset = tmp_path / "app_backend/static/assets/index-current.css"
    current_asset.parent.mkdir(parents=True)
    current_asset.write_text("current css")
    old_runner_asset = (
        "/home/runner/work/talk-to-my-data-agent-pandas/"
        "talk-to-my-data-agent-pandas/app_backend/static/assets/index-old.css"
    )
    expected_asset = tmp_path / "app_backend/static/assets/index-old.css"
    stack_state = {
        "deployment": {
            "resources": [
                {
                    "type": "datarobot:index/applicationSource:ApplicationSource",
                    "outputs": {
                        "files": [[old_runner_asset, "static/assets/index-old.css"]]
                    },
                }
            ]
        }
    }

    created_files = prepare_pulumi_refresh_files.prepare_refresh_files(
        stack_state=stack_state,
        workspace=tmp_path,
    )

    assert created_files == [expected_asset]
    assert expected_asset.read_text() == "current css"


def test_prepare_refresh_files_does_not_restore_deleted_source_files(
    tmp_path: Path,
) -> None:
    missing_build_script = tmp_path / "app_backend/build-app.sh"
    missing_requirements = tmp_path / "app_backend/requirements.txt"
    stack_state = {
        "deployment": {
            "resources": [
                {
                    "type": "datarobot:index/applicationSource:ApplicationSource",
                    "outputs": {
                        "files": [
                            [str(missing_build_script), "build-app.sh"],
                            [str(missing_requirements), "requirements.txt"],
                        ]
                    },
                }
            ]
        }
    }

    created_files = prepare_pulumi_refresh_files.prepare_refresh_files(
        stack_state=stack_state,
        workspace=tmp_path,
    )

    assert created_files == []
    assert not missing_build_script.exists()
    assert not missing_requirements.exists()
