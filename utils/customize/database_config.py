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

import os
from pathlib import Path
from typing import Dict, Tuple

import pandas as pd

from utils.customize.api import download_registry_dataset_as_dataframe
from utils.resources import DatabaseDescription


class SchemaTableConfigManager:
    """Manages schema and table descriptions from CSV files using pandas."""

    def __init__(self, local: bool = True):  # "database_description.csv"):
        """
        Initialize the SchemaTableConfigManager.

        Args:
            csv_path: Path to the CSV file containing schema and table descriptions
        """
        self.local = local
        self._load()

    def _load(self) -> None:
        self.db_description = None

        if self.local and os.getenv("DATABASE_DESCRIPTION_PATH") is not None:
            self.db_description = pd.read_csv(
                os.path.join(
                    Path(__file__).resolve().parent.parent.parent.absolute(),
                    os.getenv("DATABASE_DESCRIPTION_PATH"),
                )
            )
        else:
            db_description = DatabaseDescription()
            if db_description.id:
                try:
                    self.db_description = download_registry_dataset_as_dataframe(
                        db_description.id
                    )
                except Exception as e:
                    print(f"Error downloading database description: {e}")

    def load_all_descriptions(self) -> Tuple[Dict[str, str], Dict[str, str]]:
        """
        Load schema and table descriptions from single CSV file.

        Expected CSV format:
        schema_name,schema_description,table_name,table_description
        PUBLIC,パブリックデータ,USERS,ユーザー情報
        PUBLIC,パブリックデータ,PRODUCTS,商品マスター
        TEST02,テスト02020,TRANSACTIONS,取引履歴

        Returns:
            Tuple of (schema_descriptions, table_descriptions)
            Returns ({}, {}) if file doesn't exist or has errors
        """
        if self.db_description is None:
            return {}, {}

        try:
            # Read CSV with pandas
            df = self.db_description

            # Validate required columns
            required_columns = [
                "schema_name",
                "schema_description",
                "table_name",
                "table_description",
            ]
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(
                    f"Database description dataset is missing required columns: {missing_columns}"
                )

            # Extract schema descriptions (remove duplicates, keep first occurrence)
            schema_df = (
                df[["schema_name", "schema_description"]]
                .dropna()
                .drop_duplicates("schema_name")
            )
            schema_dict = dict(
                zip(
                    schema_df["schema_name"].str.strip(),
                    schema_df["schema_description"].str.strip(),
                )
            )

            # Extract table descriptions (if columns exist)

            table_df = (
                df[["table_name", "table_description"]]
                .dropna()
                .drop_duplicates("table_name")
            )
            table_dict = dict(
                zip(
                    table_df["table_name"].str.strip(),
                    table_df["table_description"].str.strip(),
                )
            )

            # Remove empty keys or values
            schema_dict = {k: v for k, v in schema_dict.items() if k and v}
            table_dict = {k: v for k, v in table_dict.items() if k and v}

            return schema_dict, table_dict

        except Exception as e:
            # Log error but don't fail - return empty dicts
            print(f"Warning: Could not load database descriptions: {e}")
            return {}, {}

    def load_schema_descriptions(self) -> Dict[str, str]:
        """
        Load schema descriptions from CSV file.

        Returns:
            Dictionary mapping schema names to descriptions.
            Returns empty dict if file doesn't exist or has errors.
        """
        schema_dict, _ = self.load_all_descriptions()
        return schema_dict

    def load_table_descriptions(self) -> Dict[str, str]:
        """
        Load table descriptions from CSV file.

        Returns:
            Dictionary mapping table names to descriptions.
            Returns empty dict if file doesn't exist or has errors.
        """
        _, table_dict = self.load_all_descriptions()
        return table_dict
