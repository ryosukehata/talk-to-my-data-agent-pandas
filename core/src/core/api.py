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
from __future__ import annotations

import ast
import asyncio
import copy
import functools
import inspect
import json
import logging
import os
import re
import sys
import tempfile
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from types import ModuleType
from typing import (
    Any,
    AsyncGenerator,
    Callable,
    Literal,
    TypeVar,
    cast,
)

import datarobot as dr
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import psutil
import scipy
import sklearn
import statsmodels as sm
from datarobot.client import RESTClientObject
from datarobot.models.dataset import Dataset
from datarobot_genai.core.utils.token_tracking import (
    HeuristicTokenCountingStrategy,
    TokenUsageTracker,
    count_messages_tokens,
    estimate_csv_rows_for_token_limit,
)
from fastapi import Request
from joblib import Memory
from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam
from openai.types.chat.chat_completion_system_message_param import (
    ChatCompletionSystemMessageParam,
)
from openai.types.chat.chat_completion_user_message_param import (
    ChatCompletionUserMessageParam,
)
from plotly.subplots import make_subplots
from pydantic import BaseModel, ValidationError

from core.api_exceptions import ApplicationUsageException, UsageExceptionType
from core.chat_dataset_helper import extract_and_store_datasets
from core.constants import (
    ALTERNATIVE_LLM_BIG,
    ALTERNATIVE_LLM_SMALL,
    DICTIONARY_BATCH_SIZE,
    DICTIONARY_PARALLEL_BATCH_SIZE,
    DICTIONARY_TIMEOUT,
    DISK_CACHE_LIMIT_BYTES,
    MAX_CSV_TOKENS,
    MAX_REGISTRY_DATASET_SIZE,
    REGISTRY_DATASET_SIZE_CUTOFF,
    VALUE_ERROR_MESSAGE,
)
from core.data_connections.datarobot.helpers import handle_datarobot_error
from core.datarobot_client import use_user_token
from core.datarobot_dataset_handler import (
    BaseRecipe,
    DatasetSparkRecipe,
    DataSourceRecipe,
    load_or_create_spark_recipe,
)
from core.llm_client import AsyncLLMClient

sys.path.append(os.path.dirname(os.path.realpath(__file__)))
from core import prompts, tools
from core.analyst_db import (
    AnalystDB,
    DatasetMetadata,
    DataSourceType,
    ExternalDataStoreNameDataSourceType,
    InternalDataSourceType,
    get_data_source_type,
)
from core.code_execution import (
    InvalidGeneratedCode,
    MaxReflectionAttempts,
    execute_python,
    reflect_code_generation_errors,
)
from core.data_analyst_telemetry import telemetry
from core.data_cleansing_helpers import (
    add_summary_statistics,
    process_column,
)
from core.database_helpers import DatabaseOperator, get_external_database
from core.dr_helper import async_submit_actuals_to_datarobot
from core.i18n import gettext
from core.logging_helper import get_logger, log_api_call
from core.resources import LLMDeployment
from core.schema import (
    AnalysisError,
    AnalystChatMessage,
    AnalystDataset,
    BusinessAnalysisGeneration,
    ChartGenerationExecutionResult,
    ChatRequest,
    CleansedDataset,
    CodeGeneration,
    Component,
    DatabaseAnalysisCodeGeneration,
    DataDictionary,
    DataDictionaryColumn,
    DataRegistryDataset,
    DictionaryGeneration,
    DownloadedRegistryDataset,
    EnhancedQuestionGeneration,
    ExternalDataSource,
    ExternalDataSourcesSelection,
    GetBusinessAnalysisMetadata,
    GetBusinessAnalysisRequest,
    GetBusinessAnalysisResult,
    RunAnalysisRequest,
    RunAnalysisResult,
    RunAnalysisResultMetadata,
    RunChartsRequest,
    RunChartsResult,
    RunDatabaseAnalysisRequest,
    RunDatabaseAnalysisResult,
    RunDatabaseAnalysisResultMetadata,
    TokenUsageInfo,
    Tool,
    UsageInfoComponent,
)

logger = get_logger()
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("openai.http_client").setLevel(logging.WARNING)


def log_memory() -> None:
    process = psutil.Process()
    memory = process.memory_info().rss / 1024 / 1024  # MB
    logger.info(f"Memory usage: {memory:.2f} MB")


def _get_datarobot_association_id(completion_response: Any) -> str:
    association_id = getattr(completion_response, "datarobot_association_id", None)
    if association_id is None and isinstance(completion_response, dict):
        association_id = completion_response.get("datarobot_association_id")
    if not association_id:
        raise ValueError("DataRobot response did not include datarobot_association_id.")
    return str(association_id)


@functools.cache
def initialize_deployment() -> tuple[RESTClientObject, str]:
    """Initialize either LLM Gateway or DataRobot-hosted LLM deployment based on environment settings and credential priority."""
    try:
        dr_client = dr.Client()
        chat_agent_deployment_id = LLMDeployment().id
        if chat_agent_deployment_id is None:
            raise ValueError(
                "LLM Deployment ID is required but not found. Please check your infrastructure setup."
            )
        deployment_chat_base_url = (
            f"{dr_client.endpoint.rstrip('/')}/deployments/{chat_agent_deployment_id}/"
        )
        logger.info(
            f"Using the DataRobot-hosted LLM deployment (configured at infrastructure time) at: {deployment_chat_base_url}"
        )
        return dr_client, deployment_chat_base_url

    except ValidationError as e:
        raise ValueError(
            "Unable to load Deployment ID."
            "If running locally, verify you have selected the correct "
            "stack and that it is active using `pulumi stack output`. "
            "If running in DataRobot, verify your runtime parameters have been set correctly."
        ) from e


_memory = Memory(tempfile.gettempdir(), verbose=0)
_memory.clear(warn=False)  # clear cache on startup

T = TypeVar("T")


def cache(f: T) -> T:
    """Cache function and coroutine results to disk using joblib."""
    cached_f = _memory.cache(f)

    if asyncio.iscoroutinefunction(f):

        async def awrapper(*args: Any, **kwargs: Any) -> Any:
            in_cache = cached_f.check_call_in_cache(*args, **kwargs)
            result = await cached_f(*args, **kwargs)
            if not in_cache:
                _memory.reduce_size(DISK_CACHE_LIMIT_BYTES)
            else:
                logger.info(
                    f"Using previously cached result for function `{f.__name__}`"
                )
            return result

        return cast(T, awrapper)
    else:

        def wrapper(*args: Any, **kwargs: Any) -> Any:
            in_cache = cached_f.check_call_in_cache(*args, **kwargs)
            result = cached_f(*args, **kwargs)
            if not in_cache:
                _memory.reduce_size(DISK_CACHE_LIMIT_BYTES)
            else:
                logger.info(
                    f"Using previously cached result for function `{f.__name__}`"  # type: ignore[attr-defined]
                )
            return result

        return cast(T, wrapper)


def get_user_email() -> str:
    return dr.client.get_client().get("account/info/").json()["email"]


# This can be large as we are not storing the actual datasets in memory, just metadata
@telemetry.meter_and_trace
def list_registry_datasets(
    remote: bool = False, limit: int = 100
) -> list[DataRegistryDataset]:
    """Fetch datasets from Data Registry with specified limit

    Args:
        filter_downloadable (bool, optional): Include only downloadable datasets. Defaults to False.
        limit (int, optional): _description_. Defaults to 100.

    Returns:
        list[DataRegistryDataset]: _description_
    """
    logger.info(f"Acting as user: {get_user_email()}")

    with handle_datarobot_error("Dataset.iterate()"):
        datasets = list(Dataset.iterate(limit=limit, filter_failed=True))

    return [
        DataRegistryDataset(
            id=ds.id,
            name=ds.name,
            created=(_year_month_day(ds.created_at) if ds.created_at else "N/A"),
            size=(f"{ds.size / (1024 * 1024):.1f} MB" if ds.size else "N/A"),
        )
        for ds in datasets
        if (remote and ds.is_data_engine_eligible and ds.is_snapshot)
        or (
            not remote
            and ds.size
            and ds.size <= REGISTRY_DATASET_SIZE_CUTOFF
            and ds.is_snapshot
        )
    ]


def _year_month_day(date: datetime | str) -> str:
    if isinstance(date, str):
        date = datetime.fromisoformat(date)
    return date.strftime("%Y-%m-%d")


@telemetry.trace
async def register_remote_registry_datasets(
    request: Request, dataset_ids: list[str], analyst_db: AnalystDB
) -> tuple[
    list[DownloadedRegistryDataset],
    list[tuple[Callable[..., Any], list[Any], dict[str, Any]]],
]:
    """Load selected datasets into the application, downloading the entire datasets.

    Args:
        dataset_ids (list[str]): The list of dataset IDs to load.
        analyst_db (AnalystDB): The database to register into

    Returns:
        tuple[list[AnalystDataset], list[tuple[Callable, list, dict]]: A tuple of
            1. a dictionary of dataset names and data and
            2. a list of callbacks + arguments to that callback to be run in the background
               to pull datasets.

    Raises:
        ValueError: If the loading cannot be performed. This can be either (a) the small datasets exceed
                    our size threshold, or (b) a remote dataset is invalid (e.g. it is not snapshotted)."""
    if not DatasetSparkRecipe.should_use_spark_recipe():
        logger.warning(
            "Attempted to register remote datasets in an unsupported feature (should be unreachable through UI)."
        )
        raise ApplicationUsageException(
            UsageExceptionType.FEATURE_NOT_SUPPORTED,
            "Cannot use remote datasets with an unsupported DataRobot API version.",
        )
    datasets = [Dataset.get(d_id) for d_id in dataset_ids]

    # Dynamic datasets cannot be used with data wrangling.
    invalid_remote_datasets = [ds for ds in datasets if not ds.is_data_engine_eligible]

    if invalid_remote_datasets:
        raise ApplicationUsageException(
            UsageExceptionType.DATASETS_INVALID,
            f"Cannot register remote, dynamic datasets: {[ds.name for ds in invalid_remote_datasets]}.",
        )

    existing_dataset_names = await find_existing_dataset_names(analyst_db, datasets)

    if existing_dataset_names:
        raise ApplicationUsageException(
            UsageExceptionType.DATASET_ALREADY_USED,
            f"Cannot register already registered datasets: {existing_dataset_names}.",
        )

    background_tasks: list[tuple[Callable[..., Any], list[Any], dict[str, Any]]] = []

    downloaded_datasets = []

    if dataset_ids:
        with use_user_token(request, allow_use_builder_token=True):
            recipe = await load_or_create_spark_recipe(analyst_db, dataset_ids)

            await recipe.refresh()  # Clear out any removed datasets.

        await recipe.add_datasets([ds.id for ds in datasets])

        for ds in datasets:
            await analyst_db.register_dataset(
                AnalystDataset(name=ds.name),
                InternalDataSourceType.REMOTE_REGISTRY,
                file_size=0,
                external_id=ds.id,
                clobber=False,
            )

        background_tasks.append(
            (register_remote_datasets, [request, recipe, analyst_db, datasets], {})
        )

        for ds in datasets:
            downloaded_datasets.append(DownloadedRegistryDataset(name=ds.name))

    return downloaded_datasets, background_tasks


async def find_existing_dataset_names(
    analyst_db: AnalystDB, datasets: list[Dataset]
) -> list[str]:
    dataset_names = {ds.name for ds in datasets}
    existing_names = set(await analyst_db.list_analyst_datasets())
    return list(dataset_names & existing_names)


@telemetry.trace
async def register_remote_datasets(
    request: Request,
    recipe: DatasetSparkRecipe,
    analyst_db: AnalystDB,
    datasets: list[Dataset],
) -> None:
    for dataset in datasets:
        with use_user_token(request, allow_use_builder_token=True):
            preview = await recipe.preview_dataset(dataset)
        analyst_dataset = AnalystDataset(name=dataset.name, data=preview.response)

        await analyst_db.register_dataset(
            analyst_dataset,
            InternalDataSourceType.REMOTE_REGISTRY,
            file_size=0,
            external_id=dataset.id,
            original_column_types=preview.original_types,
            clobber=True,
        )


@telemetry.trace
async def sync_data_sources_and_datasets(
    request: Request,
    canonical_name: str,
    analyst_db: AnalystDB,
    data_store_id: str,
    selected_datasource_ids: ExternalDataSourcesSelection,
) -> tuple[
    list[DownloadedRegistryDataset],
    list[tuple[Callable[..., Any], list[Any], dict[str, Any]]],
]:
    """
    Register any data sets for data sources *not already present*.

    Args:
        analyst_db (str): The database.
        data_source_id (str): The data source in question.

    Returns:
        tuple[list[AnalystDataset], list[tuple[Callable, list, dict]]: A tuple of
            1. a dictionary of dataset names and data and
            2. a list of callbacks + arguments to that callback to be run in the background
               to pull datasets.
    """
    logger.debug(
        "Syncing data sources and detaset.",
        extra={"data_store_id": data_store_id, "canonical_name": canonical_name},
    )
    datasets = await analyst_db.list_analyst_dataset_metadata(
        data_source=ExternalDataStoreNameDataSourceType.from_name(canonical_name)
    )

    already_registered_paths = {ds.name for ds in datasets}

    new_datasources = [
        ds
        for ds in selected_datasource_ids.selected_data_sources
        if ds.path not in already_registered_paths
    ]

    downloaded = []
    background_tasks: list[tuple[Callable[..., Any], list[Any], dict[str, Any]]] = []

    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            "Initially registering data sources.",
            extra={
                "data_store_id": data_store_id,
                "canonical_name": canonical_name,
                "paths": [ds.path for ds in new_datasources],
            },
        )

    for ds in new_datasources:
        await analyst_db.register_dataset(
            AnalystDataset(name=ds.path),
            ExternalDataStoreNameDataSourceType.from_name(name=canonical_name),
            file_size=0,
            external_id=None,
            clobber=False,
        )
        downloaded.append(DownloadedRegistryDataset(name=ds.path))

    background_tasks.append(
        (register_datasource, [request, analyst_db, data_store_id, new_datasources], {})
    )

    return downloaded, background_tasks


@telemetry.meter_and_trace
async def register_datasource(
    request: Request,
    analyst_db: AnalystDB,
    data_store_id: str,
    datasources: list[ExternalDataSource],
) -> None:
    with use_user_token(request, allow_use_builder_token=True):
        recipe = await DataSourceRecipe.load_or_create(analyst_db, data_store_id)
        for ds in datasources:
            preview = await recipe.preview_datasource(ds)
            analyst_dataset = AnalystDataset(name=ds.path, data=preview.response)

            await analyst_db.register_dataset(
                analyst_dataset,
                ExternalDataStoreNameDataSourceType.from_name(
                    recipe.data_store.canonical_name
                ),
                file_size=0,
                external_id=None,
                clobber=True,
                original_column_types=preview.original_types,
            )


@telemetry.meter_and_trace
async def load_registry_datasets(
    dataset_ids: list[str],
    analyst_db: AnalystDB,
) -> list[DownloadedRegistryDataset]:
    """Load selected datasets into the application, downloading the entire datasets.

    Args:
        dataset_ids (list[str]): The list of dataset IDs to load.
        analyst_db (AnalystDB): The database to register into

    Returns:
        list[DownloadedRegistryDataset]: A list of dictionary of dataset names and data.

    Raises:
        ApplicationUsageException: If the loading cannot be performed. This can be either (a) the small datasets exceed
                                   our size threshold, or (b) a remote dataset is invalid (e.g. it is not snapshotted)
    """

    downloaded_datasets = []
    datasets = [Dataset.get(id_) for id_ in dataset_ids]

    if (
        sum([ds.size for ds in datasets if ds.size is not None])
        > MAX_REGISTRY_DATASET_SIZE
    ):
        raise ApplicationUsageException(
            UsageExceptionType.DATASETS_TOO_LARGE,
            f"The requested Data Registry datasets must total <= {int(MAX_REGISTRY_DATASET_SIZE)} bytes",
        )

    existing_datasets = await find_existing_dataset_names(analyst_db, datasets)

    if existing_datasets:
        raise ApplicationUsageException(
            UsageExceptionType.DATASET_ALREADY_USED,
            f"Some requested datasets are already present {existing_datasets}.",
        )

    for dataset in datasets:
        try:
            df = dataset.get_as_dataframe()
            result_dataset = AnalystDataset(name=dataset.name, data=df)
            logger.info(f"Successfully downloaded {dataset.name}")
        except Exception as e:
            logger.error(f"Failed to read dataset {dataset.name}: {str(e)}")
            downloaded_datasets.append(
                DownloadedRegistryDataset(name=dataset.name, error=str(e))
            )
            continue

        await analyst_db.register_dataset(
            result_dataset, InternalDataSourceType.REGISTRY, dataset.size or 0
        )
        downloaded_datasets.append(DownloadedRegistryDataset(name=result_dataset.name))

    return downloaded_datasets


async def _get_dictionary_batch(
    columns: list[str],
    df: pd.DataFrame,
    batch_size: int = 5,
    telemetry_json: dict[str, Any] | None = None,
    token_tracker: TokenUsageTracker | None = None,
) -> list[DataDictionaryColumn]:
    """Process a batch of columns to get their descriptions"""

    # Get sample data and stats for just these columns
    # Convert timestamps to ISO format strings for JSON serialization
    if telemetry_json is not None:
        telemetry_send = deepcopy(telemetry_json)
        telemetry_send["startTimestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    else:
        telemetry_send = None
    try:
        logger.debug(f"Processing batch of {len(columns)} columns")
        sample_data = {}
        logger.debug("Converting datetime columns to ISO format")
        num_samples = 10
        for col in columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                # Convert timestamps to ISO format strings
                sample_values = df[col].head(num_samples).copy()
                # NaT値を処理する
                sample_values = sample_values.apply(
                    lambda x: x.isoformat() if pd.notna(x) else None
                )
                sample_data[col] = sample_values.to_list()
            else:
                # For non-datetime columns, just take the samples as is
                sample_data[col] = df[col].head(num_samples).to_list()

        # Handle numeric summary
        numeric_summary = {}
        logger.debug("Calculating numeric summaries")
        for col in columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                desc = (
                    df[col]
                    .describe()
                    .reset_index()
                    .rename(columns={"index": "statistic", col: "value"})
                )
                numeric_summary[col] = desc.to_dict("list")

        # Get categories for non-numeric columns
        categories = []
        logger.debug("Getting categories for non-numeric columns")
        for column in columns:
            if not pd.api.types.is_numeric_dtype(df[column]):
                try:
                    # サンプルを取得してvalue_countsを計算
                    if len(df) > 1000:
                        sample = df[column].sample(n=1000, random_state=42)
                    else:
                        sample = df[column]

                    value_counts = sample.value_counts().head(10).reset_index()

                    # Convert any timestamp values to strings
                    if pd.api.types.is_datetime64_any_dtype(df[column]):
                        value_counts["index"] = value_counts["index"].map(
                            lambda x: x.isoformat() if pd.notna(x) else None
                        )
                    categories.append({column: value_counts["index"].tolist()})
                except Exception:
                    continue

        # Create messages for OpenAI
        messages: list[ChatCompletionMessageParam] = [
            ChatCompletionSystemMessageParam(
                role="system", content=prompts.SYSTEM_PROMPT_GET_DICTIONARY
            ),
            ChatCompletionUserMessageParam(
                role="user", content=f"Data:\n{sample_data}\n"
            ),
            ChatCompletionUserMessageParam(
                role="user", content=f"Statistical Summary:\n{numeric_summary}\n"
            ),
        ]

        if categories:
            messages.append(
                ChatCompletionUserMessageParam(
                    role="user", content=f"Categorical Values:\n{categories}\n"
                )
            )
        logger.debug(
            f"total_characters: {len(''.join([str(msg) for msg in messages]))}"
        )
        # Get descriptions from OpenAI
        async with AsyncLLMClient(token_tracker=token_tracker) as client:
            with telemetry.time(
                f"{_get_dictionary_batch.__module__}.{_get_dictionary_batch.__qualname__}.llm_call"
            ):
                (
                    completion,
                    completion_org,
                ) = await client.chat.completions.create_with_completion(
                    response_model=DictionaryGeneration,
                    model=ALTERNATIVE_LLM_SMALL,
                    messages=messages,
                    timeout=900,
                )

        # Convert to dictionary format
        descriptions = completion.to_dict()
        association_id = _get_datarobot_association_id(completion_org)
        logger.info(f"Association ID: {association_id}")

        if telemetry_send is not None:
            # query type added in parent function
            # submit telemetry
            asyncio.create_task(
                async_submit_actuals_to_datarobot(
                    association_id=association_id, telemetry_json=telemetry_send
                )
            )

        # Only return descriptions for requested columns
        return [
            DataDictionaryColumn(
                column=col,
                description=descriptions.get(col, "No description available"),
                data_type=str(df[col].dtype),
            )
            for col in columns
        ]

    except ValueError as e:
        logger.error(f"Invalid dictionary response: {str(e)}")
        return [
            DataDictionaryColumn(
                column=col,
                description="No valid description available",
                data_type=str(df[col].dtype),
            )
            for col in columns
        ]


_LLM_DETAIL_RE = re.compile(r'"detail"\s*:\s*"([^"]+)"')
_MODEL_NOT_FOUND_RE = re.compile(
    r"Model\s+(\S+?)\s+not found in catalog", re.IGNORECASE
)
_FRIENDLY_ERROR_MAX_LEN = 200
_UNWRAP_DEPTH_CAP = 3


def _unwrap_instructor_exception(exc: BaseException) -> BaseException:
    try:
        from instructor.core.exceptions import InstructorRetryException
    except ImportError:
        return exc

    current: BaseException = exc
    for _ in range(_UNWRAP_DEPTH_CAP):
        if not isinstance(current, InstructorRetryException):
            return current
        failed = getattr(current, "failed_attempts", None) or []
        if failed:
            last = failed[-1]
            inner = getattr(last, "exception", None)
            if isinstance(inner, BaseException):
                current = inner
                continue
        cause = cast(BaseException | None, current.__cause__)
        if isinstance(cause, BaseException):
            current = cause
            continue
        return cast(BaseException, current)
    return current


def _extract_detail(raw: str) -> str | None:
    match = _LLM_DETAIL_RE.search(raw)
    if not match:
        return None
    detail = match.group(1).strip()
    model_match = _MODEL_NOT_FOUND_RE.search(detail)
    if model_match:
        return f"model '{model_match.group(1).strip()}' not found in catalog"
    if len(detail) > 120:
        detail = detail[:120].rstrip() + "..."
    return detail or None


def _classify_llm_error(exc: BaseException) -> str:
    try:
        from openai import (
            APIConnectionError,
            APIError,
            APIStatusError,
            APITimeoutError,
            AuthenticationError,
            BadRequestError,
            InternalServerError,
            NotFoundError,
            PermissionDeniedError,
            RateLimitError,
        )
    except ImportError:
        return "The LLM service returned an unexpected error."

    if isinstance(exc, (asyncio.TimeoutError, APITimeoutError)):
        return "The LLM service did not respond in time. Please try again."
    if isinstance(exc, AuthenticationError):
        return "The configured LLM credentials are invalid or expired."
    if isinstance(exc, PermissionDeniedError):
        return "The configured LLM credentials are not authorized to use this model."
    if isinstance(exc, NotFoundError):
        return "The configured LLM model or deployment was not found."
    if isinstance(exc, RateLimitError):
        return "The LLM service is rate-limiting requests. Please try again shortly."
    if isinstance(exc, BadRequestError):
        return (
            "The LLM request was rejected as invalid. Check the configured model name."
        )
    if isinstance(exc, APIConnectionError):
        return "Could not reach the LLM service. Check network connectivity and endpoint URL."
    if isinstance(exc, InternalServerError):
        return (
            "The LLM service reported an internal error. "
            "The deployment may be misconfigured or down."
        )
    if isinstance(exc, APIStatusError):
        status = getattr(exc, "status_code", None) or getattr(
            getattr(exc, "response", None), "status_code", None
        )
        if status:
            return f"The LLM service returned an HTTP error (status {status})."
        return "The LLM service returned an HTTP error."
    if isinstance(exc, APIError):
        return "The LLM service returned an API error."
    return str(exc) or "The LLM service returned an unexpected error."


def _friendly_llm_error(exc: BaseException) -> str:
    root = _unwrap_instructor_exception(exc)
    base = _classify_llm_error(root)
    detail = _extract_detail(str(root))
    message = f"{base} Detail: {detail}" if detail else base
    message = message.replace("<", "").replace(">", "")
    if len(message) > _FRIENDLY_ERROR_MAX_LEN:
        message = message[: _FRIENDLY_ERROR_MAX_LEN - 3].rstrip() + "..."
    return message


@log_api_call
@telemetry.meter_and_trace
async def get_dictionary(
    dataset: AnalystDataset, telemetry_json: dict[str, Any] | None = None
) -> DataDictionary:
    """Process a single dataset with parallel column batch processing.

    Raises:
        RuntimeError: when every batch failed. Partial failures still return a
            dictionary with placeholder rows for the failed batches.
    """

    logger.info(f"Processing dataset {dataset.name} init")
    df_full = dataset.to_df()
    df = df_full.sample(n=min(10000, len(df_full)), random_state=42)

    logger.info(f"Processing dataset {dataset.name} with shape {df.shape}")

    if df.empty:
        logger.warning(f"Dataset {dataset.name} is empty")
        return DataDictionary(
            name=dataset.name,
            column_descriptions=[],
        )

    column_batches = [
        list(df.columns[i : i + DICTIONARY_BATCH_SIZE])
        for i in range(0, len(df.columns), DICTIONARY_BATCH_SIZE)
    ]
    logger.info(f"Created {len(column_batches)} batches for {len(df.columns)} columns")

    sem = asyncio.Semaphore(DICTIONARY_PARALLEL_BATCH_SIZE)

    async def throttled_get_dictionary_batch(
        batch: list[str],
    ) -> list[DataDictionaryColumn]:
        async with sem:
            return await asyncio.wait_for(
                _get_dictionary_batch(
                    batch,
                    df,
                    DICTIONARY_BATCH_SIZE,
                    telemetry_json=telemetry_json,
                ),
                timeout=DICTIONARY_TIMEOUT,
            )

    tasks = [throttled_get_dictionary_batch(batch) for batch in column_batches]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    dictionary: list[DataDictionaryColumn] = []
    failures: list[BaseException] = []
    for batch, result in zip(column_batches, results):
        if isinstance(result, BaseException):
            if isinstance(result, asyncio.TimeoutError):
                logger.warning(f"Timeout processing batch: {batch}")
            else:
                logger.error(f"Error processing batch {batch}: {result!s}")
            failures.append(result)
            dictionary.extend(
                DataDictionaryColumn(
                    column=col,
                    description="No Description Available",
                    data_type=str(df[col].dtype),
                )
                for col in batch
            )
        else:
            dictionary.extend(result)

    if failures and len(failures) == len(column_batches):
        raise RuntimeError(_friendly_llm_error(failures[0])) from failures[0]

    logger.info(
        f"Created dictionary with {len(dictionary)} entries for dataset {dataset.name}"
    )

    return DataDictionary(
        name=dataset.name,
        column_descriptions=dictionary,
    )


def find_imports(module: ModuleType) -> list[str]:
    """
    Get top-level third-party imports from a Python module.

    Args:
        module: Python module object to analyze

    Returns:
        list of third-party package names

    Example:
        >>> import my_module
        >>> imports = find_third_party_imports(my_module)
        >>> print(imports)  # ['pandas', 'numpy', 'requests']
    """
    try:
        # Get the source code of the module
        source = inspect.getsource(module)
        tree = ast.parse(source)

        stdlib_modules = set(sys.stdlib_module_names)
        third_party = set()

        # Only look at top-level imports
        for node in tree.body:
            if isinstance(node, ast.Import):
                for name in node.names:
                    module_name = name.name.split(".")[0]
                    if module_name not in stdlib_modules:
                        third_party.add(module_name)

            elif isinstance(node, ast.ImportFrom):
                if node.module is None:
                    continue
                module_name = node.module.split(".")[0]
                if module_name not in stdlib_modules:
                    third_party.add(module_name)

        return sorted(third_party)
    except Exception:
        return []


@telemetry.trace
def get_tools() -> list[Tool]:
    try:
        # find all functions defined in the tools module
        tool_functions = [func for func in dir(tools) if callable(getattr(tools, func))]

        # find the function signatures and doc strings
        tools_list = []
        for func_name in tool_functions:
            func = getattr(tools, func_name)
            signature = inspect.signature(func)
            docstring = inspect.getdoc(func)
            tools_list.append(
                Tool(
                    name=func_name,
                    signature=str(signature),
                    docstring=docstring,
                    function=func,
                )
            )
        return tools_list
    except Exception:
        return []


@telemetry.trace
async def _generate_run_charts_python_code(
    request: RunChartsRequest,
    validation_error: InvalidGeneratedCode | None = None,
    token_tracker: TokenUsageTracker | None = None,
    telemetry_json: dict[str, Any] | None = None,
) -> str:
    if telemetry_json is not None:
        telemetry_send = deepcopy(telemetry_json)
        telemetry_send["startTimestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    else:
        telemetry_send = None
    df = request.dataset.to_df()
    question = request.question
    dataframe_metadata = {
        "shape": {"rows": int(df.shape[0]), "columns": int(df.shape[1])},
        "statistics": df.describe(include="all").to_dict(),
        "dtypes": df.dtypes.astype(str).to_dict(),
    }
    messages: list[ChatCompletionMessageParam] = [
        ChatCompletionSystemMessageParam(
            role="system",
            content=prompts.SYSTEM_PROMPT_PLOTLY_CHART,
        ),
        ChatCompletionUserMessageParam(role="user", content=f"Question: {question}"),
        ChatCompletionUserMessageParam(
            role="user", content=f"Data Metadata:\n{dataframe_metadata}"
        ),
        ChatCompletionUserMessageParam(
            role="user", content=f"Data top 25 rows:\n{df.head(25).to_string()}"
        ),
    ]
    if validation_error:
        msg = type(validation_error).__name__ + f": {str(validation_error)}"
        messages.extend(
            [
                ChatCompletionUserMessageParam(
                    role="user",
                    content=f"Previous attempt failed with error: {msg}",
                ),
                ChatCompletionUserMessageParam(
                    role="user",
                    content=f"Failed code: {validation_error.code}",
                ),
                ChatCompletionUserMessageParam(
                    role="user",
                    content="Please generate new code that avoids this error.",
                ),
            ]
        )

    # Get response based on model mode
    async with AsyncLLMClient(token_tracker=token_tracker) as client:
        with telemetry.time(
            f"{_generate_run_charts_python_code.__module__}.{_generate_run_charts_python_code.__qualname__}.llm_call"
        ):
            (
                response,
                response_org,
            ) = await client.chat.completions.create_with_completion(
                response_model=CodeGeneration,
                model=ALTERNATIVE_LLM_BIG,
                temperature=0,
                messages=messages,
                timeout=900,
            )
    association_id = _get_datarobot_association_id(response_org)
    logger.info(f"Association ID: {association_id}")
    if telemetry_send is not None:
        # add query type to telemetry
        telemetry_send["query_type"] = "04_generate_run_charts_python_code"
        # submit telemetry
        asyncio.create_task(
            async_submit_actuals_to_datarobot(
                association_id=association_id, telemetry_json=telemetry_send
            )
        )
    return response.code


@telemetry.trace
async def _generate_run_analysis_python_code(
    request: RunAnalysisRequest,
    analyst_db: AnalystDB,
    validation_error: InvalidGeneratedCode | None = None,
    attempt: int = 0,
    token_tracker: TokenUsageTracker | None = None,
    telemetry_json: dict[str, Any] | None = None,
) -> CodeGeneration:
    """
    Generate Python analysis code based on JSON data and question.

    Parameters:
    - request: RunAnalysisRequest containing data and question
    - validation_errors: Past validation errors to include in prompt

    Returns:
    - Generated code
    """
    # Convert dictionary data structure to list of columns for all datasets
    logger.info("Starting code gen")
    if telemetry_json is not None:
        telemetry_send = deepcopy(telemetry_json)
        telemetry_send["startTimestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    else:
        telemetry_send = None

    all_columns = []
    all_descriptions = []
    all_data_types = []

    dictionaries = [
        await analyst_db.get_data_dictionary(name) for name in request.dataset_names
    ]
    for dictionary in dictionaries:
        if dictionary is None:
            continue
        for entry in dictionary.column_descriptions:
            all_columns.append(f"{dictionary.name}.{entry.column}")
            all_descriptions.append(entry.description)
            all_data_types.append(entry.data_type)

    # Create dictionary format for prompt
    dictionary_data = {
        "columns": all_columns,
        "descriptions": all_descriptions,
        "data_types": all_data_types,
    }

    # Get sample data and shape info for all datasets
    all_samples = []
    all_shapes = []

    logger.debug(f"datasets: {request.dataset_names}")
    for dataset_name in request.dataset_names:
        try:
            dataset = (await analyst_db.get_cleansed_dataset(dataset_name)).to_df()
        except Exception:
            dataset = (await analyst_db.get_dataset(dataset_name)).to_df()
        all_shapes.append(
            f"{dataset_name}: {dataset.shape[0]} rows x {dataset.shape[1]} columns"
        )
        # Limit sample to 10 rows
        sample_df = dataset.head(10)
        all_samples.append(f"{dataset_name}:\n{sample_df}")

    shape_info = "\n".join(all_shapes)
    sample_data = "\n\n".join(all_samples)
    logger.debug("Assembling messages")
    # Create messages for OpenAI
    messages: list[ChatCompletionMessageParam] = [
        ChatCompletionSystemMessageParam(
            role="system", content=prompts.SYSTEM_PROMPT_PYTHON_ANALYST
        ),
        ChatCompletionUserMessageParam(
            role="user", content=f"Business Question: {request.question}"
        ),
        ChatCompletionUserMessageParam(
            role="user",
            content=(
                f"Available dataset keys in dfs: {json.dumps(request.dataset_names)}\n"
                "IMPORTANT: Only use these exact strings as keys when accessing dfs. "
                "Do not derive key names from the business question or any other source."
            ),
        ),
        ChatCompletionUserMessageParam(
            role="user", content=f"Data Shapes:\n{shape_info}"
        ),
        ChatCompletionUserMessageParam(
            role="user", content=f"Sample Data:\n{sample_data}"
        ),
        ChatCompletionUserMessageParam(
            role="user",
            content=f"Data Dictionary:\n{json.dumps(dictionary_data, ensure_ascii=False)}",
        ),
    ]

    tools_list = get_tools()
    if len(tools_list) > 0:
        messages.append(
            ChatCompletionUserMessageParam(
                role="user",
                content="If it helps the analysis, you can optionally use following functions:\n"
                + "\n".join([str(t) for t in tools_list]),
            )
        )

    logger.debug(f"total_characters: {len(''.join([str(msg) for msg in messages]))}")
    # Add error context if available
    if validation_error:
        msg = type(validation_error).__name__ + f": {str(validation_error)}"
        messages.extend(
            [
                ChatCompletionUserMessageParam(
                    role="user",
                    content=f"Previous attempt failed with error: {msg}",
                ),
                ChatCompletionUserMessageParam(
                    role="user",
                    content=f"Failed code: {validation_error.code}",
                ),
                ChatCompletionUserMessageParam(
                    role="user",
                    content="Please generate new code that avoids this error.",
                ),
            ]
        )
        if attempt > 2:
            messages.append(
                ChatCompletionUserMessageParam(
                    role="user",
                    content="Convert the dataframe to pandas!",
                )
            )
    logger.info("Running Code Gen")
    logger.debug(messages)
    async with AsyncLLMClient(token_tracker=token_tracker) as client:
        with telemetry.time(
            f"{_generate_run_analysis_python_code.__module__}.{_generate_run_analysis_python_code.__qualname__}.llm_call"
        ):
            (
                completion,
                completion_org,
            ) = await client.chat.completions.create_with_completion(
                response_model=CodeGeneration,
                model=ALTERNATIVE_LLM_BIG,
                temperature=0.1,
                messages=messages,
                max_retries=10,
                timeout=900,
            )
    association_id = _get_datarobot_association_id(completion_org)
    logger.info(f"Association ID: {association_id}")

    if telemetry_send is not None:
        # add query type to telemetry
        telemetry_send["query_type"] = "03_generate_code_file"
        # submit telemetry
        asyncio.create_task(
            async_submit_actuals_to_datarobot(
                association_id=association_id, telemetry_json=telemetry_send
            )
        )
    logger.info("Code Gen complete")
    return completion


@telemetry.meter_and_trace
async def cleanse_dataframe(dataset: AnalystDataset) -> CleansedDataset:
    """Clean and standardize multiple pandas DataFrames in parallel.

    Args:
        datasets: List of AnalystDataset objects to clean
    Returns:
        List of CleansedDataset objects containing cleaned data and reports
    Raises:
        ValueError: If a dataset is empty
    """
    logger.info(f"Cleansing dataset: {dataset.name}")

    if dataset.to_df().empty:
        raise ValueError(f"Dataset {dataset.name} is empty")

    df = dataset.to_df()
    sample_df = df.sample(n=min(500, len(df)), random_state=42)

    results = []
    for col in df.columns:
        results.append(process_column(df, col, sample_df))

    # Create new DataFrame from processed columns
    new_columns = {}
    reports = []

    for new_name, series, report in results:
        new_columns[new_name] = series
        reports.append(report)

    cleaned_df = pd.DataFrame(new_columns)
    add_summary_statistics(cleaned_df, reports)

    return CleansedDataset(
        dataset=AnalystDataset(
            name=dataset.name,
            data=cleaned_df,
        ),
        cleaning_report=reports,
    )


@log_api_call
@telemetry.meter_and_trace
async def summarize_conversation(
    messages: list[ChatCompletionMessageParam],
    token_tracker: TokenUsageTracker | None = None,
    telemetry_json: dict[str, Any] | None = None,
) -> str:
    """Summarize a conversation history, when getting close to model's context window limit.

    Args:
        messages: list of message dictionaries with 'role' and 'content' fields
        token_tracker: Optional token usage tracker

    Returns:
        str: Summary of the conversation

    Raises:
        Exception: If summarization fails (network, LLM, parsing errors)
    """

    if telemetry_json is not None:
        telemetry_send = deepcopy(telemetry_json)
        telemetry_send["startTimestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    else:
        telemetry_send = None

    class ConversationSummary(BaseModel):
        summary: str

    try:
        messages_str = "\n".join(
            [f"{msg['role']}: {msg['content']}" for msg in messages]
        )

        token_count = count_messages_tokens(messages, ALTERNATIVE_LLM_SMALL)
        logger.info(
            f"Summarizing conversation: {token_count} tokens, {len(messages)} messages"
        )

        prompt_messages: list[ChatCompletionMessageParam] = [
            ChatCompletionSystemMessageParam(
                content=prompts.SYSTEM_PROMPT_SUMMARIZE_CONVERSATION,
                role="system",
            ),
            ChatCompletionUserMessageParam(
                content=f"Conversation History:\n{messages_str}",
                role="user",
            ),
        ]

        async with AsyncLLMClient(token_tracker=token_tracker) as client:
            with telemetry.time(
                f"{summarize_conversation.__module__}.{summarize_conversation.__qualname__}.llm_call"
            ):
                completion: ConversationSummary = await client.chat.completions.create(
                    response_model=ConversationSummary,
                    model=ALTERNATIVE_LLM_SMALL,
                    messages=prompt_messages,
                    timeout=900,
                )

        logger.info(f"Summary created: {len(completion.summary)} characters")
        return completion.summary

    except Exception as e:
        logger.error(f"Error preparing messages for summarization: {str(e)}")
        raise


@log_api_call
@telemetry.meter_and_trace
async def rephrase_message(
    messages: ChatRequest,
    token_tracker: TokenUsageTracker | None = None,
    telemetry_json: dict[str, Any] | None = None,
) -> str:
    """Process chat messages history and return a new question

    Args:
        messages: list of message dictionaries with 'role' and 'content' fields
        token_tracker: Optional token usage tracker

    Returns:
        Dict[str, str]: Dictionary containing response content
    """
    if telemetry_json is not None:
        telemetry_send = deepcopy(telemetry_json)
        telemetry_send["startTimestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    else:
        telemetry_send = None

    # Debug logging
    token_count = count_messages_tokens(messages.messages, ALTERNATIVE_LLM_BIG)

    logger.info(
        f"DEBUG rephrase_message: {token_count} tokens, {len(messages.messages)} messages"
    )

    # Build prompt: system message + actual conversation history
    prompt_messages: list[ChatCompletionMessageParam] = [
        ChatCompletionSystemMessageParam(
            content=prompts.SYSTEM_PROMPT_REPHRASE_MESSAGE,
            role="system",
        )
    ]

    # Add the actual conversation messages (already includes summary if present)
    prompt_messages.extend(messages.messages)

    async with AsyncLLMClient(token_tracker=token_tracker) as client:
        with telemetry.time(
            f"{rephrase_message.__module__}.{rephrase_message.__qualname__}.llm_call"
        ):
            (
                completion,
                completion_org,
            ) = await client.chat.completions.create_with_completion(
                response_model=EnhancedQuestionGeneration,
                model=ALTERNATIVE_LLM_BIG,
                messages=prompt_messages,
                timeout=900,
            )

    association_id = _get_datarobot_association_id(completion_org)
    logger.info(f"Association ID: {association_id}")

    if telemetry_send is not None:
        # add query type to telemetry
        telemetry_send["query_type"] = "02_rephrase"
        # submit telemetry
        asyncio.create_task(
            async_submit_actuals_to_datarobot(
                association_id=association_id, telemetry_json=telemetry_send
            )
        )
    return completion.enhanced_user_message


@reflect_code_generation_errors(max_attempts=7)
@telemetry.trace
async def _run_charts(
    request: RunChartsRequest,
    exception_history: list[InvalidGeneratedCode] | None = None,
    token_tracker: TokenUsageTracker | None = None,
    telemetry_json: dict[str, Any] | None = None,
) -> RunChartsResult:
    """Generate and validate chart code with retry logic"""
    # Create messages for OpenAI
    start_time = datetime.now()

    if not request.dataset:
        raise ValueError(VALUE_ERROR_MESSAGE)

    df = request.dataset.to_df()
    if exception_history is None:
        exception_history = []

    code = await _generate_run_charts_python_code(
        request,
        next(iter(exception_history[::-1]), None),
        token_tracker,
        telemetry_json=telemetry_json,
    )
    try:
        result = execute_python(
            modules={
                "pd": pd,
                "np": np,
                "go": go,
                "scipy": scipy,
            },
            functions={
                "make_subplots": make_subplots,
            },
            expected_function="create_charts",
            code=code,
            input_data=df,
            output_type=ChartGenerationExecutionResult,
            allowed_modules={
                "pandas",
                "numpy",
                "plotly",
                "scipy",
                "datetime",
            },
        )
    except InvalidGeneratedCode:
        raise
    except Exception as e:
        raise InvalidGeneratedCode(code=code, exception=e)

    duration = datetime.now() - start_time

    return RunChartsResult(
        status="success",
        code=code,
        fig1_json=result.fig1.to_json(),
        fig2_json=result.fig2.to_json(),
        metadata=RunAnalysisResultMetadata(
            duration=duration.total_seconds(),
            attempts=len(exception_history) + 1,
        ),
    )


@log_api_call
@telemetry.meter_and_trace
async def run_charts(
    request: RunChartsRequest,
    token_tracker: TokenUsageTracker | None = None,
    telemetry_json: dict[str, Any] | None = None,
) -> RunChartsResult:
    """Execute analysis workflow on datasets."""
    try:
        chart_result = await _run_charts(
            request, token_tracker=token_tracker, telemetry_json=telemetry_json
        )
        return chart_result
    except ValidationError as e:
        logger.error(f"Failed to parse LLM response for charts: {e}")
        user_friendly_error = ValueError(
            "Unable to generate charts for this analysis. "
            "The data structure may not be suitable for visualization. "
            "The analysis results are still available."
        )
        return RunChartsResult(
            status="error",
            metadata=RunAnalysisResultMetadata(
                duration=0,
                attempts=1,
                exception=AnalysisError.from_value_error(user_friendly_error),
            ),
        )
    except MaxReflectionAttempts as e:
        return RunChartsResult(
            status="error",
            metadata=RunAnalysisResultMetadata(
                duration=e.duration,
                attempts=len(e.exception_history) if e.exception_history else 0,
                exception=AnalysisError.from_max_reflection_exception(e),
            ),
        )


@log_api_call
@telemetry.meter_and_trace
async def get_business_analysis(
    request: GetBusinessAnalysisRequest,
    token_tracker: TokenUsageTracker | None = None,
    telemetry_json: dict[str, Any] | None = None,
) -> GetBusinessAnalysisResult:
    """
    Generate business analysis based on data and question.

    Parameters:
    - request: BusinessAnalysisRequest containing data and question

    Returns:
    - Dictionary containing analysis components
    """
    try:
        # Convert JSON data to DataFrame for analysis
        start = datetime.now()
        if telemetry_json is not None:
            telemetry_send = deepcopy(telemetry_json)
            telemetry_send["startTimestamp"] = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        else:
            telemetry_send = None
        df = request.dataset.to_df()

        initial_rows = 750

        df_csv, _ = estimate_csv_rows_for_token_limit(df, MAX_CSV_TOKENS, initial_rows)

        # Create messages for OpenAI
        messages: list[ChatCompletionMessageParam] = [
            ChatCompletionSystemMessageParam(
                role="system", content=prompts.SYSTEM_PROMPT_BUSINESS_ANALYSIS
            ),
            ChatCompletionUserMessageParam(
                role="user",
                content=f"Business Question: {request.question}",
            ),
            ChatCompletionUserMessageParam(
                role="user", content=f"Analyzed Data:\n{df_csv}"
            ),
            ChatCompletionUserMessageParam(
                role="user",
                content=f"Data Dictionary:\n{request.dictionary.model_dump_json()}",
            ),
        ]
        async with AsyncLLMClient(token_tracker=token_tracker) as client:
            with telemetry.time(
                f"{get_business_analysis.__module__}.{get_business_analysis.__qualname__}.llm_call"
            ):
                (
                    completion,
                    completion_org,
                ) = await client.chat.completions.create_with_completion(
                    response_model=BusinessAnalysisGeneration,
                    model=ALTERNATIVE_LLM_BIG,
                    temperature=0.1,
                    messages=messages,
                    timeout=900,
                )
        association_id = _get_datarobot_association_id(completion_org)
        logger.info(f"Association ID: {association_id}")

        if telemetry_send is not None:
            # add query type to telemetry
            # although it's called the same time as 04, change number for clarity
            telemetry_send["query_type"] = "05_generate_business_analysis"
            # submit telemetry
            asyncio.create_task(
                async_submit_actuals_to_datarobot(
                    association_id=association_id, telemetry_json=telemetry_send
                )
            )
        duration = (datetime.now() - start).total_seconds()
        # Ensure all response fields are present
        metadata = GetBusinessAnalysisMetadata(
            duration=duration,
            question=request.question,
            rows_analyzed=len(df),
            columns_analyzed=len(df.columns),
        )
        return GetBusinessAnalysisResult(
            status="success",
            **completion.model_dump(),
            metadata=metadata,
        )

    except ValidationError as e:
        logger.error(f"Failed to parse LLM response for business analysis: {e}")
        user_friendly_error = ValueError(
            "Unable to generate business insights for this analysis. "
            "The analysis results are still available. "
            "Try simplifying your question or checking your data."
        )
        return GetBusinessAnalysisResult(
            status="error",
            metadata=GetBusinessAnalysisMetadata(
                exception=AnalysisError.from_value_error(user_friendly_error)
            ),
            additional_insights="",
            follow_up_questions=[],
            bottom_line="",
        )
    except ValueError as e:
        logger.error(f"ValueError during business analysis generation: {e}")
        return GetBusinessAnalysisResult(
            status="error",
            metadata=GetBusinessAnalysisMetadata(
                exception=AnalysisError.from_value_error(e)
            ),
            additional_insights="",
            follow_up_questions=[],
            bottom_line="",
        )
    except Exception as e:
        msg = type(e).__name__ + f": {str(e)}"
        logger.error(f"Error in get_business_analysis: {msg}")
        return GetBusinessAnalysisResult(
            status="error",
            metadata=GetBusinessAnalysisMetadata(exception_str=msg),
            additional_insights="",
            follow_up_questions=[],
            bottom_line="",
        )


@reflect_code_generation_errors(max_attempts=7)
@telemetry.trace
async def _run_analysis(
    request: RunAnalysisRequest,
    analyst_db: AnalystDB | None = None,
    exception_history: list[InvalidGeneratedCode] | None = None,
    token_tracker: TokenUsageTracker | None = None,
    telemetry_json: dict[str, Any] | None = None,
    analysis_context: RunCompleteAnalysisRequestContext | None = None,
) -> RunAnalysisResult:
    start_time = datetime.now()

    if analysis_context:
        analyst_db = analysis_context.analyst_db
        token_tracker = analysis_context.token_tracker

    if analyst_db is None:
        raise ValueError("analyst_db is required")

    if not request.dataset_names:
        raise ValueError(VALUE_ERROR_MESSAGE)

    if exception_history is None:
        exception_history = []
    logger.info(f"Running analysis (attempt {len(exception_history)})")

    if (
        analysis_context
        and analysis_context.assistant_message_id
        and analysis_context.assistant_message
    ):
        analysis_context.assistant_message.step_value = "GENERATING_QUERY"
        analysis_context.assistant_message.step_reattempt = len(exception_history)
        analysis_context.stage_message_update()

    completion = await _generate_run_analysis_python_code(
        request,
        analyst_db,
        next(iter(exception_history[::-1]), None),
        attempt=len(exception_history),
        token_tracker=token_tracker,
        telemetry_json=telemetry_json,
    )
    code = completion.code
    logger.info("Code generated, preparing execution")

    if (
        analysis_context
        and analysis_context.assistant_message_id
        and analysis_context.assistant_message
    ):
        analysis_context.assistant_message.step_value = "RUNNING_QUERY"
        analysis_context.assistant_message.step_reattempt = len(exception_history)
        analysis_context.stage_message_update()

    dataframes: dict[str, pd.DataFrame] = {}

    for dataset_name in request.dataset_names:
        try:
            dataset = (
                await analyst_db.get_cleansed_dataset(dataset_name, max_rows=None)
            ).to_df()
        except Exception:
            dataset = (
                await analyst_db.get_dataset(dataset_name, max_rows=None)
            ).to_df()
        dataframes[dataset_name] = dataset
    functions = {}
    tool_functions = get_tools()
    for tool in tool_functions:
        functions[tool.name] = tool.function
    try:
        logger.info("Executing")
        result = execute_python(
            modules={
                "pd": pd,
                "np": np,
                "sm": sm,
                "scipy": scipy,
                "sklearn": sklearn,
            },
            functions=functions,
            expected_function="analyze_data",
            code=code,
            input_data=dataframes,
            output_type=AnalystDataset,
            allowed_modules={
                "pandas",
                "numpy",
                "scipy",
                "sklearn",
                "statsmodels",
                "datetime",
                *find_imports(tools),
            },
        )
    except InvalidGeneratedCode:
        raise
    except Exception as e:
        raise InvalidGeneratedCode(code=code, exception=e)
    logger.info("Execution done")
    duration = datetime.now() - start_time
    return RunAnalysisResult(
        status="success",
        code=code,
        dataset=result,
        metadata=RunAnalysisResultMetadata(
            duration=duration.total_seconds(),
            attempts=len(exception_history) + 1,
            datasets_analyzed=len(dataframes),
            total_rows_analyzed=sum(
                len(df) for df in dataframes.values() if not df.empty
            ),
            total_columns_analyzed=sum(
                len(df.columns) for df in dataframes.values() if not df.empty
            ),
        ),
        used_datasets=completion.used_datasets,
    )


@log_api_call
async def run_analysis(
    request: RunAnalysisRequest,
    analyst_db: AnalystDB | None = None,
    token_tracker: TokenUsageTracker | None = None,
    telemetry_json: dict[str, Any] | None = None,
    analysis_context: RunCompleteAnalysisRequestContext | None = None,
) -> RunAnalysisResult:
    """Execute analysis workflow on datasets."""
    logger.debug("Entering run_analysis")
    log_memory()
    try:
        return await _run_analysis(
            request,
            analyst_db=analyst_db,
            token_tracker=token_tracker,
            telemetry_json=telemetry_json,
            analysis_context=analysis_context,
        )
    except MaxReflectionAttempts as e:
        return RunAnalysisResult(
            status="error",
            metadata=RunAnalysisResultMetadata(
                duration=e.duration,
                attempts=len(e.exception_history) if e.exception_history else 0,
                exception=AnalysisError.from_max_reflection_exception(e),
            ),
        )
    except ValidationError as e:
        logger.error(f"Failed to parse LLM response for analysis: {e}")
        user_friendly_error = ValueError(
            "Unable to complete the analysis. "
            "This could be due to data quality issues, complex dataset structure, or the question being too complex. "
            "Try simplifying your question or verifying your data quality."
        )
        return RunAnalysisResult(
            status="error",
            metadata=RunAnalysisResultMetadata(
                duration=0,
                attempts=1,
                exception=AnalysisError.from_value_error(user_friendly_error),
            ),
        )
    except ValueError as e:
        return RunAnalysisResult(
            status="error",
            metadata=RunAnalysisResultMetadata(
                duration=0,
                attempts=1,
                exception=AnalysisError.from_value_error(e),
            ),
        )


async def _generate_database_analysis_code(
    database: DatabaseOperator[Any],
    request: RunDatabaseAnalysisRequest,
    analyst_db: AnalystDB,
    validation_error: InvalidGeneratedCode | None = None,
    token_tracker: TokenUsageTracker | None = None,
    telemetry_json: dict[str, Any] | None = None,
) -> str:
    """
    Generate Snowflake SQL analysis code based on data samples and question.

    Parameters:
    - request: DatabaseAnalysisRequest containing data samples and question

    Returns:
    - Dictionary containing generated code and description
    """
    if telemetry_json is not None:
        telemetry_send = deepcopy(telemetry_json)
        telemetry_send["startTimestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    else:
        telemetry_send = None

    # Convert dictionary data structure to list of columns for all tables
    dictionaries = [
        (
            await analyst_db.get_data_dictionary(name),
            await analyst_db.get_dataset_metadata(name),
        )
        for name in request.dataset_names
    ]

    for dictionary, metadata in dictionaries:
        if dictionary:
            if metadata and metadata.original_column_types:
                for column in dictionary.column_descriptions:
                    if original_type := metadata.original_column_types.get(
                        column.column
                    ):
                        column.data_type = original_type
            dictionary.name = database.query_friendly_name(dictionary.name)
    all_tables_info = [
        d.model_dump(mode="json") for d, m in dictionaries if d is not None
    ]

    # Get sample data for all tables
    all_samples = []

    for table in request.dataset_names:
        df = (await analyst_db.get_dataset(table)).to_df()
        schema_str, table_str = table.split(".")

        # friendly_name = database.query_friendly_name(table)

        sample_str = (
            f"Schema: {schema_str}, Table: {table_str}\n{df.head(10).to_string()}"
        )
        all_samples.append(sample_str)

    # Create messages for OpenAI
    messages: list[ChatCompletionMessageParam] = [
        database.get_system_prompt(),
        ChatCompletionUserMessageParam(
            content=f"Business Question: {request.question}",
            role="user",
        ),
        ChatCompletionUserMessageParam(
            content=f"Sample Data:\n{chr(10).join(all_samples)}", role="user"
        ),
        ChatCompletionUserMessageParam(
            content=f"Data Dictionary:\n{json.dumps(all_tables_info, ensure_ascii=False)}",
            role="user",
        ),
    ]
    if validation_error:
        msg = type(validation_error).__name__ + f": {str(validation_error)}"
        messages.extend(
            [
                ChatCompletionUserMessageParam(
                    role="user",
                    content=f"Previous attempt failed with error: {msg}",
                ),
                ChatCompletionUserMessageParam(
                    role="user",
                    content=f"Failed code: {validation_error.code}",
                ),
                ChatCompletionUserMessageParam(
                    role="user",
                    content="Please generate new code that avoids this error.",
                ),
            ]
        )

    # Get response from OpenAI
    async with AsyncLLMClient(token_tracker=token_tracker) as client:
        with telemetry.time(
            f"{_generate_database_analysis_code.__module__}.{_generate_database_analysis_code.__qualname__}.llm_call"
        ):
            try:
                (
                    completion,
                    completion_org,
                ) = await client.chat.completions.create_with_completion(
                    response_model=DatabaseAnalysisCodeGeneration,
                    model=ALTERNATIVE_LLM_BIG,
                    temperature=0.1,
                    messages=messages,
                    timeout=900,
                )
            except ValidationError as e:
                logger.error(f"LLM returned invalid database analysis response: {e}")
                raise ValueError(
                    "Unable to analyze your data. "
                    "This could be due to data quality issues, complex dataset structure, or the question being too complex. "
                    "Try simplifying your question or checking your data."
                ) from e
    association_id = _get_datarobot_association_id(completion_org)
    logger.info(f"Association ID: {association_id}")

    if telemetry_send is not None:
        # add query type to telemetry
        telemetry_send["query_type"] = "03_generate_code_database"
        # submit telemetry
        asyncio.create_task(
            async_submit_actuals_to_datarobot(
                association_id=association_id, telemetry_json=telemetry_send
            )
        )
    return str(completion.code)


@reflect_code_generation_errors(max_attempts=7)
@telemetry.trace
async def _run_database_analysis(
    request: RunDatabaseAnalysisRequest,
    analyst_db: AnalystDB | None = None,
    database_override: DatabaseOperator[Any] | None = None,
    exception_history: list[InvalidGeneratedCode] | None = None,
    token_tracker: TokenUsageTracker | None = None,
    telemetry_json: dict[str, Any] | None = None,
    analysis_context: RunCompleteAnalysisRequestContext | None = None,
) -> RunDatabaseAnalysisResult:
    start_time = datetime.now()
    if analysis_context:
        analyst_db = analysis_context.analyst_db
        token_tracker = analysis_context.token_tracker
        database_override = database_override or analysis_context.database

    if analyst_db is None:
        raise ValueError("analyst_db is required")

    if not request.dataset_names:
        raise ValueError(VALUE_ERROR_MESSAGE)

    if exception_history is None:
        exception_history = []

    database = (
        get_external_database() if database_override is None else database_override
    )

    if (
        analysis_context
        and analysis_context.assistant_message_id
        and analysis_context.assistant_message
    ):
        analysis_context.assistant_message.step_value = "GENERATING_QUERY"
        analysis_context.assistant_message.step_reattempt = len(exception_history)
        analysis_context.stage_message_update()

    sql_code = await _generate_database_analysis_code(
        database,
        request,
        analyst_db,
        next(iter(exception_history[::-1]), None),
        token_tracker,
        telemetry_json=telemetry_json,
    )
    if (
        analysis_context
        and analysis_context.assistant_message_id
        and analysis_context.assistant_message
    ):
        analysis_context.assistant_message.step_value = "RUNNING_QUERY"
        analysis_context.assistant_message.step_reattempt = len(exception_history)
        analysis_context.stage_message_update()

    try:
        results = await database.execute_query(query=sql_code)
        results = cast(list[dict[str, Any]], results)
        duration = datetime.now() - start_time

    except InvalidGeneratedCode:
        raise
    except Exception as e:
        raise InvalidGeneratedCode(code=sql_code, exception=e)
    return RunDatabaseAnalysisResult(
        status="success",
        code=sql_code,
        dataset=AnalystDataset(
            data=results,
        ),
        metadata=RunDatabaseAnalysisResultMetadata(
            duration=duration.total_seconds(),
            attempts=len(exception_history),
            datasets_analyzed=len(request.dataset_names),
            # total_columns_analyzed=sum(len(ds.columns) for ds in request.datasets),
        ),
    )


@log_api_call
@telemetry.meter_and_trace
async def run_database_analysis(
    request: RunDatabaseAnalysisRequest,
    analyst_db: AnalystDB | None = None,
    database_override: DatabaseOperator[Any] | None = None,
    token_tracker: TokenUsageTracker | None = None,
    telemetry_json: dict[str, Any] | None = None,
    analysis_context: RunCompleteAnalysisRequestContext | None = None,
) -> RunDatabaseAnalysisResult:
    """Execute analysis workflow on datasets."""
    try:
        return await _run_database_analysis(
            request,
            analyst_db,
            database_override=database_override,
            token_tracker=token_tracker,
            telemetry_json=telemetry_json,
            analysis_context=analysis_context,
        )
    except MaxReflectionAttempts as e:
        return RunDatabaseAnalysisResult(
            status="error",
            metadata=RunDatabaseAnalysisResultMetadata(
                duration=e.duration,
                attempts=len(e.exception_history) if e.exception_history else 0,
                exception=AnalysisError.from_max_reflection_exception(e),
            ),
        )
    except ValueError as e:
        return RunDatabaseAnalysisResult(
            status="error",
            metadata=RunDatabaseAnalysisResultMetadata(
                duration=0,
                attempts=1,
                exception=AnalysisError.from_value_error(e),
            ),
        )


# Type definitions
@dataclass
class AnalysisGenerationError:
    message: str
    original_error: BaseException | None = None


@dataclass
class RunCompleteAnalysisRequestContext:
    chat_request: ChatRequest
    request: Request | None
    data_source: DataSourceType
    dataset_metadata: list[DatasetMetadata]
    analyst_db: AnalystDB
    chat_id: str
    user_message_id: str
    enable_chart_generation: bool
    enable_business_insights: bool
    token_tracker: TokenUsageTracker

    user_message: AnalystChatMessage | None = None
    assistant_message_id: str | None = None
    assistant_message: AnalystChatMessage | None = None
    database: DatabaseOperator[Any] | None = None
    recipe: BaseRecipe | None = None

    message_update_task: asyncio.Task[Any] | None = None

    def stage_message_update(
        self, target: Literal["assistant", "user"] = "assistant"
    ) -> None:
        target_message_id = (
            self.assistant_message_id if target == "assistant" else self.user_message_id
        )
        target_message = copy.copy(
            self.assistant_message if target == "assistant" else self.user_message
        )
        if target_message:
            target_message.step = copy.copy(target_message.step)

        if not target_message or not target_message_id:
            return

        previous_task = self.message_update_task

        async def update_task() -> None:
            if previous_task:
                await previous_task

            await self.analyst_db.update_chat_message(
                message_id=target_message_id,
                message=target_message,
            )

        self.message_update_task = asyncio.create_task(update_task())

    async def await_message_update(self) -> None:
        if self.message_update_task:
            await self.message_update_task
            self.message_update_task = None


async def execute_business_analysis_and_charts(
    analysis_result: RunAnalysisResult | RunDatabaseAnalysisResult,
    enhanced_message: str,
    token_tracker: TokenUsageTracker | None = None,
    enable_chart_generation: bool = True,
    enable_business_insights: bool = True,
    telemetry_json: dict[str, Any] | None = None,
) -> tuple[
    RunChartsResult | BaseException | None,
    GetBusinessAnalysisResult | BaseException | None,
]:
    analysis_result.dataset = cast(AnalystDataset, analysis_result.dataset)
    # Prepare both requests
    chart_request = RunChartsRequest(
        dataset=analysis_result.dataset,
        question=enhanced_message,
    )

    business_request = GetBusinessAnalysisRequest(
        dataset=analysis_result.dataset,
        dictionary=DataDictionary.from_analyst_df(analysis_result.dataset.to_df()),
        question=enhanced_message,
    )

    if enable_chart_generation and enable_business_insights:
        # Run both analyses concurrently
        result = await asyncio.gather(
            run_charts(chart_request, token_tracker, telemetry_json=telemetry_json),
            get_business_analysis(
                business_request, token_tracker, telemetry_json=telemetry_json
            ),
            return_exceptions=True,
        )

        return (result[0], result[1])
    elif enable_chart_generation:
        charts_result = await run_charts(
            chart_request, token_tracker, telemetry_json=telemetry_json
        )
        return charts_result, None
    else:
        business_result = await get_business_analysis(
            business_request, token_tracker, telemetry_json=telemetry_json
        )
        return None, business_result


@telemetry.meter_and_trace
async def run_complete_analysis(
    chat_request: ChatRequest,
    data_source: DataSourceType,
    dataset_metadata: list[DatasetMetadata],
    analyst_db: AnalystDB,
    chat_id: str,
    message_id: str,
    request: Request | None,
    enable_chart_generation: bool = True,
    enable_business_insights: bool = True,
    telemetry_json: dict[str, Any] | None = None,
) -> AsyncGenerator[Component | AnalysisGenerationError, None]:
    datasets_names = [ds.name for ds in dataset_metadata]
    token_tracker = TokenUsageTracker(strategy=HeuristicTokenCountingStrategy())
    analysis_context = RunCompleteAnalysisRequestContext(
        chat_request=chat_request,
        request=request,
        data_source=data_source,
        dataset_metadata=dataset_metadata,
        analyst_db=analyst_db,
        chat_id=chat_id,
        user_message_id=message_id,
        enable_chart_generation=enable_chart_generation,
        enable_business_insights=enable_business_insights,
        token_tracker=token_tracker,
    )

    user_message = await analyst_db.get_chat_message(message_id=message_id)
    analysis_context.user_message = user_message
    if user_message is None or user_message.role != "user":
        yield AnalysisGenerationError("Message not found")

        return
    # Get enhanced message
    if telemetry_json is not None:
        telemetry_json["chat_id"] = chat_id
        telemetry_json["chat_seq"] = len(chat_request.messages)
        telemetry_json["data_source"] = (
            data_source.value
            if isinstance(data_source, InternalDataSourceType)
            else data_source.name
        )
        telemetry_json["datasets_names"] = datasets_names
        telemetry_json["enable_chart_generation"] = enable_chart_generation
        telemetry_json["enable_business_insights"] = enable_business_insights
    try:
        logger.info("Getting rephrased question...")
        enhanced_message = await rephrase_message(
            chat_request, token_tracker=token_tracker, telemetry_json=telemetry_json
        )
        logger.info("Getting rephrased question done")

        yield enhanced_message

    except Exception as e:
        logger.error(f"Error rephrasing message: {e}", exc_info=True)
        user_message.error = (
            f"Failed to process your question: {_friendly_llm_error(e)}"
        )
        user_message.in_progress = False
        analysis_context.stage_message_update(target="user")
        await analysis_context.await_message_update()
        yield AnalysisGenerationError(user_message.error)

        return

    assistant_message = AnalystChatMessage(
        role="assistant",
        content=enhanced_message,
        components=[EnhancedQuestionGeneration(enhanced_user_message=enhanced_message)],
        in_progress=True,
    )
    should_test_connection = (
        data_source == InternalDataSourceType.DATABASE
        or data_source == InternalDataSourceType.REMOTE_REGISTRY
        or isinstance(data_source, ExternalDataStoreNameDataSourceType)
    )
    assistant_message.step_value = (
        "TESTING_CONNECTION" if should_test_connection else "GENERATING_QUERY"
    )
    analysis_context.assistant_message = assistant_message

    analysis_context.assistant_message_id = await analyst_db.add_chat_message(
        chat_id=chat_id,
        message=assistant_message,
    )
    analysis_context.stage_message_update()

    user_message.in_progress = False
    analysis_context.stage_message_update(target="user")
    # Run main analysis
    logger.info("Start main analysis")
    try:
        is_database = data_source == InternalDataSourceType.DATABASE
        logger.info("Getting analysis result...")
        log_memory()

        analysis_result: RunAnalysisResult | RunDatabaseAnalysisResult

        recipe: BaseRecipe

        if is_database:
            logger.info("Running database analysis")
            analysis_result = await run_database_analysis(
                RunDatabaseAnalysisRequest(
                    dataset_names=datasets_names,
                    question=enhanced_message,
                ),
                analyst_db,
                token_tracker=token_tracker,
                telemetry_json=telemetry_json,
                analysis_context=analysis_context,
            )
        elif isinstance(data_source, ExternalDataStoreNameDataSourceType):
            logger.info("Running DataStore DataWrangling analysis")
            data_store_id = await DataSourceRecipe.get_id_for_data_store_canonical_name(
                data_source.friendly_name
            )
            if not data_store_id:
                assistant_message.in_progress = False
                assistant_message.error = "A remote dataset was deleted and can no longer be used for analysis. Please refresh."
                analysis_context.stage_message_update()

                yield AnalysisGenerationError(assistant_message.error)
                await analysis_context.await_message_update()
                return

            if request:
                with use_user_token(request, allow_use_builder_token=True):
                    recipe = await DataSourceRecipe.load_or_create(
                        analyst_db, data_store_id
                    )
                    result = await recipe.refresh()
            else:
                recipe = await DataSourceRecipe.load_or_create(
                    analyst_db, data_store_id
                )
                result = await recipe.refresh()
            if result:
                assistant_message.in_progress = False
                assistant_message.error = "A remote dataset was deleted and can no longer be used for analysis. Please refresh."
                analysis_context.stage_message_update()

                yield AnalysisGenerationError(assistant_message.error)
                await analysis_context.await_message_update()
                return

            logger.debug(
                "Running DataStore data wrangling analysis with args",
                extra={
                    "dataset_names": datasets_names,
                    "question": enhanced_message,
                },
            )

            analysis_result = await run_database_analysis(
                RunDatabaseAnalysisRequest(
                    dataset_names=datasets_names,
                    question=enhanced_message,
                ),
                analyst_db,
                database_override=recipe.as_database_operator(),
                token_tracker=token_tracker,
                telemetry_json=telemetry_json,
                analysis_context=analysis_context,
            )

        else:
            if all(m.external_id is not None for m in dataset_metadata):
                if not DatasetSparkRecipe.should_use_spark_recipe():
                    raise RuntimeError(
                        "Should be unreachable. Ended up with remote datasets while remote datasets is disallowed."
                    )
                logging.info("Running DataWrangling analysis")

                if request:
                    with use_user_token(request, allow_use_builder_token=True):
                        recipe = await load_or_create_spark_recipe(
                            analyst_db=analyst_db
                        )
                        refresh = await recipe.refresh()
                else:
                    recipe = await load_or_create_spark_recipe(analyst_db=analyst_db)
                    refresh = await recipe.refresh()

                if refresh:
                    assistant_message.in_progress = False
                    assistant_message.error = "A remote dataset was deleted and can no longer be used for analysis. Please refresh."
                    analysis_context.stage_message_update()

                    yield AnalysisGenerationError(assistant_message.error)
                    await analysis_context.await_message_update()

                    return

                analysis_result = await run_database_analysis(
                    RunDatabaseAnalysisRequest(
                        dataset_names=datasets_names,
                        question=enhanced_message,
                    ),
                    analyst_db,
                    database_override=recipe.as_database_operator(),
                    token_tracker=token_tracker,
                    telemetry_json=telemetry_json,
                    analysis_context=analysis_context,
                )
            elif all(m.external_id is None for m in dataset_metadata):
                logging.info("Running local analysis")
                analysis_result = await run_analysis(
                    RunAnalysisRequest(
                        dataset_names=datasets_names,
                        question=enhanced_message,
                    ),
                    analysis_context=analysis_context,
                    token_tracker=token_tracker,
                    telemetry_json=telemetry_json,
                )
            else:
                raise ValueError(
                    "Cannot run analysis on a mix of local and remote datasets."
                )

        await analysis_context.await_message_update()
        log_memory()
        logger.info("Getting analysis result done")

        if isinstance(analysis_result, BaseException):
            error_message = (
                "Error running initial analysis. Try rephrasing: "
                f"{_friendly_llm_error(analysis_result)}"
            )
            assistant_message.in_progress = False
            assistant_message.error = error_message
            analysis_context.stage_message_update()

            yield AnalysisGenerationError(error_message)

            await analysis_context.await_message_update()
            return

        yield analysis_result

        assistant_message.components.append(analysis_result)
        assistant_message.step_value = "ANALYZING_RESULTS"
        analysis_context.stage_message_update()

        assistant_message = await extract_and_store_datasets(
            analyst_db, assistant_message
        )
        analysis_context.assistant_message = assistant_message

        analysis_context.stage_message_update()

    except Exception as e:
        error_message = (
            f"Error running initial analysis. Try rephrasing: {_friendly_llm_error(e)}"
        )
        assistant_message.in_progress = False
        assistant_message.error = error_message
        analysis_context.stage_message_update()

        yield AnalysisGenerationError(error_message)

        await analysis_context.await_message_update()
        return

    # Only proceed with additional analysis if we have valid initial results
    if not (
        analysis_result
        and analysis_result.dataset
        and (enable_chart_generation or enable_business_insights)
    ):
        assistant_message.in_progress = False
        analysis_context.stage_message_update()
        await analysis_context.await_message_update()
        return

    # Run concurrent analyses
    try:
        charts_result, business_result = await execute_business_analysis_and_charts(
            analysis_result,
            enhanced_message,
            token_tracker,
            enable_business_insights=enable_business_insights,
            enable_chart_generation=enable_chart_generation,
            telemetry_json=telemetry_json,
        )

        # Handle chart results
        if isinstance(charts_result, BaseException):
            error_message = "Error generating charts"
            assistant_message.error = error_message
            analysis_context.stage_message_update()

            yield AnalysisGenerationError(error_message)

        elif charts_result is not None:
            assistant_message.components.append(charts_result)
            analysis_context.stage_message_update()

            yield charts_result

        # Handle business analysis results
        if isinstance(business_result, BaseException):
            error_message = "Error generating business insights"
            assistant_message.error = error_message
            analysis_context.stage_message_update()

            yield AnalysisGenerationError(error_message)

        elif business_result is not None:
            assistant_message.components.append(business_result)
            analysis_context.stage_message_update()

            yield business_result

        assistant_message.in_progress = False
        analysis_context.stage_message_update()

    except Exception as e:
        error_message = (
            f"Error setting up additional analysis: {_friendly_llm_error(e)}"
        )
        assistant_message.in_progress = False
        assistant_message.error = error_message
        analysis_context.stage_message_update()

        yield AnalysisGenerationError(error_message)

    finally:
        # Generate token usage component
        if token_tracker.call_count > 0:
            final_usage_component = UsageInfoComponent(
                usage=TokenUsageInfo(**token_tracker.to_dict())
            )

            assistant_message.components.append(final_usage_component)

            analysis_context.stage_message_update()

            yield final_usage_component

        await analysis_context.await_message_update()


async def process_data_and_update_state(
    new_dataset_names: list[str],
    analyst_db: AnalystDB,
    data_source: str | DataSourceType,
    telemetry_json: dict[str, Any] | None = None,
) -> AsyncGenerator[str, None]:
    """Process datasets and yield progress updates asynchronously."""
    # Start processing and yield initial message
    logger.info(
        "Starting data processing",
        extra={"new_dataset_names": new_dataset_names, "data_source": data_source},
    )
    log_memory()
    yield gettext("Starting data processing")

    # Handle data cleansing based on the source
    # Convert string data_source to DataSourceType if needed
    data_source_type = (
        data_source
        if isinstance(data_source, InternalDataSourceType)
        or isinstance(data_source, ExternalDataStoreNameDataSourceType)
        else get_data_source_type(data_source)
    )
    if data_source_type != InternalDataSourceType.DATABASE and not isinstance(
        data_source_type, ExternalDataStoreNameDataSourceType
    ):
        try:
            logger.info("Cleansing datasets")
            yield gettext("Cleansing datasets")
            for analysis_dataset_name in new_dataset_names:
                metadata = await analyst_db.get_dataset_metadata(analysis_dataset_name)
                if metadata.data_source == InternalDataSourceType.REMOTE_REGISTRY:
                    # Skip remote datasets.
                    continue

                analysis_dataset = await analyst_db.get_dataset(
                    analysis_dataset_name, max_rows=None
                )

                cleansed_dataset = await cleanse_dataframe(analysis_dataset)
                reg_result = await analyst_db.register_dataset(
                    cleansed_dataset, data_source=InternalDataSourceType.GENERATED
                )
                if not reg_result["success"]:
                    logger.error(
                        f"Failed to register cleansed dataset {analysis_dataset_name}: {reg_result['msg']}"
                    )
                    yield gettext(
                        "Failed to register cleansed dataset: {analysis_dataset_name}"
                    ).format(analysis_dataset_name=analysis_dataset_name)
                    continue
                yield gettext("Cleansed dataset: {analysis_dataset_name}").format(
                    analysis_dataset_name=analysis_dataset_name
                )
                del cleansed_dataset
                del analysis_dataset
                log_memory()

            logger.info("Cleansing datasets complete")
            yield gettext("Cleansing datasets complete")
            log_memory()
        except Exception as e:
            logger.error(
                "Data processing failed during dataset cleansing",
                extra={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "datasets": new_dataset_names,
                    "data_source": data_source_type.value,
                    "memory_usage": f"{psutil.Process().memory_info().rss / 1024 / 1024:.2f} MB",
                },
                exc_info=True,
            )
            yield gettext("Data processing failed")
            raise
    else:
        pass

    # Generate data dictionaries
    logger.info("Data processing successful, generating dictionaries")
    yield gettext("Data processing successful, generating dictionaries")
    log_memory()
    for analysis_dataset_name in new_dataset_names:
        try:
            existing_dictionary = await analyst_db.get_data_dictionary(
                analysis_dataset_name
            )
            logger.info(
                f"Found existing dictionary for dataset: {analysis_dataset_name}"
            )
            if existing_dictionary is not None:
                await analyst_db.clear_dictionary_error(analysis_dataset_name)
                continue

        except Exception:
            pass

        logger.info(f"Creating dictionary for dataset: {analysis_dataset_name}")
        try:
            analysis_dataset = await analyst_db.get_dataset(analysis_dataset_name)
            new_dictionary = await get_dictionary(analysis_dataset, telemetry_json)
            logger.info(new_dictionary.to_application_df())
            del analysis_dataset
            await analyst_db.register_data_dictionary(new_dictionary, clobber=True)
            await analyst_db.clear_dictionary_error(analysis_dataset_name)
            logger.info(f"Registered dictionary for dataset: {analysis_dataset_name}")
            yield gettext("Registered data dictionary: {analysis_dataset_name}").format(
                analysis_dataset_name=analysis_dataset_name
            )
        except Exception as e:
            logger.error(
                f"Failed to generate data dictionary for {analysis_dataset_name}",
                exc_info=True,
            )
            try:
                await analyst_db.mark_dictionary_failed(
                    analysis_dataset_name, _friendly_llm_error(e)
                )
            except Exception:
                logger.error(
                    f"Also failed to persist dictionary error for {analysis_dataset_name}",
                    exc_info=True,
                )
            yield gettext(
                "Failed to generate data dictionary: {analysis_dataset_name}"
            ).format(analysis_dataset_name=analysis_dataset_name)
        log_memory()
    log_memory()
    # Final completion message
    yield gettext("Processing complete")
