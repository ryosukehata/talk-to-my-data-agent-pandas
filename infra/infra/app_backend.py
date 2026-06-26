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
import os
import re
import subprocess
import textwrap
from collections.abc import Callable
from pathlib import Path
from typing import Sequence, cast

import pulumi
import pulumi_datarobot as datarobot
from core.credentials import SnowflakeCredentials
from core.customize.csv_validator import (
    validate_prompt_template_csv,
    validate_schema_table_description_csv,
)
from core.customize.feature_flag_config import FEATURE_FLAG_ENV_VARS
from core.i18n import LanguageCode, LocaleSettings
from core.resources import (
    app_env_name,
    dashboard_env_name,
    database_description_name,
    prompt_template_ai_catalog_name,
)
from core.schema import AppInfra, DatabaseConnectionType
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

from . import llm as llm_module
from . import project_dir, use_case
from .app_frontend import app_frontend
from .components.dr_credential import (
    get_credential_runtime_parameter_values,
    get_database_credentials,
)
from .llm import app_runtime_parameters as llm_app_runtime_parameters

project_root = project_dir.parent
required_key_scope_level: str = "admin"

DATABASE_CONNECTION_TYPE = cast(
    DatabaseConnectionType, os.getenv("DATABASE_CONNECTION_TYPE", "no_database")
)
SKIP_PULUMI_CUSTOM_JOBS = (
    os.environ.get("SKIP_PULUMI_CUSTOM_JOBS", "false").lower() == "true"
)

APP_BACKEND_APP_PATHS = {
    "react": Path("app_backend"),
    "streamlit": Path("frontend"),
}
EXCLUDE_PATTERNS = [
    re.compile(pattern)
    for pattern in [
        r".*htmlcov/.*",
        r".*tests/.*",
        r".*\.coverage.*",
        r".*\.DS_Store",
        r".*\.dylib",
        r".*\.pyc",
        r".*\.ruff_cache/.*",
        r".*\.so",
        r".*\.venv/.*",
        r".*\.mypy_cache/.*",
        r".*__pycache__/.*",
        r".*\.pytest_cache/.*",
    ]
]

RuntimeParameter = (
    datarobot.ApplicationSourceRuntimeParameterValueArgs
    | datarobot.CustomModelRuntimeParameterValueArgs
)

__all__ = [
    "app_backend_app",
    "app_backend_app_env_name",
    "app_backend_app_resource_name",
    "app_backend_app_runtime_parameters",
    "app_backend_app_source",
    "app_backend_application_path",
    "get_app_backend_app_files",
]


def get_app_backend_app_path() -> Path:
    frontend_type = os.environ.get("FRONTEND_TYPE", "react")
    return APP_BACKEND_APP_PATHS[frontend_type]


def _deduplicate_files_by_destination(
    source_files: Sequence[tuple[str, str]],
) -> list[tuple[str, str]]:
    unique_files: dict[str, tuple[str, str]] = {}
    conflicting_destinations: set[str] = set()

    for source_path, destination_path in source_files:
        existing_file = unique_files.get(destination_path)
        if existing_file is None:
            unique_files[destination_path] = (source_path, destination_path)
            continue
        if existing_file[0] != source_path:
            conflicting_destinations.add(destination_path)

    if conflicting_destinations:
        duplicates = ", ".join(sorted(conflicting_destinations))
        raise ValueError(
            f"Duplicate application source destination paths: {duplicates}"
        )

    return list(unique_files.values())


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


def _prep_metadata_yaml(runtime_parameter_values: Sequence[RuntimeParameter]) -> None:
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
    if not runtime_parameter_specs:
        runtime_parameter_specs = "    []"
    with open(app_backend_application_path / "metadata.yaml.jinja") as f:
        template = Environment(loader=BaseLoader()).from_string(f.read())
    (app_backend_application_path / "metadata.yaml").write_text(
        template.render(additional_params=runtime_parameter_specs)
    )


def _write_version_file() -> None:
    version_file = app_backend_application_path / "VERSION"
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--always"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        pulumi.warn(f"Failed to determine application version via git: {exc}")
        version_file.unlink(missing_ok=True)
        return

    if result.returncode != 0:
        pulumi.warn(f"Failed to determine application version via git: {result.stderr}")
        version_file.unlink(missing_ok=True)
        return

    version_file.write_text(result.stdout.strip())


def get_app_backend_app_files(
    runtime_parameter_values: Sequence[RuntimeParameter],
) -> list[tuple[str, str]]:
    _prep_metadata_yaml(runtime_parameter_values)
    _write_version_file()
    source_files: list[tuple[str, str]] = []
    for dirpath, _, filenames in os.walk(
        app_backend_application_path, followlinks=True
    ):
        for filename in filenames:
            if ".yaml" in filename:
                continue
            file_path = Path(dirpath) / filename
            source_files.append(
                (
                    file_path.resolve().as_posix(),
                    file_path.relative_to(app_backend_application_path).as_posix(),
                )
            )
    source_files.extend(
        (f.as_posix(), f.relative_to(project_root).as_posix())
        for f in (project_root / "utils").glob("**/*.py")
        if f.is_file()
    )
    source_files.append(
        ((app_backend_application_path / "metadata.yaml").as_posix(), "metadata.yaml")
    )

    if DATABASE_CONNECTION_TYPE == "snowflake":
        credentials = SnowflakeCredentials()
        if credentials.snowflake_key_path:
            snowflake_file = project_root / credentials.snowflake_key_path
            if snowflake_file.is_file():
                source_files.append(
                    (str(snowflake_file), credentials.snowflake_key_path)
                )

    source_files = [
        (file_path, file_name)
        for file_path, file_name in source_files
        if not any(
            exclude_pattern.match(file_name) for exclude_pattern in EXCLUDE_PATTERNS
        )
    ]

    application_locale = LocaleSettings().app_locale
    if application_locale != LanguageCode.EN:
        source_files.append(
            (
                str(
                    project_root
                    / "core"
                    / "src"
                    / "core"
                    / "locale"
                    / application_locale
                    / "LC_MESSAGES"
                    / "base.mo"
                ),
                f"core/src/core/locale/{application_locale}/LC_MESSAGES/base.mo",
            )
        )

    return _deduplicate_files_by_destination(source_files)


def _add_dataset_runtime_parameter(
    runtime_parameters: list[datarobot.ApplicationSourceRuntimeParameterValueArgs],
    env_var_name: str,
    runtime_parameter_name: str,
    validator: Callable[[str], None],
    dataset_resource_name: str,
) -> None:
    if not os.environ.get(env_var_name):
        return

    file_path = str(project_root / os.environ[env_var_name])
    pulumi.info(f"Validating CSV file: {file_path}")
    validator(file_path)
    pulumi.info("CSV validation passed - file is ready for upload")

    dataset = datarobot.DatasetFromFile(
        resource_name=dataset_resource_name,
        file_path=file_path,
        use_case_ids=[use_case.id],
    )
    runtime_parameters.append(
        _app_runtime_parameter(runtime_parameter_name, dataset.id)
    )


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


def get_dashboard_files() -> tuple[list[tuple[str, str]], str]:
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


LocaleSettings().setup_locale()

app_backend_app_env_name: str = app_env_name
app_backend_application_path = project_root / get_app_backend_app_path()

with open(app_backend_application_path / "app_infra.json", "w") as infra_selection:
    infra_selection.write(
        AppInfra(
            database=DATABASE_CONNECTION_TYPE,
            llm=getattr(llm_module, "llm_application_name", "llm"),
        ).model_dump_json()
    )

use_japanese_font_env_raw = os.environ.get("USE_JAPANESE_FONT_ENV")
USE_JAPANESE_FONT_ENV = (
    use_japanese_font_env_raw.lower() in {"1", "true", "yes", "y", "on"}
    if use_japanese_font_env_raw is not None
    else False
)
app_environment_id = os.environ.get("APP_ENVIRONMENT_ID")
if app_environment_id:
    pulumi.info(f"Using existing app environment '{app_environment_id}'")
    app_environment = datarobot.ExecutionEnvironment.get(
        id=app_environment_id,
        resource_name="Data Analyst app environment [PRE-EXISTING]",
    )
    base_environment_id: pulumi.Input[str] = app_environment.id
elif USE_JAPANESE_FONT_ENV:
    app_environment = datarobot.ExecutionEnvironment(
        resource_name=f"App Environment for Data Analyst[{PROJECT_NAME}]",
        programming_language="python",
        use_cases=["customApplication"],
        description=f"App Environment for Data Analyst[{PROJECT_NAME}]",
        docker_context_path=os.fspath((project_root / "docker").resolve()),
        name="Python 3.12 Data Analyst Environment with Japanese Font",
    )
    base_environment_id = app_environment.id
else:
    base_environment_id = RuntimeEnvironments.PYTHON_312_APPLICATION_BASE.value.id

app_backend_app_source_args: dict[str, pulumi.Input[str]] = {
    "resource_name": f"Data Analyst App Source [{PROJECT_NAME}]",
    "base_environment_id": base_environment_id,
}
app_backend_app_resource_name: str = f"Data Analyst Application [{PROJECT_NAME}]"
app_backend_app_runtime_parameters = [
    *list(llm_app_runtime_parameters),
    _app_runtime_parameter("APP_LOCALE", LocaleSettings().app_locale),
]

for env_var in FEATURE_FLAG_ENV_VARS.values():
    if os.environ.get(env_var):
        app_backend_app_runtime_parameters.append(
            _app_runtime_parameter(env_var, os.environ[env_var])
        )

_add_dataset_runtime_parameter(
    app_backend_app_runtime_parameters,
    "DATABASE_DESCRIPTION_PATH",
    database_description_name,
    validate_schema_table_description_csv,
    f"AI Catalog DATABASE DESCRIPTIONTools Dataset [{PROJECT_NAME}]",
)
_add_dataset_runtime_parameter(
    app_backend_app_runtime_parameters,
    "PROMPTS_TEMPLATE_PATH",
    prompt_template_ai_catalog_name,
    validate_prompt_template_csv,
    f"AI Catalog Prompts Template Dataset [{PROJECT_NAME}]",
)

db_credential = get_database_credentials(DATABASE_CONNECTION_TYPE)
db_runtime_parameter_values = get_credential_runtime_parameter_values(db_credential)
app_backend_app_runtime_parameters += db_runtime_parameter_values  # type: ignore[arg-type]

if app_frontend is None:
    app_source_files = get_app_backend_app_files(app_backend_app_runtime_parameters)
else:
    app_source_files = app_frontend.stdout.apply(
        lambda _: get_app_backend_app_files(app_backend_app_runtime_parameters)
    )

app_backend_app_source = datarobot.ApplicationSource(
    files=app_source_files,
    runtime_parameter_values=app_backend_app_runtime_parameters,
    resources=datarobot.ApplicationSourceResourcesArgs(
        resource_label=CustomAppResourceBundles.CPU_7XL.value.id,
        replicas=1,
        session_affinity=True,
    ),
    required_key_scope_level=required_key_scope_level,
    opts=pulumi.ResourceOptions(retain_on_delete=True),
    **app_backend_app_source_args,
)

app_backend_app = datarobot.CustomApplication(
    resource_name=app_backend_app_resource_name,
    source_version_id=app_backend_app_source.version_id,
    use_case_ids=[use_case.id],
    allow_auto_stopping=True,
    resources=app_backend_app_source.resources,
    required_key_scope_level=app_backend_app_source.required_key_scope_level,
    opts=pulumi.ResourceOptions(depends_on=[app_backend_app_source]),
)

export(app_backend_app_env_name, app_backend_app.id)
export(app_backend_app_resource_name, app_backend_app.application_url)
export("DATAROBOT_APPLICATION_ID", app_backend_app.id)

base_job_environment_id = RuntimeEnvironment(
    name="[DataRobot] Python 3.11 Custom Metrics"
).id
job_resource_bundle_id = "cpu.medium"
dataset_trace_path = str(
    project_root / "resources" / "job_telemetry_exporter" / "sample_trace.csv"
)
dataset_access_log_path = str(
    project_root / "resources" / "job_telemetry_exporter" / "sample_access_log.csv"
)
job_path = project_root / "resources" / "job_telemetry_exporter"
cleanup_job_path = project_root / "resources" / "job_cleanup"
dashboard_path = project_root / "resources" / "app_usage_dashboard"
dataset_trace_name = f"Dataset Trace [{PROJECT_NAME}]"
dataset_access_log_name = f"Dataset Access Log [{PROJECT_NAME}]"
job_resource_name = f"Usage Export Job [{PROJECT_NAME}]"
cleanup_job_resource_name = f"Cleanup Job [{PROJECT_NAME}]"
dashboard_source_args = ApplicationSourceArgs(
    resource_name=f"Data Analyst Dashboard Source [{PROJECT_NAME}]",
    base_environment_id=RuntimeEnvironments.PYTHON_312_APPLICATION_BASE.value.id,
).model_dump(mode="json", exclude_none=True)
dashboard_resource_name = f"Data Analyst Dashboard [{PROJECT_NAME}]"


def create_monitoring_resources() -> None:
    llm_deployment_id = _runtime_parameter_value(
        app_backend_app_runtime_parameters, "LLM_DEPLOYMENT_ID"
    )
    if llm_deployment_id is None:
        pulumi.info(
            "Skipping usage monitoring resources because the selected LLM "
            "configuration does not expose LLM_DEPLOYMENT_ID"
        )
        return

    dataset_trace = datarobot.DatasetFromFile(
        "dataset_trace",
        file_path=dataset_trace_path,
        name=dataset_trace_name,
        use_case_ids=[use_case.id],
    )
    dataset_access_log = datarobot.DatasetFromFile(
        "dataset_access_log",
        file_path=dataset_access_log_path,
        name=dataset_access_log_name,
        use_case_ids=[use_case.id],
    )

    export(dataset_trace_name, dataset_trace.id)
    export("DATASET_TRACE_ID", dataset_trace.id)
    export(dataset_access_log_name, dataset_access_log.id)
    export("DATASET_ACCESS_LOG_ID", dataset_access_log.id)

    job_runtime_parameters = [
        _app_runtime_parameter("LLM_DEPLOYMENT_ID", llm_deployment_id),
        _app_runtime_parameter("DATAROBOT_APPLICATION_ID", app_backend_app.id),
        _app_runtime_parameter("DATASET_TRACE_ID", dataset_trace.id),
        _app_runtime_parameter("DATASET_ACCESS_LOG_ID", dataset_access_log.id),
    ]
    job_files, job_files_hash = get_job_files(job_runtime_parameters, job_path)
    job_description = (
        f"DataRobot Custom Job for telemetry export. Content Hash: {job_files_hash}"
    )

    if SKIP_PULUMI_CUSTOM_JOBS:
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
    dashboard_files, dashboard_files_hash = get_dashboard_files()
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
        use_case_ids=[use_case.id],
        allow_auto_stopping=True,
    )
    export(dashboard_env_name, dashboard.id)
    export(dashboard_resource_name, dashboard.application_url)


def create_cleanup_job() -> None:
    job_runtime_parameters = [
        _app_runtime_parameter("DATAROBOT_APPLICATION_ID", app_backend_app.id)
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


if os.environ.get("DISALLOW_MONITORING_RESOURCES", "false").lower() == "true":
    pulumi.info("Disallowing monitoring resources")
else:
    create_monitoring_resources()

if SKIP_PULUMI_CUSTOM_JOBS:
    pulumi.info("Skipping cleanup custom job creation")
elif os.environ.get("DISALLOW_APP_CLEANUP_JOB", "false").lower() == "true":
    pulumi.info("Skipping app data cleanup job creation")
else:
    create_cleanup_job()
