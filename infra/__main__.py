# Copyright 2024 DataRobot, Inc.
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
import os
import sys

import datarobot as dr
import pulumi
import pulumi_datarobot as datarobot
from datarobot_pulumi_utils.common.feature_flags import check_feature_flags
from datarobot_pulumi_utils.common.urls import get_deployment_url
from datarobot_pulumi_utils.pulumi.custom_model_deployment import CustomModelDeployment
from datarobot_pulumi_utils.pulumi.proxy_llm_blueprint import ProxyLLMBlueprint
from datarobot_pulumi_utils.pulumi.stack import PROJECT_NAME
from datarobot_pulumi_utils.schema.apps import CustomAppResourceBundles
from datarobot_pulumi_utils.schema.llms import LLMs

sys.path.append("..")

from settings_main import PROJECT_ROOT

from infra import (
    settings_app_infra,
    settings_dashboard_infra,
    settings_generative,
    settings_job_infra,
)
from infra.app_frontend import app_frontend
from infra.components.dr_credential import (
    get_credential_runtime_parameter_values,
    get_database_credentials,
    get_llm_credentials,
)
from infra.settings_database import DATABASE_CONNECTION_TYPE
from infra.settings_proxy_llm import CHAT_MODEL_NAME
from utils.custom_job_helper import (
    delete_all_custom_job_schedule,
    get_custom_job_by_name,
)
from utils.customize.csv_validator import (
    validate_prompt_template_csv,
    validate_schema_table_description_csv,
)
from utils.i18n import LocaleSettings
from utils.resources import (
    app_env_name,
    dashboard_env_name,
    llm_deployment_env_name,
)
from utils.schema import AppInfra

TEXTGEN_DEPLOYMENT_ID = os.environ.get("TEXTGEN_DEPLOYMENT_ID")
TEXTGEN_REGISTERED_MODEL_ID = os.environ.get("TEXTGEN_REGISTERED_MODEL_ID")
USE_DATAROBOT_LLM_GATEWAY = (
    os.environ.get("USE_DATAROBOT_LLM_GATEWAY", "false").lower() == "true"
)


# Check if OpenAI credentials are available (same logic as in utils/api.py)
def has_openai_credentials() -> bool:
    """Check if OpenAI credentials are available in environment variables."""
    # Check for the essential OpenAI environment variables
    api_key = os.environ.get("OPENAI_API_KEY")
    api_base = os.environ.get("OPENAI_API_BASE")

    if api_key and api_base:
        pulumi.info("OpenAI credentials detected in environment variables")
        return True
    return False


# 1. If `LLMs.DEPLOYED_LLM` is set, an already deployed DataRobot-hosted LLM deployment i.e.,
#    NVIDIA NIM, Cohere, Shared LLM Deployment, or other custom model of the text gen type.
# 2. If `LLMs.DEPLOYED_LLM` is unset and OpenAI Credentials are set, spin up an LLM Blueprint deployed
#    with OpenAI credentials
# 3. If `LLMs.DEPLOYED_LLM` is unset and OpenAI Credentials are not set, it check if pay as you go
#    pricing is enabled and spin up an LLM Blueprint with DataRobot credentials
HAS_OPENAI_CREDS = has_openai_credentials()
USE_LLM_GATEWAY = USE_DATAROBOT_LLM_GATEWAY and not HAS_OPENAI_CREDS

if USE_LLM_GATEWAY:
    pulumi.info("Using LLM Gateway - OpenAI credentials will not be required")
    check_feature_flags(
        PROJECT_ROOT / "infra" / "feature_flag_requirements_llm_gateway.yaml"
    )

if settings_generative.LLM == LLMs.DEPLOYED_LLM:
    pulumi.info(f"{TEXTGEN_DEPLOYMENT_ID=}")
    pulumi.info(f"{TEXTGEN_REGISTERED_MODEL_ID=}")
    if (TEXTGEN_DEPLOYMENT_ID is None) == (TEXTGEN_REGISTERED_MODEL_ID is None):  # XOR
        raise ValueError(
            "Either TEXTGEN_DEPLOYMENT_ID or TEXTGEN_REGISTERED_MODEL_ID must be set when using a deployed LLM. Plese check your .env file"
        )

LocaleSettings().setup_locale()

check_feature_flags(PROJECT_ROOT / "infra" / "feature_flag_requirements.yaml")

with open(
    settings_app_infra.application_path / "app_infra.json", "w"
) as infra_selection:
    infra_selection.write(
        AppInfra(
            database=DATABASE_CONNECTION_TYPE,
            llm=settings_generative.LLM.name,  # Always write the actual LLM name
        ).model_dump_json()
    )

if "DATAROBOT_DEFAULT_USE_CASE" in os.environ:
    use_case_id = os.environ["DATAROBOT_DEFAULT_USE_CASE"]
    pulumi.info(f"Using existing use case '{use_case_id}'")
    use_case = datarobot.UseCase.get(
        id=use_case_id,
        resource_name="Data Analyst Use Case [PRE-EXISTING]",
    )
else:
    use_case = datarobot.UseCase(
        resource_name=f"Data Analyst Use Case [{PROJECT_NAME}]",
        description="Use case for Data Analyst application",
    )

prediction_environment = datarobot.PredictionEnvironment(
    resource_name=f"Data Analyst Prediction Environment [{PROJECT_NAME}]",
    platform=dr.enums.PredictionEnvironmentPlatform.DATAROBOT_SERVERLESS,
)

if not USE_LLM_GATEWAY:
    llm_credential = get_llm_credentials(settings_generative.LLM)

    llm_runtime_parameter_values = get_credential_runtime_parameter_values(
        llm_credential, "llm"
    )

playground = datarobot.Playground(
    use_case_id=use_case.id,
    **settings_generative.playground_args.model_dump(),
)

if settings_generative.LLM == LLMs.DEPLOYED_LLM:
    if TEXTGEN_REGISTERED_MODEL_ID is not None:
        proxy_llm_registered_model = datarobot.RegisteredModel.get(
            resource_name="Existing TextGen Registered Model",
            id=TEXTGEN_REGISTERED_MODEL_ID,
        )

        proxy_llm_deployment = datarobot.Deployment(
            resource_name=f"Data Analyst LLM Deployment [{PROJECT_NAME}]",
            registered_model_version_id=proxy_llm_registered_model.version_id,
            prediction_environment_id=prediction_environment.id,
            label=f"Data Analyst LLM Deployment [{PROJECT_NAME}]",
            use_case_ids=[use_case.id],
            opts=pulumi.ResourceOptions(
                replace_on_changes=["registered_model_version_id"]
            ),
        )
    elif TEXTGEN_DEPLOYMENT_ID is not None:
        proxy_llm_deployment = datarobot.Deployment.get(
            resource_name="Existing LLM Deployment", id=TEXTGEN_DEPLOYMENT_ID
        )
    else:
        raise ValueError(
            "Either TEXTGEN_REGISTERED_MODEL_ID or TEXTGEN_DEPLOYMENT_ID have to be set in `.env`"
        )
    llm_blueprint = ProxyLLMBlueprint(
        use_case_id=use_case.id,
        playground_id=playground.id,
        proxy_llm_deployment_id=proxy_llm_deployment.id,
        chat_model_name=CHAT_MODEL_NAME,
        **settings_generative.llm_blueprint_args.model_dump(mode="python"),
    )

elif settings_generative.LLM != LLMs.DEPLOYED_LLM:
    llm_blueprint = datarobot.LlmBlueprint(  # type: ignore[assignment]
        playground_id=playground.id,
        **settings_generative.llm_blueprint_args.model_dump(),
    )

llm_custom_model = datarobot.CustomModel(
    **settings_generative.custom_model_args.model_dump(exclude_none=True),
    use_case_ids=[use_case.id],
    source_llm_blueprint_id=llm_blueprint.id,
    runtime_parameter_values=(
        []
        if settings_generative.LLM == LLMs.DEPLOYED_LLM or USE_LLM_GATEWAY
        else llm_runtime_parameter_values
    ),
    guard_configurations=settings_job_infra.guardrails,
)

llm_deployment = CustomModelDeployment(
    resource_name=f"Chat Agent Deployment [{PROJECT_NAME}]",
    use_case_ids=[use_case.id],
    custom_model_version_id=llm_custom_model.version_id,
    registered_model_args=settings_generative.registered_model_args,
    prediction_environment=prediction_environment,
    deployment_args=settings_generative.deployment_args,
)


app_runtime_parameters = [
    datarobot.ApplicationSourceRuntimeParameterValueArgs(
        key=llm_deployment_env_name,
        type="deployment",
        value=llm_deployment.id,
    ),
    datarobot.ApplicationSourceRuntimeParameterValueArgs(
        key="APP_LOCALE", type="string", value=LocaleSettings().app_locale
    ),
]


if os.environ.get("DATABASE_DESCRIPTION_PATH", None):
    file_path = str(PROJECT_ROOT / os.environ.get("DATABASE_DESCRIPTION_PATH"))

    # Validate CSV file before upload
    pulumi.info(f"Validating CSV file: {file_path}")

    validate_schema_table_description_csv(file_path)
    pulumi.info("CSV validation passed - file is ready for upload")
    try:
        dataset_description = datarobot.DatasetFromFile(
            resource_name=f"AI Catalog DATABASE DESCRIPTIONTools Dataset [{PROJECT_NAME}]",
            file_path=file_path,
            use_case_ids=[use_case.id],
        )
        app_runtime_parameters.append(
            datarobot.ApplicationSourceRuntimeParameterValueArgs(
                key="DATABASE_DESCRIPTION",
                type="string",
                value=dataset_description.id,
            )
        )
    except (FileNotFoundError, ValueError) as e:
        raise ValueError(f"CSV validation failed: {e}")
    except Exception as e:
        pulumi.warn(
            f"Could not create dataset from {os.environ.get('DATASET_DESCRIPTION_PATH')}: {e}"
        )


if os.environ.get("PROMPTS_TEMPLATE_PATH", None):
    file_path = str(PROJECT_ROOT / os.environ.get("PROMPTS_TEMPLATE_PATH"))

    # Validate CSV file before upload
    pulumi.info(f"Validating CSV file: {file_path}")

    validate_prompt_template_csv(file_path)
    pulumi.info("CSV validation passed - file is ready for upload")
    try:
        dataset_prompts_template = datarobot.DatasetFromFile(
            resource_name=f"AI Catalog Prompts Template Dataset [{PROJECT_NAME}]",
            file_path=file_path,
            use_case_ids=[use_case.id],
        )
        app_runtime_parameters.append(
            datarobot.ApplicationSourceRuntimeParameterValueArgs(
                key="PROMPT_TEMPLATE_AI_CATALOG",
                type="string",
                value=dataset_prompts_template.id,
            )
        )
    except (FileNotFoundError, ValueError) as e:
        raise ValueError(f"CSV validation failed: {e}")
    except Exception as e:
        pulumi.warn(
            f"Could not create dataset from {os.environ.get('DATASET_DESCRIPTION_PATH')}: {e}"
        )

if os.environ.get("VITE_ENABLE_TEMPLATE_EDIT"):
    app_runtime_parameters.append(
        datarobot.ApplicationSourceRuntimeParameterValueArgs(
            key="VITE_ENABLE_TEMPLATE_EDIT",
            type="string",
            value=os.environ.get("VITE_ENABLE_TEMPLATE_EDIT"),
        )
    )

if os.environ.get("VITE_ENABLE_CUSTOM_PROMPTS"):
    app_runtime_parameters.append(
        datarobot.ApplicationSourceRuntimeParameterValueArgs(
            key="VITE_ENABLE_CUSTOM_PROMPTS",
            type="string",
            value=os.environ.get("VITE_ENABLE_CUSTOM_PROMPTS"),
        )
    )


db_credential = get_database_credentials(DATABASE_CONNECTION_TYPE)

db_runtime_parameter_values = get_credential_runtime_parameter_values(
    db_credential, "db"
)
app_runtime_parameters += db_runtime_parameter_values  # type: ignore[arg-type]
# Only pass LLM Gateway runtime parameters if we're actually using LLM Gateway
# This prevents confusion when OpenAI credentials override LLM Gateway settings
if USE_LLM_GATEWAY:
    app_runtime_parameters.append(
        datarobot.ApplicationSourceRuntimeParameterValueArgs(
            key="USE_DATAROBOT_LLM_GATEWAY",
            type="string",
            value="true",
        )
    )


app_source = datarobot.ApplicationSource(
    files=app_frontend.stdout.apply(
        lambda _: settings_app_infra.get_app_files(
            runtime_parameter_values=app_runtime_parameters
        )
    ),
    runtime_parameter_values=app_runtime_parameters,
    resources=datarobot.ApplicationSourceResourcesArgs(
        resource_label=CustomAppResourceBundles.CPU_8XL.value.id,
        replicas=1,
        session_affinity=True,
    ),
    **settings_app_infra.app_source_args,
)

app = datarobot.CustomApplication(
    resource_name=settings_app_infra.app_resource_name,
    source_version_id=app_source.version_id,
    use_case_ids=[use_case.id],
    allow_auto_stopping=True,
)


pulumi.export(llm_deployment_env_name, llm_deployment.id)
pulumi.export(
    settings_generative.deployment_args.resource_name,
    llm_deployment.id.apply(get_deployment_url),
)
# Export LLM Gateway configuration for visibility
pulumi.export(
    "USE_DATAROBOT_LLM_GATEWAY", "true" if USE_DATAROBOT_LLM_GATEWAY else "false"
)

# App output
pulumi.export(app_env_name, app.id)
pulumi.export(
    settings_app_infra.app_resource_name,
    app.application_url,
)


def create_monitoring_resources():
    # Dataset for usage dashboard
    dataset_trace = datarobot.DatasetFromFile(
        "dataset_trace",
        file_path=settings_job_infra.dataset_trace_path,
        use_case_ids=[use_case.id],
    )
    dataset_access_log = datarobot.DatasetFromFile(
        "dataset_access_log",
        file_path=settings_job_infra.dataset_access_log_path,
        use_case_ids=[use_case.id],
    )

    # Dataset outputs
    pulumi.export(settings_job_infra.dataset_trace_name, dataset_trace.id)
    pulumi.export("DATASET_TRACE_ID", dataset_trace.id)
    pulumi.export(settings_job_infra.dataset_access_log_name, dataset_access_log.id)
    pulumi.export("DATASET_ACCESS_LOG_ID", dataset_access_log.id)

    # set the runtime parameters
    job_runtime_parameters = [
        datarobot.ApplicationSourceRuntimeParameterValueArgs(
            key=key,
            type="string",
            value=value,
        )
        for key, value in {
            "LLM_DEPLOYMENT_ID": llm_deployment.id,
            "DATAROBOT_APPLICATION_ID": app.id,
            "DATASET_TRACE_ID": dataset_trace.id,
            "DATASET_ACCESS_LOG_ID": dataset_access_log.id,
            "MODE": "append",
        }.items()
    ]

    class CustomJobScheduleCleanup(pulumi.ComponentResource):
        def __init__(self, name, custom_job_name, opts=None):
            super().__init__("custom:resource:CustomJobScheduleCleanup", name, {}, opts)
            self.cleanup_done = pulumi.Output.from_input(custom_job_name).apply(
                self._delete_schedules_if_exists
            )
            self.register_outputs({"cleanup_done": self.cleanup_done})

        def _delete_schedules_if_exists(self, job_name):
            job = get_custom_job_by_name(job_name)
            if job is None:
                # Job does not exist, skip deletion
                return True
            job_id = job["id"]
            delete_all_custom_job_schedule(job_id)
            return True

    # Cleanup schedules before updating/creating custom_job
    cleanup = CustomJobScheduleCleanup(
        "custom-job-schedule-cleanup", settings_job_infra.job_resource_name
    )

    job_files, job_files_hash = settings_job_infra.get_job_files(
        job_runtime_parameters, settings_job_infra.job_path
    )
    # Add content hash to description to force update on file change
    job_description = (
        f"DataRobot Custom Job for telemetry export. Content Hash: {job_files_hash}"
    )

    custom_job = datarobot.CustomJob(
        resource_name=settings_job_infra.job_resource_name,
        name=settings_job_infra.job_resource_name,
        description=job_description,
        environment_id=settings_job_infra.base_environment_id,
        files=job_files,
        runtime_parameter_values=job_runtime_parameters,
        resource_bundle_id=settings_job_infra.resource_bundle_id,
        job_type="default",
        opts=pulumi.ResourceOptions(
            depends_on=[cleanup],
        ),
    )

    pulumi.export(settings_job_infra.job_resource_name, custom_job.id)
    pulumi.export("CUSTOM_JOB_ID", custom_job.id)

    class CustomJobPostActions(pulumi.ComponentResource):
        def __init__(self, name, custom_job_id, opts=None):
            super().__init__(
                "custom:resource:CustomJobPostActions",
                name,
                {"custom_job_id": custom_job_id},
                opts,
            )
            import pulumi.runtime

            # Only run the job if we're in the actual update phase, not preview
            if not pulumi.runtime.is_dry_run():
                result = custom_job_id.apply(
                    lambda id: settings_job_infra.run_job_once(id)
                )
                self.custom_run_id = result.apply(
                    lambda r: r["run_id"] if r["success"] else "NA"
                )
            else:
                self.custom_run_id = pulumi.Output.from_input("NA")
            self.schedule_id = custom_job_id.apply(
                lambda id: settings_job_infra.create_job_schedule(id)
            )
            # Register outputs for stack export
            self.register_outputs(
                {
                    "custom_run_id": self.custom_run_id,
                    "schedule_id": self.schedule_id,
                }
            )

    # Post-actions after custom_job is fully created/updated
    post_actions = CustomJobPostActions(
        "custom-job-post-actions",
        custom_job.id,
        opts=pulumi.ResourceOptions(depends_on=[custom_job]),
    )

    pulumi.export("CUSTOM_JOB_RUN_ID", post_actions.custom_run_id)
    pulumi.export("CUSTOM_JOB_SCHEDULE_ID", post_actions.schedule_id)
    pulumi.export("MODE", "append")

    dashboard_runtime_parameters = [
        datarobot.ApplicationSourceRuntimeParameterValueArgs(
            key=key,
            type="string",
            value=value,
        )
        for key, value in {
            "DATASET_TRACE_ID": dataset_trace.id,
            "DATASET_ACCESS_LOG_ID": dataset_access_log.id,
        }.items()
    ]

    dashboard_files, dashboard_files_hash = (
        settings_dashboard_infra.get_dashboard_files()
    )
    dashboard_description = f"DataRobot Custom Application for Data Analyst Dashboard. Content Hash: {dashboard_files_hash}"
    pulumi.info(f"Dashboard description: {dashboard_description}")

    dashboard_source = datarobot.ApplicationSource(
        files=dashboard_files,
        runtime_parameter_values=dashboard_runtime_parameters,
        resources=datarobot.ApplicationSourceResourcesArgs(
            resource_label=CustomAppResourceBundles.CPU_XL.value.id,
        ),
        **settings_dashboard_infra.dashboard_source_args,
    )

    dashboard = datarobot.CustomApplication(
        resource_name=settings_dashboard_infra.dashboard_resource_name,
        source_version_id=dashboard_source.version_id,
        use_case_ids=[use_case.id],
        allow_auto_stopping=True,
    )

    pulumi.export(dashboard_env_name, dashboard.id)
    pulumi.export(
        settings_dashboard_infra.dashboard_resource_name, dashboard.application_url
    )


def create_cleanup_job(app: datarobot.CustomApplication):
    job_runtime_parameters = [
        datarobot.ApplicationSourceRuntimeParameterValueArgs(
            key=key,
            type="string",
            value=value,
        )
        for key, value in {
            "DATAROBOT_APPLICATION_ID": app.id,
        }.items()
    ]

    class CustomJobScheduleCleanup(pulumi.ComponentResource):
        def __init__(self, name, custom_job_name, opts=None):
            super().__init__("custom:resource:CustomJobScheduleCleanup", name, {}, opts)
            self.cleanup_done = pulumi.Output.from_input(custom_job_name).apply(
                self._delete_schedules_if_exists
            )
            self.register_outputs({"cleanup_done": self.cleanup_done})

        def _delete_schedules_if_exists(self, job_name):
            job = get_custom_job_by_name(job_name)
            if job is None:
                # Job does not exist, skip deletion
                return True
            job_id = job["id"]
            delete_all_custom_job_schedule(job_id)
            return True

    # Cleanup schedules before updating/creating custom_job
    cleanup = CustomJobScheduleCleanup(
        "cleanup-job-schedule-cleanup", settings_job_infra.cleanup_job_resource_name
    )

    job_files, job_files_hash = settings_job_infra.get_job_files(
        job_runtime_parameters, settings_job_infra.cleanup_job_path
    )

    # Add content hash to description to force update on file change
    job_description = f"DataRobot Cleanup Custom Job Content Hash: {job_files_hash}"

    cleanup_custom_job = datarobot.CustomJob(
        resource_name=settings_job_infra.cleanup_job_resource_name,
        name=settings_job_infra.cleanup_job_resource_name,
        description=job_description,
        environment_id=settings_job_infra.base_environment_id,
        files=job_files,
        runtime_parameter_values=job_runtime_parameters,
        resource_bundle_id=settings_job_infra.resource_bundle_id,
        job_type="default",
        opts=pulumi.ResourceOptions(
            depends_on=[cleanup],
        ),
    )
    pulumi.export(settings_job_infra.cleanup_job_resource_name, cleanup_custom_job.id)
    pulumi.export("CLEANUP_CUSTOM_JOB_ID", cleanup_custom_job.id)


# Only stop monitoring resources if DISALLOW_MONITORING_RESOURCES is set to true
if os.environ.get("DISALLOW_MONITORING_RESOURCES", "false").lower() == "true":
    pulumi.info("Disallowing monitoring resources")
else:
    create_monitoring_resources()

if os.environ.get("DISALLOW_APP_CLEANUP_JOB", "false").lower() == "true":
    pulumi.info("Skipping app data cleanup job creation")
else:
    create_cleanup_job(app)
