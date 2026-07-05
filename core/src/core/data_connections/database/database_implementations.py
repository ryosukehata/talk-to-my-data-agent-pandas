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

from typing import Any

from core.credentials import JDBCCredentials, NoDatabaseCredentials
from core.database_helpers import (
    BigQueryOperator,
    DatabaseOperator,
    JdbcPreviewOperator,
    NoDatabaseOperator,
    SAPDatasphereOperator,
    SnowflakeOperator,
    load_app_infra,
)
from core.database_helpers import (
    get_database_operator as _get_database_operator,
)
from core.database_helpers import (
    get_external_database as _get_external_database,
)
from core.schema import AppInfra


def get_database_operator(
    app_infra: AppInfra, schema: str | None = None
) -> DatabaseOperator[Any]:
    return _get_database_operator(app_infra, schema=schema)


def get_external_database(schema: str | None = None) -> DatabaseOperator[Any]:
    return _get_external_database(schema=schema)


__all__ = [
    "BigQueryOperator",
    "DatabaseOperator",
    "JDBCCredentials",
    "JdbcPreviewOperator",
    "NoDatabaseCredentials",
    "NoDatabaseOperator",
    "SAPDatasphereOperator",
    "SnowflakeOperator",
    "get_database_operator",
    "get_external_database",
    "load_app_infra",
]
