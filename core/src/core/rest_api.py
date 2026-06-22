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

"""Main FastAPI application factory for the Data Analyst API."""

from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from starlette.types import Lifespan

import core.routers.chats as chats_routes
import core.routers.database as database_routes
import core.routers.datasets as datasets_routes
import core.routers.dictionaries as dictionaries_routes
import core.routers.external_data_stores as external_data_store_routes
import core.routers.registry as registry_routes
import core.routers.user as user_routes
from core import deps, file_utils
from core import middleware as core_middleware
from core.logging_helper import get_logger
from core.middleware import session_middleware
from core.routers import (
    chats_router,
    database_router,
    datasets_router,
    dictionaries_router,
    external_data_stores_router,
    registry_router,
    supported_types_router,
    user_router,
)

from .telemetry import otel

logger = get_logger()

# Backward-compatible exports for utils.rest_api/core.rest_api consumers.
SessionState = core_middleware.SessionState
_initialize_session = core_middleware._initialize_session
get_database = core_middleware.get_database
session_store = core_middleware.session_store
get_initialized_db = deps.get_initialized_db
detect_and_decode_csv = file_utils.detect_and_decode_csv
detect_delimiter = file_utils.detect_delimiter
load_and_validate_csv = file_utils.load_and_validate_csv
create_chat = chats_routes.create_chat
create_chat_message = chats_routes.create_chat_message
create_new_chat_message = chats_routes.create_new_chat_message
delete_chat = chats_routes.delete_chat
delete_chat_message = chats_routes.delete_chat_message
get_chat = chats_routes.get_chat
get_chat_message = chats_routes.get_chat_message
get_chat_messages = chats_routes.get_chat_messages
get_chats = chats_routes.get_chats
run_complete_analysis_task = chats_routes.run_complete_analysis_task
save_chat_messages = chats_routes.save_chat_messages
update_chat = chats_routes.update_chat
get_and_process_tables = database_routes.get_and_process_tables
get_database_tables = database_routes.get_database_tables
load_from_database = database_routes.load_from_database
process_and_update = database_routes.process_and_update
delete_datasets = datasets_routes.delete_datasets
download_dataset = datasets_routes.download_dataset
get_cleansed_dataset = datasets_routes.get_cleansed_dataset
get_dataset_by_id = datasets_routes.get_dataset_by_id
get_dataset_metadata = datasets_routes.get_dataset_metadata
upload_files = datasets_routes.upload_files
delete_dictionary = dictionaries_routes.delete_dictionary
download_dictionary = dictionaries_routes.download_dictionary
get_dictionaries = dictionaries_routes.get_dictionaries
update_dictionary_cell = dictionaries_routes.update_dictionary_cell
get_available_external_data_stores = (
    external_data_store_routes.get_available_external_data_stores
)
get_supported_datasource_types = (
    external_data_store_routes.get_supported_datasource_types
)
register_external_data_sources = external_data_store_routes.register_external_data_sources
update_data_sources_for_data_store = (
    external_data_store_routes.update_data_sources_for_data_store
)
get_registry_datasets = registry_routes.get_registry_datasets
get_datarobot_account = user_routes.get_datarobot_account
store_datarobot_account = user_routes.store_datarobot_account
_app_singleton: FastAPI | None = None


def custom_openapi(app: FastAPI) -> dict[str, Any]:
    """Generate custom OpenAPI schema with security definitions."""
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Add security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "ApiKeyAuth": {"type": "apiKey", "in": "header", "name": "X-API-Key"}
    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema


def create_app(
    lifespan: Lifespan[FastAPI] | None = None,
    title: str = "Data Analyst API",
) -> FastAPI:
    """Create a configured FastAPI app, preserving the default singleton."""
    global _app_singleton

    if lifespan is None and title == "Data Analyst API":
        if _app_singleton is None:
            _app_singleton = _create_fastapi_app()
        return _app_singleton

    return _create_fastapi_app(lifespan=lifespan, title=title)


def _create_fastapi_app(
    lifespan: Lifespan[FastAPI] | None = None,
    title: str = "Data Analyst API",
) -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        FastAPI: The configured FastAPI application instance
    """
    app = FastAPI(
        title=title,
        description="""
        An intelligent API for data analysis that provides capabilities including:
        - Dataset management (upload CSV/Excel files, connect to databases, access the Data Registry)
        - Data cleansing and standardization
        - Data dictionary creation and management
        - Chat-based data analysis conversations
        - Python code generation
        - Chart creation
        - Business insights generation

        Available endpoint groups:
        - /api/v1/registry: Access Data Registry datasets
        - /api/v1/database: Database connection and table management
        - /api/v1/datasets: Upload, retrieve, and manage datasets
        - /api/v1/dictionaries: Manage data dictionaries
        - /api/v1/chats: Create and manage chat conversations for data analysis

        The API uses OpenAI's GPT models for intelligent analysis and response generation.
        """,
        version="1.0.0",
        contact={"name": "API Support", "email": "support@example.com"},
        license_info={
            "name": "Apache 2.0",
            "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
        },
        lifespan=lifespan,
        debug=True,  # Stack traces will be exposed for 500 responses
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allows all origins
        allow_credentials=True,
        allow_methods=["*"],  # Allows all methods
        allow_headers=["*"],  # Allows all headers
    )

    # Add session middleware
    app.middleware("http")(session_middleware)

    # Set custom OpenAPI schema
    app.openapi = lambda: custom_openapi(app)  # type: ignore[method-assign]

    # Get script name from environment
    script_name = os.environ.get("SCRIPT_NAME", "")
    prefix = f"{script_name}/api/v1"

    # Register all routers
    app.include_router(registry_router, prefix=prefix)
    app.include_router(database_router, prefix=prefix)
    app.include_router(datasets_router, prefix=prefix)
    app.include_router(dictionaries_router, prefix=prefix)
    app.include_router(chats_router, prefix=prefix)
    app.include_router(user_router, prefix=prefix)
    app.include_router(external_data_stores_router, prefix=prefix)
    app.include_router(supported_types_router, prefix=prefix)

    try:
        from core.customize.rest_api import router as customize_router

        app.include_router(customize_router, prefix=prefix)
        logger.info("Customize API endpoints mounted")
    except ImportError as e:
        logger.warning("Customize module was not found: %s", e)
    except Exception as e:
        logger.exception("Failed to load customize API endpoints: %s", e)

    # Initialize telemetry on application startup
    otel.log_application_start()

    # Setup auto-instrumentation for FastAPI
    # This will automatically trace all incoming HTTP requests
    otel.instrument_fastapi_app(app)

    return app


app = create_app()
