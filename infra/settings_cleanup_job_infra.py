import hashlib
import textwrap
from pathlib import Path
from typing import Sequence, Tuple

import pulumi_datarobot as datarobot
from datarobot_pulumi_utils.pulumi.stack import PROJECT_NAME
from datarobot_pulumi_utils.schema.exec_envs import RuntimeEnvironment

from .settings_main import PROJECT_ROOT

# environment id
base_environment_id = RuntimeEnvironment(
    name="[DataRobot] Python 3.11 Custom Metrics"
).id


cleanup_job_path = PROJECT_ROOT / "resources" / "job_cleanup"

# set the source bundle
resource_bundle_id = "cpu.medium"


cleanup_job_resource_name: str = f"Cleanup Job [{PROJECT_NAME}]"


def _prep_metadata_yaml(
    runtime_parameter_values: Sequence[
        datarobot.ApplicationSourceRuntimeParameterValueArgs
        | datarobot.CustomModelRuntimeParameterValueArgs
    ],
    job_path: Path,
) -> None:
    from jinja2 import BaseLoader, Environment

    llm_runtime_parameter_specs = "\n".join(
        [
            textwrap.dedent(
                f"""\
            - fieldName: {param.key}
              type: {param.type}
        """
            )
            for param in runtime_parameter_values
        ]
    )
    with open(job_path / "metadata.yaml.jinja") as f:
        template = Environment(loader=BaseLoader()).from_string(f.read())
    (job_path / "metadata.yaml").write_text(
        template.render(
            additional_params=llm_runtime_parameter_specs,
        )
    )


def get_job_files(
    runtime_parameter_values: Sequence[
        datarobot.ApplicationSourceRuntimeParameterValueArgs
        | datarobot.CustomModelRuntimeParameterValueArgs,
    ],
    job_path: Path,
) -> Tuple[list[tuple[str, str]], str]:
    _prep_metadata_yaml(runtime_parameter_values)
    # Get all files from job path, excluding specific patterns
    files_to_include: list[Path] = []
    for f in job_path.glob("**/*"):
        if (
            f.is_file()
            and not f.name.endswith(".yaml")
            and "__pycache__" not in f.parts
            and not (f.name.endswith(".pyc") or f.name.endswith(".pyo"))
            and f.name != ".DS_Store"
            and f.name != "run_local.sh"
        ):
            files_to_include.append(f)

    # Add the generated metadata.yaml
    metadata_file_path = job_path / "metadata.yaml"
    files_to_include.append(metadata_file_path)

    # Calculate hash based on file contents
    hasher = hashlib.sha256()
    # Sort files by path to ensure consistent hash order
    files_to_include.sort()
    for file_path in files_to_include:
        try:
            with open(file_path, "rb") as file_content:
                while True:
                    chunk = file_content.read(4096)
                    if not chunk:
                        break
                    hasher.update(chunk)
        except FileNotFoundError:
            # metadata.yaml might not exist on the very first run before _prep_metadata_yaml
            # This is okay, the hash will change once it's created.
            pass

    content_hash = hasher.hexdigest()

    # Prepare the list of tuples for Pulumi
    source_files_tuples = [
        (f.as_posix(), f.relative_to(job_path).as_posix()) for f in files_to_include
    ]

    return source_files_tuples, content_hash
