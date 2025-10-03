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

import csv
from pathlib import Path


def validate_csv_for_upload(file_path: str) -> None:
    """
    Validate CSV file for upload to DataRobot.
    
    Checks:
    1. File exists
    2. File has .csv extension
    3. File contains required columns: schema_name, schema_description, table_name, table_description
    
    Args:
        file_path: Path to the CSV file to validate
        
    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file is not a CSV or missing required columns
    """
    file_path_obj = Path(file_path)
    
    # Check if file exists
    if not file_path_obj.exists():
        raise FileNotFoundError(f"CSV file not found: {file_path}")
    
    # Check if file has .csv extension
    if file_path_obj.suffix.lower() != '.csv':
        raise ValueError(f"File must be a CSV file (has .csv extension): {file_path}")
    
    # Check if file has required columns
    try:
        with open(file_path, 'r', encoding='utf-8') as csvfile:
            # Read the first line to get headers
            reader = csv.reader(csvfile)
            headers = next(reader, None)
            
            if headers is None:
                raise ValueError(f"CSV file is empty: {file_path}")
            
            # Convert headers to set for comparison
            actual_columns = set(header.strip() for header in headers)
            required_columns = {'schema_name', 'schema_description', 'table_name', 'table_description'}
            missing_columns = required_columns - actual_columns
            
            if missing_columns:
                raise ValueError(
                    f"CSV file is missing required columns: {', '.join(sorted(missing_columns))}. "
                    f"Required columns are: {', '.join(sorted(required_columns))}"
                )
            
            # Check if CSV has any data rows
            has_data = False
            for row in reader:
                if any(cell.strip() for cell in row):  # Check if row has any non-empty cells
                    has_data = True
                    break
            
            if not has_data:
                raise ValueError(f"CSV file has no data rows: {file_path}")
                
    except UnicodeDecodeError:
        raise ValueError(f"CSV file has invalid encoding (must be UTF-8): {file_path}")
    except csv.Error as e:
        raise ValueError(f"CSV file is corrupted or has invalid format: {file_path}. Error: {e}")
    except Exception as e:
        raise ValueError(f"Error reading CSV file {file_path}: {e}")