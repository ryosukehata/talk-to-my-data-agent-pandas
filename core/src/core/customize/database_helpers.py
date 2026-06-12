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

"""
カスタマイズされたデータベースヘルパー関数

スキーマやテーブルの説明文付きデータ取得機能を提供する。
"""

from core.customize.database_config import SchemaTableConfigManager
from core.database_helpers import get_external_database


def get_schemas_with_descriptions() -> dict[str, str]:
    """
    Get all available schemas with their descriptions.

    Returns:
        Dictionary mapping schema names to descriptions.
        If no description is available, schema name is used as description.
    """
    config_manager = SchemaTableConfigManager()
    schemas = get_external_database().get_schemas()
    descriptions = config_manager.load_schema_descriptions()

    return {schema: descriptions.get(schema, schema) for schema in schemas}


def get_tables_with_descriptions(schema: str | None = None) -> dict[str, str]:
    """
    Get all available tables with their descriptions.

    Args:
        schema: Schema name to filter tables (optional)

    Returns:
        Dictionary mapping table names to descriptions.
        If no description is available, table name is used as description.
    """
    config_manager = SchemaTableConfigManager()
    tables = get_external_database(schema=schema).get_tables()
    descriptions = config_manager.load_table_descriptions()

    return {table: descriptions.get(table, table) for table in tables}
