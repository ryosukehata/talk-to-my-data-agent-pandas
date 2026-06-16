# DatasetMetadata tuple columns investigation 2026-06-16

## User-facing error

Initial analysis failed while registering a pandas dataset whose columns included tuple labels:

```text
8 validation errors for DatasetMetadata
columns.36 Input should be a valid string [type=string_type, input_value=('black_friday', 0.0), input_type=tuple]
```

## Root cause

`DatasetMetadata.columns` is typed as `list[str]`. The fork keeps the public dataframe path on pandas, where column labels may be arbitrary hashable values, including tuples and `MultiIndex` labels.

Before this fix, `DatasetHandler.register_dataframe()` passed `list(df.columns)` into `DatasetMetadata`. For tuple-labeled pandas columns this produced `list[tuple[...]]`, which Pydantic rejected before metadata could be stored.

`pyarrow.Table.from_pandas(..., preserve_index=False)` already normalizes those labels into the string column names used when the table is registered in DuckDB, for example:

```python
[("black_friday", 0.0)] -> ["('black_friday', '0.0')"]
```

The fix stores metadata columns from `arrow_table.schema.names`, so metadata and the registered DuckDB table use the same string column names.

## Additional minimal compatibility fix

`DataDictionary.from_analyst_df()` also assumed that every dataframe column label was already a string. That is safe for the upstream Polars implementation, but pandas analysis result dataframes can still contain tuple labels after operations such as `pivot` or `groupby().unstack()`.

The minimal fix stringifies the `DataDictionaryColumn.column` value while keeping the existing pandas dtype lookup unchanged. This prevents the same Pydantic `string_type` validation error when a business-analysis dictionary is built from a pandas analysis result.

## Upstream comparison

Upstream v11.5.1 and upstream main already use `polars.DataFrame` in `DatasetHandler.register_dataframe()`. Polars column names are strings, so `columns=list(df.columns)` is safe there.

This fork intentionally preserved pandas in the dataset roundtrip layer. That means the upstream implementation pattern cannot be copied directly without either converting the whole path to Polars or normalizing pandas column labels at the storage boundary. The minimal compatible fix is to normalize via the PyArrow schema that is already used for table creation.

## Version comparison

Observed local app backend environment:

- `pydantic==2.7.4`
- `pandas==2.3.3`
- `polars==1.41.2`
- `pyarrow==18.1.0`
- `datarobot==3.16.0`
- `litellm==1.80.0`
- `scikit-learn==1.7.2`

Upstream v11.5.1 lock snapshot:

- `pydantic==2.12.5`
- `pandas==2.3.3`
- `polars==1.36.1`
- `pyarrow==18.1.0`
- `datarobot==3.10.0`
- `litellm==1.80.0`
- `scikit-learn==1.7.2`

Upstream main app backend lock snapshot:

- `pydantic==2.12.5`
- `pandas==2.3.3`
- `polars==1.36.1`
- `pyarrow==20.0.0`
- `datarobot==3.14.0`
- `litellm==1.80.0`
- `scikit-learn==1.7.2`

The failure is not primarily caused by a library version mismatch. It is caused by pandas accepting tuple column labels while the Pydantic model requires strings. Newer Pydantic also expects `list[str]` elements to be strings, so the same invalid metadata input remains unsafe.

## Tests

Added a regression test:

```text
uv run pytest app_backend/tests/test_analyst_db_upstream_compat.py::test_register_dataset_normalizes_tuple_columns_for_metadata -q
uv run pytest app_backend/tests/test_schema_pandas_compat.py::test_data_dictionary_from_analyst_df_stringifies_tuple_columns -q
```

The test registers a pandas dataset with tuple column labels, verifies registration succeeds, and checks that `DatasetMetadata.columns` are strings matching the restored DuckDB dataframe columns.

The second test builds a `DataDictionary` from a pandas dataframe with tuple column labels and verifies dictionary column names are strings.
