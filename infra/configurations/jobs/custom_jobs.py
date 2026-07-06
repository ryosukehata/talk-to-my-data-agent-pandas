# Copyright 2025 DataRobot, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import hashlib
import textwrap
from collections.abc import Sequence
from pathlib import Path

import pulumi
import pulumi_datarobot as datarobot
from core.resources import dashboard_env_name
from datarobot_pulumi_utils.pulumi import export
from datarobot_pulumi_utils.pulumi.stack import PROJECT_NAME
from datarobot_pulumi_utils.schema.apps import (
    ApplicationSourceArgs,
    CustomAppResourceBundles,
)
from datarobot_pulumi_utils.schema.exec_envs import (
    RuntimeEnvironment,
    RuntimeEnvironments,
)

RuntimeParameter = (
    datarobot.ApplicationSourceRuntimeParameterValueArgs
    | datarobot.CustomModelRuntimeParameterValueArgs
)

__all__ = [
    "create_cleanup_job",
    "create_monitoring_resources",
    "create_optional_job_resources",
    "get_dashboard_files",
    "get_job_files",
]


def _app_runtime_parameter(
    key: str, value: pulumi.Input[str]
) -> datarobot.ApplicationSourceRuntimeParameterValueArgs:
    return datarobot.ApplicationSourceRuntimeParameterValueArgs(
        key=key,
        type="string",
        value=value,
    )


def _runtime_parameter_value(
    runtime_parameter_values: Sequence[RuntimeParameter], key: str
) -> pulumi.Input[str] | None:
    for parameter in runtime_parameter_values:
        if parameter.key == key:
            return parameter.value
    return None


def _prep_job_metadata_yaml(
    runtime_parameter_values: Sequence[RuntimeParameter],
    job_path: Path,
) -> None:
    from jinja2 import BaseLoader, Environment

    runtime_parameter_specs = "\n".join(
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
        template.render(additional_params=runtime_parameter_specs)
    )


def get_job_files(
    runtime_parameter_values: Sequence[RuntimeParameter],
    job_path: Path,
) -> tuple[list[tuple[str, str]], str]:
    _prep_job_metadata_yaml(runtime_parameter_values, job_path=job_path)
    files_to_include: list[Path] = []
    for file_path in job_path.glob("**/*"):
        if (
            file_path.is_file()
            and not file_path.name.endswith(".yaml")
            and "__pycache__" not in file_path.parts
            and not (file_path.name.endswith(".pyc") or file_path.name.endswith(".pyo"))
            and file_path.name != ".DS_Store"
            and file_path.name != "run_local.sh"
        ):
            files_to_include.append(file_path)

    files_to_include.append(job_path / "metadata.yaml")
    hasher = hashlib.sha256()
    files_to_include.sort()
    for file_path in files_to_include:
        try:
            with open(file_path, "rb") as file_content:
                while chunk := file_content.read(4096):
                    hasher.update(chunk)
        except FileNotFoundError:
            pass

    source_files = [
        (file_path.as_posix(), file_path.relative_to(job_path).as_posix())
        for file_path in files_to_include
    ]
    return source_files, hasher.hexdigest()


def get_dashboard_files(dashboard_path: Path) -> tuple[list[tuple[str, str]], str]:
    files_to_include: list[Path] = []
    for file_path in dashboard_path.glob("**/*"):
        if (
            file_path.is_file()
            and "__pycache__" not in file_path.parts
            and not (file_path.name.endswith(".pyc") or file_path.name.endswith(".pyo"))
            and file_path.name != ".DS_Store"
            and file_path.name != "run_local.sh"
        ):
            files_to_include.append(file_path)

    hasher = hashlib.sha256()
    files_to_include.sort()
    for file_path in files_to_include:
        try:
            with open(file_path, "rb") as file_content:
                while chunk := file_content.read(4096):
                    hasher.update(chunk)
        except FileNotFoundError:
            pass

    source_files = [
        (str(file_path), file_path.relative_to(dashboard_path).as_posix())
        for file_path in files_to_include
    ]
    return source_files, hasher.hexdigest()


def create_monitoring_resources(
    *,
    project_root: Path,
    use_case_id: pulumi.Input[str],
    app_backend_app_id: pulumi.Input[str],
    app_backend_app_runtime_parameters: Sequence[RuntimeParameter],
    skip_custom_jobs: bool,
) -> None:
    llm_deployment_id = _runtime_parameter_value(
        app_backend_app_runtime_parameters, "LLM_DEPLOYMENT_ID"
    )
    if llm_deployment_id is None:
        pulumi.info(
            "Skipping usage monitoring resources because the selected LLM "
            "configuration does not expose LLM_DEPLOYMENT_ID"
        )
        return

    base_job_environment_id = RuntimeEnvironment(
        name="[DataRobot] Python 3.11 Custom Metrics"
    ).id
    job_resource_bundle_id = "cpu.medium"
    job_path = project_root / "resources" / "job_telemetry_exporter"
    dashboard_path = project_root / "resources" / "app_usage_dashboard"
    dataset_trace_path = str(job_path / "sample_trace.csv")
    dataset_access_log_path = str(job_path / "sample_access_log.csv")
    dataset_trace_name = f"Dataset Trace [{PROJECT_NAME}]"
    dataset_access_log_name = f"Dataset Access Log [{PROJECT_NAME}]"
    job_resource_name = f"Usage Export Job [{PROJECT_NAME}]"
    dashboard_source_args = ApplicationSourceArgs(
        resource_name=f"Data Analyst Dashboard Source [{PROJECT_NAME}]",
        base_environment_id=RuntimeEnvironments.PYTHON_312_APPLICATION_BASE.value.id,
    ).model_dump(mode="json", exclude_none=True)
    dashboard_resource_name = f"Data Analyst Dashboard [{PROJECT_NAME}]"

    dataset_trace = datarobot.DatasetFromFile(
        "dataset_trace",
        file_path=dataset_trace_path,
        name=dataset_trace_name,
        use_case_ids=[use_case_id],
    )
    dataset_access_log = datarobot.DatasetFromFile(
        "dataset_access_log",
        file_path=dataset_access_log_path,
        name=dataset_access_log_name,
        use_case_ids=[use_case_id],
    )

    export(dataset_trace_name, dataset_trace.id)
    export("DATASET_TRACE_ID", dataset_trace.id)
    export(dataset_access_log_name, dataset_access_log.id)
    export("DATASET_ACCESS_LOG_ID", dataset_access_log.id)

    job_runtime_parameters = [
        _app_runtime_parameter("LLM_DEPLOYMENT_ID", llm_deployment_id),
        _app_runtime_parameter("DATAROBOT_APPLICATION_ID", app_backend_app_id),
        _app_runtime_parameter("DATASET_TRACE_ID", dataset_trace.id),
        _app_runtime_parameter("DATASET_ACCESS_LOG_ID", dataset_access_log.id),
    ]
    job_files, job_files_hash = get_job_files(job_runtime_parameters, job_path)
    job_description = (
        f"DataRobot Custom Job for telemetry export. Content Hash: {job_files_hash}"
    )

    if skip_custom_jobs:
        pulumi.info("Skipping usage export custom job creation")
    else:
        custom_job = datarobot.CustomJob(
            resource_name=job_resource_name,
            name=job_resource_name,
            description=job_description,
            environment_id=base_job_environment_id,
            files=job_files,
            runtime_parameter_values=job_runtime_parameters,
            resource_bundle_id=job_resource_bundle_id,
            job_type="default",
        )
        export(job_resource_name, custom_job.id)
        export("CUSTOM_JOB_ID", custom_job.id)

    dashboard_runtime_parameters = [
        _app_runtime_parameter("DATASET_TRACE_ID", dataset_trace.id),
        _app_runtime_parameter("DATASET_ACCESS_LOG_ID", dataset_access_log.id),
    ]
    dashboard_files, dashboard_files_hash = get_dashboard_files(dashboard_path)
    dashboard_description = (
        "DataRobot Custom Application for Data Analyst Dashboard. "
        f"Content Hash: {dashboard_files_hash}"
    )
    pulumi.info(f"Dashboard description: {dashboard_description}")

    dashboard_source = datarobot.ApplicationSource(
        files=dashboard_files,
        runtime_parameter_values=dashboard_runtime_parameters,
        resources=datarobot.ApplicationSourceResourcesArgs(
            resource_label=CustomAppResourceBundles.CPU_XL.value.id,
        ),
        opts=pulumi.ResourceOptions(retain_on_delete=True),
        **dashboard_source_args,
    )
    dashboard = datarobot.CustomApplication(
        resource_name=dashboard_resource_name,
        source_version_id=dashboard_source.version_id,
        use_case_ids=[use_case_id],
        allow_auto_stopping=True,
    )
    export(dashboard_env_name, dashboard.id)
    export(dashboard_resource_name, dashboard.application_url)


def create_cleanup_job(
    *,
    project_root: Path,
    app_backend_app_id: pulumi.Input[str],
) -> None:
    base_job_environment_id = RuntimeEnvironment(
        name="[DataRobot] Python 3.11 Custom Metrics"
    ).id
    job_resource_bundle_id = "cpu.medium"
    cleanup_job_path = project_root / "resources" / "job_cleanup"
    cleanup_job_resource_name = f"Cleanup Job [{PROJECT_NAME}]"
    job_runtime_parameters = [
        _app_runtime_parameter("DATAROBOT_APPLICATION_ID", app_backend_app_id)
    ]
    job_files, job_files_hash = get_job_files(job_runtime_parameters, cleanup_job_path)
    job_description = f"DataRobot Cleanup Custom Job Content Hash: {job_files_hash}"

    cleanup_custom_job = datarobot.CustomJob(
        resource_name=cleanup_job_resource_name,
        name=cleanup_job_resource_name,
        description=job_description,
        environment_id=base_job_environment_id,
        files=job_files,
        runtime_parameter_values=job_runtime_parameters,
        resource_bundle_id=job_resource_bundle_id,
        job_type="default",
    )
    export(cleanup_job_resource_name, cleanup_custom_job.id)
    export("CLEANUP_CUSTOM_JOB_ID", cleanup_custom_job.id)


def create_optional_job_resources(
    *,
    project_root: Path,
    use_case_id: pulumi.Input[str],
    app_backend_app_id: pulumi.Input[str],
    app_backend_app_runtime_parameters: Sequence[RuntimeParameter],
    skip_custom_jobs: bool,
    disallow_monitoring_resources: bool,
    disallow_app_cleanup_job: bool,
) -> None:
    if disallow_monitoring_resources:
        pulumi.info("Disallowing monitoring resources")
    else:
        create_monitoring_resources(
            project_root=project_root,
            use_case_id=use_case_id,
            app_backend_app_id=app_backend_app_id,
            app_backend_app_runtime_parameters=app_backend_app_runtime_parameters,
            skip_custom_jobs=skip_custom_jobs,
        )

    if skip_custom_jobs:
        pulumi.info("Skipping cleanup custom job creation")
    elif disallow_app_cleanup_job:
        pulumi.info("Skipping app data cleanup job creation")
    else:
        create_cleanup_job(
            project_root=project_root,
            app_backend_app_id=app_backend_app_id,
        )
