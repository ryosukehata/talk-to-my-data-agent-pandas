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

import asyncio
import functools
import json
import traceback
from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Generator, Generic, TypeVar, cast
from urllib.parse import parse_qsl, urlsplit

import pandas as pd
import snowflake.connector
from google.cloud import bigquery
from hdbcli import dbapi
from openai.types.chat.chat_completion_system_message_param import (
    ChatCompletionSystemMessageParam,
)
from pydantic import ValidationError

from core.analyst_db import AnalystDB, InternalDataSourceType
from core.code_execution import InvalidGeneratedCode
from core.credentials import (
    GoogleCredentialsBQ,
    JDBCCredentials,
    NoDatabaseCredentials,
    SAPDatasphereCredentials,
    SnowflakeCredentials,
)
from core.customize.prompts import (
    SYSTEM_PROMPT_SNOWFLAKE,
)
from core.customize.snowflake_jdbc_compat import (
    snowflake_jdbc_credentials_from_legacy_env,
)
from core.logging_helper import get_logger
from core.prompts import (
    SYSTEM_PROMPT_BIGQUERY,
    SYSTEM_PROMPT_MYSQL,
    SYSTEM_PROMPT_POSTGRES,
    SYSTEM_PROMPT_SAP_DATASPHERE,
    SYSTEM_PROMPT_SQLSERVER,
)
from core.schema import (
    AnalystDataset,
    AppInfra,
)

logger = get_logger("DatabaseHelper")

T = TypeVar("T")
_DEFAULT_DB_QUERY_TIMEOUT = 300
_DATABASE_DATASET_NAME_SEPARATOR = "-"


def database_dataset_display_name(table_name: str, schema_name: str | None) -> str:
    """Return the dataset name shown in the app for a database table."""
    schema_name, table_name = database_source_parts(table_name, schema_name)
    if schema_name:
        return f"{schema_name}{_DATABASE_DATASET_NAME_SEPARATOR}{table_name}"
    return table_name


def database_source_name(table_name: str, schema_name: str | None) -> str:
    """Return a stable source identifier for a database table."""
    schema_name, table_name = database_source_parts(table_name, schema_name)
    if schema_name:
        return f"{schema_name}.{table_name}"
    return table_name


def database_source_parts(
    source_name: str, default_schema: str | None = None
) -> tuple[str | None, str]:
    """Split a database source/display name into schema and table parts."""
    if "." in source_name:
        schema_name, table_name = source_name.rsplit(".", 1)
        return schema_name or default_schema, table_name

    if default_schema:
        display_prefix = f"{default_schema}{_DATABASE_DATASET_NAME_SEPARATOR}"
        if source_name.startswith(display_prefix):
            return default_schema, source_name[len(display_prefix) :]

    return default_schema, source_name


@dataclass
class SnowflakeCredentialArgs:
    credentials: SnowflakeCredentials


@dataclass
class BigQueryCredentialArgs:
    credentials: GoogleCredentialsBQ


@dataclass
class SAPDatasphereCredentialArgs:
    credentials: SAPDatasphereCredentials


@dataclass
class JDBCCredentialArgs:
    credentials: JDBCCredentials


@dataclass
class NoDatabaseCredentialArgs:
    credentials: NoDatabaseCredentials


class DatabaseOperator(ABC, Generic[T]):
    @abstractmethod
    def __init__(self, credentials: T, default_timeout: int): ...

    @abstractmethod
    @contextmanager
    def create_connection(self) -> Any: ...

    @abstractmethod
    async def execute_query(
        self, query: str, timeout: int | None = None
    ) -> list[tuple[Any, ...]] | list[dict[str, Any]]: ...

    @abstractmethod
    async def get_tables(self, timeout: int | None = None) -> list[str]:
        return []

    @functools.lru_cache(maxsize=8)
    @abstractmethod
    def get_schemas(self, timeout: int | None = None) -> list[str]:
        return []

    @functools.lru_cache(maxsize=8)
    @abstractmethod
    async def get_data(
        self,
        *table_names: str,
        analyst_db: AnalystDB,
        sample_size: int = 5000,
        timeout: int | None = None,
    ) -> list[str]:
        return []

    @abstractmethod
    def get_system_prompt(self) -> ChatCompletionSystemMessageParam:
        return ChatCompletionSystemMessageParam(role="system", content="")

    def query_friendly_name(self, dataset_name: str) -> str:
        """Return a query-friendly version of the dataset name (e.g. quoted table name if that's required)."""
        return dataset_name

    def warmup_query(self) -> str | None:
        return None

    async def warmup(self) -> None:
        query = self.warmup_query()
        if query:
            await self.execute_query(query)


class NoDatabaseOperator(DatabaseOperator[NoDatabaseCredentialArgs]):
    def __init__(
        self,
        credentials: NoDatabaseCredentials,
        default_timeout: int = _DEFAULT_DB_QUERY_TIMEOUT,
    ):
        self._credentials = credentials

    @contextmanager
    def create_connection(self) -> Generator[None]:
        yield None

    async def execute_query(
        self,
        query: str,
        timeout: int | None = 300,
    ) -> list[tuple[Any, ...]] | list[dict[str, Any]]:
        return []

    async def get_tables(self, timeout: int | None = 300) -> list[str]:
        return []

    def get_schemas(self, timeout: int | None = 300) -> list[str]:
        return []

    @functools.lru_cache(8)
    async def get_data(
        self,
        *table_names: str,
        analyst_db: AnalystDB,
        sample_size: int = 5000,
        timeout: int | None = 300,
    ) -> list[str]:
        return []

    def get_system_prompt(self) -> ChatCompletionSystemMessageParam:
        return ChatCompletionSystemMessageParam(role="system", content="")


class SnowflakeOperator(DatabaseOperator[SnowflakeCredentialArgs]):
    def __init__(
        self,
        credentials: SnowflakeCredentials,
        default_timeout: int = _DEFAULT_DB_QUERY_TIMEOUT,
    ):
        if not credentials.is_configured():
            raise ValueError("Snowflake credentials not properly configured")
        self._credentials = credentials
        self.default_timeout = default_timeout

    @contextmanager
    def create_connection(self) -> Generator[snowflake.connector.SnowflakeConnection]:
        """Create a connection to Snowflake using environment variables"""
        if not self._credentials.is_configured():
            raise ValueError("Snowflake credentials not properly configured")

        connect_params: dict[str, Any] = {
            "user": self._credentials.user,
            "account": self._credentials.account,
            "warehouse": self._credentials.warehouse,
            "database": self._credentials.database,
            "schema": self._credentials.db_schema,
            "role": self._credentials.role,
        }

        # Try key file authentication first if configured
        project_root = Path(__file__).resolve().parent.parent
        if private_key := self._credentials.get_private_key(project_root=project_root):
            connect_params["private_key"] = private_key
        elif self._credentials.password:
            connect_params["password"] = self._credentials.password
        else:
            raise ValueError(
                "Neither private key nor password authentication configured"
            )

        # In some enviroments, the Snowflake client's platform detection crashes. This patch skips that detection.
        snowflake.connector.SnowflakeConnection.platform_detection_timeout_seconds = 0.0  # type: ignore[method-assign,assignment]
        connection = snowflake.connector.connect(**connect_params)
        yield connection
        connection.close()

    async def execute_query(
        self, query: str, timeout: int | None = None
    ) -> list[tuple[Any, ...]] | list[dict[str, Any]]:
        """Execute a Snowflake query with timeout and metadata capture

        Args:
            conn: Snowflake connection
            query: SQL query to execute
            timeout: Query timeout in seconds

        Returns:
            Tuple of (results, metadata)
        """
        timeout = timeout if timeout is not None else self.default_timeout
        conn: snowflake.connector.SnowflakeConnection
        try:
            with self.create_connection() as conn:
                with conn.cursor(snowflake.connector.DictCursor) as cursor:
                    cursor = conn.cursor(snowflake.connector.DictCursor)
                    # Set query timeout at cursor level
                    cursor.execute(
                        f"ALTER SESSION SET STATEMENT_TIMEOUT_IN_SECONDS = {timeout}"
                    )

                    try:
                        # Execute query
                        cursor.execute(query)

                        # Get results
                        results = cursor.fetchall()

                        return results

                    except snowflake.connector.errors.ProgrammingError as e:
                        # Handle Snowflake-specific errors
                        raise InvalidGeneratedCode(
                            f"Snowflake error: {str(e.msg)}",
                            code=query,
                            exception=None,
                            traceback_str="",
                        )

        except Exception as e:
            raise InvalidGeneratedCode(
                f"Query execution failed: {str(e)}",
                code=query,
                exception=e,
                traceback_str=traceback.format_exc(),
            )

    async def get_tables(self, timeout: int | None = None) -> list[str]:
        """Fetch list of tables from Snowflake schema"""
        timeout = timeout if timeout is not None else self.default_timeout

        conn: snowflake.connector.SnowflakeConnection
        try:
            with self.create_connection() as conn:
                with conn.cursor() as cursor:
                    # Log current session info
                    logger.info("Checking current session settings...")
                    cursor.execute(
                        f"ALTER SESSION SET STATEMENT_TIMEOUT_IN_SECONDS = {timeout}"
                    )

                    cursor.execute(
                        "SELECT CURRENT_DATABASE(), CURRENT_SCHEMA(), CURRENT_ROLE(), CURRENT_WAREHOUSE()",
                    )
                    current_settings = cursor.fetchone()
                    logger.info(
                        f"Current settings - Database: {current_settings[0]}, Schema: {current_settings[1]}, Role: {current_settings[2]}, Warehouse: {current_settings[3]}"  # type: ignore[index]
                    )

                    # Check if schema exists
                    cursor.execute(
                        f"""
                        SELECT COUNT(*)
                        FROM {self._credentials.database}.INFORMATION_SCHEMA.SCHEMATA
                        WHERE SCHEMA_NAME = '{self._credentials.db_schema}'
                    """,
                    )
                    schema_exists = cursor.fetchone()[0]  # type: ignore[index]
                    logger.info(f"Schema exists check: {schema_exists > 0}")

                    # Get all objects (tables and views)
                    cursor.execute(
                        f"""
                        SELECT table_name, table_type
                        FROM {self._credentials.database}.information_schema.tables
                        WHERE table_schema = '{self._credentials.db_schema}'
                        AND table_type IN ('BASE TABLE', 'VIEW')
                        ORDER BY table_type, table_name
                    """
                    )
                    results = cursor.fetchall()
                    tables = [row[0] for row in results]

                    # Log detailed results
                    logger.info(f"Total objects found: {len(results)}")
                    for table_name, table_type in results:
                        logger.info(f"Found {table_type}: {table_name}")

                    # Check schema privileges
                    cursor.execute(
                        f"""
                        SHOW GRANTS ON SCHEMA {self._credentials.database}.{self._credentials.db_schema}
                    """
                    )
                    privileges = cursor.fetchall()
                    logger.info("Schema privileges:")
                    for priv in privileges:
                        logger.info(f"Privilege: {priv}")

                    return tables

        except Exception as e:
            logger.error(f"Failed to fetch tables: {str(e)}")
            logger.error(f"Error type: {type(e)}")
            logger.error(f"Error details: {str(e)}")
            return []

    def get_schemas(self, timeout: int | None = None) -> list[str]:
        """Fetch list of available schemas from Snowflake database"""
        timeout = timeout if timeout is not None else self.default_timeout

        conn: snowflake.connector.SnowflakeConnection
        try:
            with self.create_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        f"ALTER SESSION SET STATEMENT_TIMEOUT_IN_SECONDS = {timeout}"
                    )

                    # Get all schemas in the database
                    cursor.execute(
                        f"""
                        SELECT SCHEMA_NAME
                        FROM {self._credentials.database}.INFORMATION_SCHEMA.SCHEMATA
                        WHERE SCHEMA_NAME NOT IN ('INFORMATION_SCHEMA')
                        ORDER BY SCHEMA_NAME
                        """
                    )
                    results = cursor.fetchall()

                    schemas = [row[0] for row in results]

                    logger.info(
                        f"Found {len(schemas)} schemas in database {self._credentials.database}"
                    )
                    return schemas

        except Exception as e:
            logger.error(f"Failed to fetch schemas: {str(e)}")
            # エラーが発生した場合は、少なくともデフォルトスキーマを返す
            return [self._credentials.db_schema]

    @functools.lru_cache(maxsize=8)
    async def get_data(
        self,
        *table_names: str,
        analyst_db: AnalystDB,
        sample_size: int = 5000,
        timeout: int | None = None,
    ) -> list[str]:
        """Load selected tables from Snowflake as pandas DataFrames

        Args:
        - table_names: List of table names to fetch
        - sample_size: Number of rows to sample from each table

        Returns:
        - Dictionary of table names to list of records
        """

        timeout = timeout if timeout is not None else self.default_timeout

        conn: snowflake.connector.SnowflakeConnection

        dataframes = []
        try:
            with self.create_connection() as conn:
                cursor = conn.cursor()

                for table in table_names:
                    try:
                        qualified_table = f'{self._credentials.database}.{self._credentials.db_schema}."{table}"'
                        logger.info(f"Fetching data from table: {qualified_table}")
                        cursor.execute(
                            f"ALTER SESSION SET STATEMENT_TIMEOUT_IN_SECONDS = {timeout}"
                        )
                        cursor.execute(
                            f"""
                            SELECT * FROM {qualified_table}
                            SAMPLE ({sample_size} ROWS)
                        """
                        )

                        columns = [desc[0] for desc in cursor.description]
                        data = cursor.fetchall()
                        pandas_df = pd.DataFrame(data=data, columns=columns, dtype=str)
                        # If you want to use Polars later, do it after validation/registration
                        # 修正後のコード
                        table_with_schema = f"{self._credentials.db_schema}.{table}"
                        dataframes.append(
                            AnalystDataset(name=table_with_schema, data=pandas_df)
                        )
                        # dataframes.append(AnalystDataset(name=table, data=pandas_df))

                    except Exception as e:
                        logger.error(f"Error loading table {table}: {str(e)}")
                        logger.error(f"Error type: {type(e)}")
                        logger.error(f"Error details: {str(e)}")
                        continue
                names = []
                for dataframe in dataframes:
                    reg_result = await analyst_db.register_dataset(
                        dataframe, InternalDataSourceType.DATABASE
                    )
                    if not reg_result["success"]:
                        logger.error(
                            f"Failed to register dataset {dataframe.name}: {reg_result['msg']}"
                        )
                        continue
                    names.append(dataframe.name)
                return names

        except Exception as e:
            logger.error(f"Error fetching Snowflake data: {str(e)}")
            logger.error(f"Error type: {type(e)}")
            logger.error(f"Error details: {str(e)}")
            return []

    def get_system_prompt(self) -> ChatCompletionSystemMessageParam:
        return ChatCompletionSystemMessageParam(
            role="system",
            content=SYSTEM_PROMPT_SNOWFLAKE.format(
                warehouse=self._credentials.warehouse,
                database=self._credentials.database,
            ),
        )


class BigQueryOperator(DatabaseOperator[BigQueryCredentialArgs]):
    def __init__(
        self,
        credentials: GoogleCredentialsBQ,
        default_timeout: int = _DEFAULT_DB_QUERY_TIMEOUT,
    ):
        self._credentials = credentials
        self._credentials.db_schema = self._credentials.db_schema
        self._database = credentials.service_account_key["project_id"]
        self.default_timeout = default_timeout

    @contextmanager
    def create_connection(self) -> Generator[bigquery.Client]:
        from google.oauth2 import service_account

        google_credentials = service_account.Credentials.from_service_account_info(  # type: ignore[no-untyped-call]
            GoogleCredentialsBQ().service_account_key,
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        client = bigquery.Client(
            credentials=google_credentials,
        )

        yield client

        client.close()  # type: ignore[no-untyped-call]

    async def execute_query(
        self, query: str, timeout: int | None = None
    ) -> list[tuple[Any, ...]] | list[dict[str, Any]]:
        conn: bigquery.Client
        timeout = timeout if timeout is not None else self.default_timeout
        try:
            with self.create_connection() as conn:
                results = conn.query(query, timeout=timeout)

                sql_result: pd.DataFrame = results.to_dataframe()

                sql_result_as_dicts = cast(
                    list[dict[str, Any]], sql_result.to_dict(orient="records")
                )
                return sql_result_as_dicts

        except Exception as e:
            raise InvalidGeneratedCode(
                f"Query execution failed: {str(e)}",
                code=query,
                exception=e,
                traceback_str=traceback.format_exc(),
            )

    async def get_tables(self, timeout: int | None = None) -> list[str]:
        """Fetch list of tables from BigQuery schema"""
        timeout = timeout if timeout is not None else self.default_timeout

        conn: bigquery.Client

        try:
            with self.create_connection() as conn:
                tables = [
                    i.table_id
                    for i in conn.list_tables(
                        str(self._credentials.db_schema), timeout=timeout
                    )
                ]

                # Log detailed results
                logger.info(f"Total objects found: {len(tables)}")
                logger.info(f"Found tables: {', '.join(tables)}")

                return tables

        except Exception as e:
            logger.error(f"Failed to fetch tables: {str(e)}")
            logger.error(f"Error type: {type(e)}")
            logger.error(f"Error details: {str(e)}")
            return []

    def get_schemas(self, timeout: int | None = None) -> list[str]:
        """BigQuery schemas not implemented - return empty list"""
        return []

    @functools.lru_cache(maxsize=8)
    async def get_data(
        self,
        *table_names: str,
        analyst_db: AnalystDB,
        sample_size: int = 5000,
        timeout: int | None = None,
    ) -> list[str]:
        timeout = timeout if timeout is not None else self.default_timeout

        dataframes = []

        conn: bigquery.Client

        try:
            with self.create_connection() as conn:
                for table in table_names:
                    try:
                        qualified_table = (
                            f"{self._database}.{self._credentials.db_schema}.{table}"
                        )
                        logger.info(f"Fetching data from table: {qualified_table}")

                        pandas_df: pd.DataFrame = conn.query(
                            f"""
                            SELECT * FROM `{qualified_table}`
                            LIMIT {sample_size}
                        """,
                            timeout=timeout,
                        ).to_dataframe()
                        df = pandas_df
                        logger.info(
                            f"Successfully loaded table {table}: {len(df)} rows, {len(df.columns)} columns"
                        )

                        dataframes.append(AnalystDataset(name=table, data=df))

                    except Exception as e:
                        logger.error(f"Error loading table {table}: {str(e)}")
                        logger.error(f"Error type: {type(e)}")
                        logger.error(f"Error details: {str(e)}")
                        continue

                names = []
                for dataframe in dataframes:
                    reg_result = await analyst_db.register_dataset(
                        dataframe, InternalDataSourceType.DATABASE
                    )
                    if not reg_result["success"]:
                        logger.error(
                            f"Failed to register dataset {dataframe.name}: {reg_result['msg']}"
                        )
                        continue
                    names.append(dataframe.name)

                return names

        except Exception as e:
            logger.error(f"Error fetching data: {str(e)}")
            logger.error(f"Error type: {type(e)}")
            logger.error(f"Error details: {str(e)}")
            return []

    def get_system_prompt(self) -> ChatCompletionSystemMessageParam:
        return ChatCompletionSystemMessageParam(
            role="system",
            content=SYSTEM_PROMPT_BIGQUERY.format(
                project=self._database,
                dataset=self._credentials.db_schema,
            ),
        )


class SAPDatasphereOperator(DatabaseOperator[SAPDatasphereCredentialArgs]):
    def __init__(
        self,
        credentials: SAPDatasphereCredentials,
        default_timeout: int = _DEFAULT_DB_QUERY_TIMEOUT,
    ):
        if not credentials.is_configured():
            raise ValueError("SAP Data Sphere credentials not properly configured")
        self._credentials = credentials
        self.default_timeout = default_timeout

    @contextmanager
    def create_connection(self) -> Generator[dbapi.Connection]:
        """Create a connection to SAP Data Sphere"""
        if not self._credentials.is_configured():
            raise ValueError("SAP Data Sphere credentials not properly configured")

        connect_params: dict[str, Any] = {
            "address": self._credentials.host,
            "port": self._credentials.port,
            "user": self._credentials.user,
            "password": self._credentials.password,
        }

        try:
            # Connect to SAP Data Sphere
            connection = dbapi.connect(**connect_params)
            yield connection
        except Exception:
            raise
        finally:
            connection.close()

    async def execute_query(
        self, query: str, timeout: int | None = None
    ) -> list[tuple[Any, ...]] | list[dict[str, Any]]:
        """Execute a SAP Data Sphere query with timeout

        Args:
            query: SQL query to execute
            timeout: Query timeout in seconds

        Returns:
            Query results
        """
        timeout = timeout if timeout is not None else self.default_timeout
        conn: dbapi.Connection
        try:
            with self.create_connection() as conn:
                cursor = conn.cursor()
                try:
                    # Execute query
                    cursor.execute(query)

                    # Get results
                    results = cursor.fetchall()

                    return [
                        dict(zip(row.column_names, row.column_values))
                        for row in results
                    ]

                except Exception as e:
                    # Handle SAP Data Sphere specific errors
                    raise InvalidGeneratedCode(
                        f"SAP Data Sphere error: {str(e)}",
                        code=query,
                        exception=None,
                        traceback_str="",
                    )
                finally:
                    cursor.close()

        except Exception as e:
            raise InvalidGeneratedCode(
                f"Query execution failed: {str(e)}",
                code=query,
                exception=e,
                traceback_str=traceback.format_exc(),
            )

    async def get_tables(self, timeout: int | None = None) -> list[str]:
        """Fetch list of tables from SAP Data Sphere schema"""
        timeout = timeout if timeout is not None else self.default_timeout

        conn: dbapi.Connection
        try:
            with self.create_connection() as conn:
                cursor = conn.cursor()
                try:
                    # Get all tables and views in the schema
                    cursor.execute(
                        f"""
                        SELECT TABLE_NAME
                        FROM SYS.TABLES
                        WHERE SCHEMA_NAME = '{self._credentials.db_schema}'
                        ORDER BY TABLE_NAME
                        """
                    )
                    tables = [row[0] for row in cursor.fetchall()]

                    # Get all views
                    cursor.execute(
                        f"""
                        SELECT VIEW_NAME
                        FROM SYS.VIEWS
                        WHERE SCHEMA_NAME = '{self._credentials.db_schema}'
                        ORDER BY VIEW_NAME
                        """
                    )
                    views = [row[0] for row in cursor.fetchall()]

                    all_objects = tables + views

                    # Log detailed results
                    logger.info(
                        f"Total objects found in schema {self._credentials.db_schema}: {len(all_objects)}"
                    )
                    logger.info(f"Tables: {len(tables)}, Views: {len(views)}")

                    return all_objects

                finally:
                    cursor.close()

        except Exception as e:
            logger.error(f"Failed to fetch tables from SAP Data Sphere: {str(e)}")
            logger.error(f"Error type: {type(e)}")
            logger.error(f"Error details: {str(e)}")
            return []

    def get_schemas(self, timeout: int | None = None) -> list[str]:
        """SAP Data Sphere schemas not implemented - return empty list"""
        return []

    @functools.lru_cache(maxsize=8)
    async def get_data(
        self,
        *table_names: str,
        analyst_db: AnalystDB,
        sample_size: int = 5000,
        timeout: int | None = None,
    ) -> list[str]:
        """Load selected tables from SAP Data Sphere as DataFrames

        Args:
        - table_names: List of table names to fetch
        - sample_size: Number of rows to sample from each table
        - timeout: Query timeout in seconds

        Returns:
        - List of registered dataset names
        """
        timeout = timeout if timeout is not None else self.default_timeout
        dataframes = []

        try:
            with self.create_connection() as conn:
                cursor = conn.cursor()

                for table in table_names:
                    try:
                        qualified_table = f'"{self._credentials.db_schema}"."{table}"'
                        logger.info(f"Fetching data from table: {qualified_table}")

                        # Execute query to get data with limit
                        cursor.execute(
                            f"""
                            SELECT * FROM {qualified_table}
                            LIMIT {sample_size}
                            """
                        )

                        # Get column names
                        columns = [desc[0] for desc in cursor.description]
                        data = cursor.fetchall()

                        # Convert to pandas DataFrame
                        pandas_df = pd.DataFrame(data=data, columns=columns, dtype=str)

                        logger.info(
                            f"Successfully loaded table {table}: {len(pandas_df)} rows, {len(pandas_df.columns)} columns"
                        )
                        dataframes.append(AnalystDataset(name=table, data=pandas_df))

                    except Exception as e:
                        logger.error(f"Error loading table {table}: {str(e)}")
                        logger.error(f"Error type: {type(e)}")
                        logger.error(f"Error details: {str(e)}")
                        continue

                # Register datasets
                names = []
                for dataframe in dataframes:
                    reg_result = await analyst_db.register_dataset(
                        dataframe, InternalDataSourceType.DATABASE
                    )
                    if not reg_result["success"]:
                        logger.error(
                            f"Failed to register dataset {dataframe.name}: {reg_result['msg']}"
                        )
                        continue
                    names.append(dataframe.name)
                return names

        except Exception as e:
            logger.error(f"Error fetching SAP Data Sphere data: {str(e)}")
            logger.error(f"Error type: {type(e)}")
            logger.error(f"Error details: {str(e)}")
            return []

    def get_system_prompt(self) -> ChatCompletionSystemMessageParam:
        return ChatCompletionSystemMessageParam(
            role="system",
            content=SYSTEM_PROMPT_SAP_DATASPHERE.format(
                schema=self._credentials.db_schema,
            ),
        )


_JDBC_TABLE_DISCOVERY_SQL: dict[str, str] = {
    "postgresql": """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_type = 'BASE TABLE'
    """,
    "mysql": """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = DATABASE()
          AND table_type = 'BASE TABLE'
    """,
    "sqlserver": """
        SELECT TABLE_NAME
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_TYPE = 'BASE TABLE'
    """,
    "snowflake": """
        SELECT TABLE_NAME
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = CURRENT_SCHEMA()
          AND TABLE_TYPE IN ('BASE TABLE', 'VIEW')
        ORDER BY TABLE_TYPE, TABLE_NAME
    """,
    "sap": """
        SELECT TABLE_NAME FROM SYS.TABLES WHERE SCHEMA_NAME = CURRENT_SCHEMA
        UNION ALL
        SELECT VIEW_NAME FROM SYS.VIEWS WHERE SCHEMA_NAME = CURRENT_SCHEMA
        ORDER BY TABLE_NAME
    """,
    "bigquery": """
        SELECT table_name
        FROM INFORMATION_SCHEMA.TABLES
        WHERE table_type IN ('BASE TABLE', 'VIEW')
        ORDER BY table_name
    """,
}

_JDBC_DIALECT_NAMES = {
    "postgresql": "PostgreSQL",
    "mysql": "MySQL",
    "sqlserver": "SQL Server",
    "snowflake": "Snowflake",
    "sap": "SAP Datasphere",
    "bigquery": "BigQuery",
}


class JdbcPreviewOperator(DatabaseOperator[JDBCCredentialArgs]):
    def __init__(
        self,
        credentials: JDBCCredentials,
        default_timeout: int = _DEFAULT_DB_QUERY_TIMEOUT,
        schema: str | None = None,
    ):
        self._credentials = credentials
        self.default_timeout = default_timeout
        self.default_schema = self._default_schema_from_uri()
        self._selected_schema = schema or self.default_schema

    @property
    def _dialect_key(self) -> str:
        uri = self._credentials.jdbc_uri
        if uri.startswith("jdbc:postgresql://"):
            return "postgresql"
        if uri.startswith("jdbc:mysql://"):
            return "mysql"
        if uri.startswith("jdbc:sqlserver://"):
            return "sqlserver"
        if uri.startswith("jdbc:snowflake://"):
            return "snowflake"
        if uri.startswith("jdbc:sap://"):
            return "sap"
        if uri.startswith("jdbc:bigquery://"):
            return "bigquery"
        raise ValueError(f"Unsupported JDBC URI scheme: {uri.split(':')[1]!r}")

    def _dialect_name(self) -> str:
        return _JDBC_DIALECT_NAMES[self._dialect_key]

    def _quote_identifier(self, name: str) -> str:
        match self._dialect_key:
            case "postgresql":
                return f'"{name}"'
            case "mysql":
                return f"`{name}`"
            case "sqlserver":
                return f"[{name}]"
            case "snowflake" | "sap":
                return f'"{name}"'
            case "bigquery":
                return f"`{name}`"
            case _:
                raise ValueError(f"Unsupported dialect: {self._dialect_key!r}")

    @staticmethod
    def _sql_literal(value: str) -> str:
        return "'" + value.replace("'", "''") + "'"

    @staticmethod
    def _first_record_value(row: Any) -> Any:
        if isinstance(row, dict):
            return next(iter(row.values()))
        if isinstance(row, (tuple, list)):
            return row[0]
        return row

    def _jdbc_uri_query_params(self) -> dict[str, str]:
        parsed = urlsplit(self._credentials.jdbc_uri.removeprefix("jdbc:"))
        return {
            key.lower(): value
            for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        }

    def _default_schema_from_uri(self) -> str | None:
        query_params = self._jdbc_uri_query_params()
        for key in ("schema", "dbschema", "currentschema", "defaultschema"):
            if schema := query_params.get(key):
                return schema
        return None

    def _schema_discovery_sql(self) -> str:
        match self._dialect_key:
            case "postgresql":
                return """
                    SELECT schema_name
                    FROM information_schema.schemata
                    WHERE schema_name NOT IN ('pg_catalog', 'information_schema')
                    ORDER BY schema_name
                """
            case "mysql":
                return """
                    SELECT SCHEMA_NAME
                    FROM INFORMATION_SCHEMA.SCHEMATA
                    ORDER BY SCHEMA_NAME
                """
            case "sqlserver":
                return """
                    SELECT name
                    FROM sys.schemas
                    ORDER BY name
                """
            case "snowflake":
                return """
                    SELECT SCHEMA_NAME
                    FROM INFORMATION_SCHEMA.SCHEMATA
                    ORDER BY SCHEMA_NAME
                """
            case "sap":
                return """
                    SELECT SCHEMA_NAME
                    FROM SYS.SCHEMAS
                    ORDER BY SCHEMA_NAME
                """
            case "bigquery":
                return """
                    SELECT schema_name
                    FROM INFORMATION_SCHEMA.SCHEMATA
                    ORDER BY schema_name
                """
            case _:
                raise ValueError(f"Unsupported dialect: {self._dialect_key!r}")

    def _table_discovery_sql(self) -> str:
        selected_schema = self._selected_schema
        match self._dialect_key:
            case "postgresql":
                schema = selected_schema or "public"
                return f"""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = {self._sql_literal(schema)}
                      AND table_type = 'BASE TABLE'
                    ORDER BY table_name
                """
            case "mysql":
                schema_filter = (
                    f"table_schema = {self._sql_literal(selected_schema)}"
                    if selected_schema
                    else "table_schema = DATABASE()"
                )
                return f"""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE {schema_filter}
                      AND table_type = 'BASE TABLE'
                    ORDER BY table_name
                """
            case "sqlserver":
                schema_filter = (
                    f"TABLE_SCHEMA = {self._sql_literal(selected_schema)} AND"
                    if selected_schema
                    else ""
                )
                return f"""
                    SELECT TABLE_NAME
                    FROM INFORMATION_SCHEMA.TABLES
                    WHERE {schema_filter} TABLE_TYPE = 'BASE TABLE'
                    ORDER BY TABLE_NAME
                """
            case "snowflake":
                schema_filter = (
                    f"TABLE_SCHEMA = {self._sql_literal(selected_schema)}"
                    if selected_schema
                    else "TABLE_SCHEMA = CURRENT_SCHEMA()"
                )
                return f"""
                    SELECT TABLE_NAME
                    FROM INFORMATION_SCHEMA.TABLES
                    WHERE {schema_filter}
                      AND TABLE_TYPE IN ('BASE TABLE', 'VIEW')
                    ORDER BY TABLE_TYPE, TABLE_NAME
                """
            case "sap":
                schema_filter = (
                    f"{self._sql_literal(selected_schema)}"
                    if selected_schema
                    else "CURRENT_SCHEMA"
                )
                return f"""
                    SELECT TABLE_NAME FROM SYS.TABLES WHERE SCHEMA_NAME = {schema_filter}
                    UNION ALL
                    SELECT VIEW_NAME FROM SYS.VIEWS WHERE SCHEMA_NAME = {schema_filter}
                    ORDER BY TABLE_NAME
                """
            case "bigquery":
                information_schema = (
                    f"{self._quote_identifier(selected_schema)}.INFORMATION_SCHEMA.TABLES"
                    if selected_schema
                    else "INFORMATION_SCHEMA.TABLES"
                )
                return f"""
                    SELECT table_name
                    FROM {information_schema}
                    WHERE table_type IN ('BASE TABLE', 'VIEW')
                    ORDER BY table_name
                """
            case _:
                raise ValueError(f"Unsupported dialect: {self._dialect_key!r}")

    def _qualified_table_name(self, table: str) -> str:
        schema_name, table_name = database_source_parts(table, self._selected_schema)
        quoted_table = self._quote_identifier(table_name)
        if not schema_name:
            return quoted_table
        return f"{self._quote_identifier(schema_name)}.{quoted_table}"

    @staticmethod
    def _preview() -> Any:
        from datarobot.models.jdbc_data_preview import JdbcPreview

        return JdbcPreview

    @staticmethod
    def _result_schema(result: Any) -> list[Any]:
        result_schema = getattr(result, "result_schema", None)
        if not result_schema:
            raise ValueError("JDBC preview response did not include a result schema")
        return list(result_schema)

    @staticmethod
    def _schema_names(result_schema: list[Any]) -> list[str]:
        names: list[str] = []
        for entry in result_schema:
            if isinstance(entry, dict):
                names.append(str(entry["name"]))
            else:
                names.append(str(entry.name))
        return names

    @staticmethod
    def _schema_data_type(entry: Any) -> str:
        if isinstance(entry, dict):
            return str(entry.get("data_type") or entry.get("dataType") or "")
        return str(getattr(entry, "data_type", ""))

    def _parameters(self) -> dict[str, Any]:
        return self._credentials.jdbc_connection_parameters or {}

    def validate_connection(self) -> None:
        try:
            self._preview().preview(
                jdbc_url=self._credentials.jdbc_uri,
                sql="SELECT 1",
                max_rows=1,
                parameters=self._parameters(),
            )
        except Exception as e:
            raise ValueError(f"JDBC connection validation failed: {e}") from e

    @contextmanager
    def create_connection(self) -> Generator[None]:
        yield None

    async def execute_query(
        self, query: str, timeout: int | None = None
    ) -> list[tuple[Any, ...]] | list[dict[str, Any]]:
        del timeout
        loop = asyncio.get_running_loop()
        try:
            result = await loop.run_in_executor(
                None,
                lambda: self._preview().preview(
                    jdbc_url=self._credentials.jdbc_uri,
                    sql=query,
                    max_rows=10_000,
                    parameters=self._parameters(),
                ),
            )
            columns = self._schema_names(self._result_schema(result))
            return [
                row if isinstance(row, dict) else dict(zip(columns, row))
                for row in result.records
            ]
        except Exception as e:
            raise InvalidGeneratedCode(
                f"JDBC query execution failed: {str(e)}",
                code=query,
                exception=e,
                traceback_str=traceback.format_exc(),
            )

    async def get_tables(self, timeout: int | None = None) -> list[str]:
        del timeout
        loop = asyncio.get_running_loop()
        try:
            result = await loop.run_in_executor(
                None,
                lambda: self._preview().preview(
                    jdbc_url=self._credentials.jdbc_uri,
                    sql=self._table_discovery_sql(),
                    max_rows=10_000,
                    parameters=self._parameters(),
                ),
            )
            tables = [self._first_record_value(row) for row in result.records]
            logger.info("JDBC (%s): found %d tables", self._dialect_name(), len(tables))
            return [str(table) for table in tables]
        except Exception:
            logger.error("JDBC: failed to fetch tables", exc_info=True)
            return []

    def get_schemas(self, timeout: int | None = None) -> list[str]:
        del timeout
        try:
            result = self._preview().preview(
                jdbc_url=self._credentials.jdbc_uri,
                sql=self._schema_discovery_sql(),
                max_rows=10_000,
                parameters=self._parameters(),
            )
            schemas = [
                str(schema)
                for row in result.records
                if (schema := self._first_record_value(row))
            ]
            logger.info(
                "JDBC (%s): found %d schemas",
                self._dialect_name(),
                len(schemas),
            )
            return schemas
        except Exception:
            logger.error("JDBC: failed to fetch schemas", exc_info=True)
            return [self.default_schema] if self.default_schema else []

    @functools.lru_cache(maxsize=8)
    async def get_data(
        self,
        *table_names: str,
        analyst_db: AnalystDB,
        sample_size: int = 5000,
        timeout: int | None = None,
    ) -> list[str]:
        del timeout
        loop = asyncio.get_running_loop()
        names: list[str] = []
        for table in table_names:
            try:
                result = await loop.run_in_executor(
                    None,
                    lambda table=table: self._preview().preview(
                        jdbc_url=self._credentials.jdbc_uri,
                        sql=f"SELECT * FROM {self._qualified_table_name(table)}",
                        max_rows=min(sample_size, 10_000),
                        parameters=self._parameters(),
                    ),
                )
                result_schema = self._result_schema(result)
                columns = self._schema_names(result_schema)
                records = [
                    row if isinstance(row, dict) else dict(zip(columns, row))
                    for row in result.records
                ]
                column_types = dict(
                    zip(
                        columns,
                        [self._schema_data_type(entry) for entry in result_schema],
                    )
                )
                dataframe = pd.DataFrame(records, columns=columns, dtype=str)
                display_name = database_dataset_display_name(
                    table, self._selected_schema
                )
                source_name = database_source_name(table, self._selected_schema)
                dataset = AnalystDataset(name=display_name, data=dataframe)
                reg_result = await analyst_db.register_dataset(
                    dataset,
                    InternalDataSourceType.DATABASE,
                    external_id=source_name,
                    original_column_types=column_types,
                    clobber=True,
                )
                if not reg_result["success"]:
                    logger.error(
                        "Failed to register JDBC dataset %s: %s",
                        display_name,
                        reg_result["msg"],
                    )
                    continue
                names.append(display_name)
            except Exception:
                logger.error("JDBC: error loading table %s", table, exc_info=True)
                continue
        return names

    def query_friendly_name(self, dataset_name: str) -> str:
        return self._qualified_table_name(dataset_name)

    def get_system_prompt(self) -> ChatCompletionSystemMessageParam:
        prompt = {
            "postgresql": SYSTEM_PROMPT_POSTGRES,
            "mysql": SYSTEM_PROMPT_MYSQL,
            "sqlserver": SYSTEM_PROMPT_SQLSERVER,
            "snowflake": SYSTEM_PROMPT_SNOWFLAKE,
            "sap": SYSTEM_PROMPT_SAP_DATASPHERE,
            "bigquery": SYSTEM_PROMPT_BIGQUERY,
        }[self._dialect_key]
        return ChatCompletionSystemMessageParam(role="system", content=prompt)


def get_database_operator(
    app_infra: AppInfra, schema: str | None = None
) -> DatabaseOperator[Any]:
    if app_infra.database in ("snowflake", "sap", "bigquery", "datarobot_jdbc"):
        try:
            return JdbcPreviewOperator(JDBCCredentials(), schema=schema)
        except (ValidationError, ValueError) as exc:
            if app_infra.database == "snowflake":
                credentials = snowflake_jdbc_credentials_from_legacy_env()
                if credentials is not None:
                    return JdbcPreviewOperator(credentials, schema=schema)
            raise ValueError(
                f"DATABASE_CONNECTION_TYPE is '{app_infra.database}' but JDBC_URI "
                "is missing or invalid. Set JDBC_URI to a valid JDBC connection "
                "string such as jdbc:snowflake://..., jdbc:sap://..., or "
                "jdbc:bigquery://...."
            ) from exc

    return NoDatabaseOperator(NoDatabaseCredentials())


def load_app_infra() -> AppInfra:
    directories = [".", "frontend", "app_backend"]
    error = None
    for directory in directories:
        path = Path(directory).joinpath("app_infra.json")
        try:
            with open(path) as infra_selection:
                app_json = json.load(infra_selection)
                return AppInfra(**app_json)
        except (FileNotFoundError, ValidationError) as e:
            error = e
    raise ValueError(
        "Failed to read app_infra.json.\n"
        "If running locally, verify you have selected the correct "
        "stack and that it is active using `pulumi stack output`.\n"
        f"Ensure file is created by running `pulumi up`: {str(error)}"
    ) from error


def get_external_database(schema: str | None = None) -> DatabaseOperator[Any]:
    return get_database_operator(load_app_infra(), schema=schema)
