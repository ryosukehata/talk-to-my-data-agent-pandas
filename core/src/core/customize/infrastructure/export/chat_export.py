from __future__ import annotations

import base64
import binascii
import json
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
import pandas as pd

_PLOTLY_TRACE_METADATA_FIELDS = frozenset({"type", "name"})


def plotly_trace_to_dataframe(trace: Mapping[str, Any]) -> pd.DataFrame:
    """Convert a Plotly trace dict into tabular rows safe for Excel export."""
    columns: dict[str, list[Any]] = {}

    for key, value in trace.items():
        if key in _PLOTLY_TRACE_METADATA_FIELDS:
            continue

        column_values = _as_column_values(value)
        if column_values is None:
            continue

        columns[key] = [_to_excel_cell_value(item) for item in column_values]

    if not columns:
        return pd.DataFrame()

    column_names = list(columns)
    row_count = max(len(values) for values in columns.values())
    records = [
        {
            column_name: (
                columns[column_name][row_index]
                if row_index < len(columns[column_name])
                else None
            )
            for column_name in column_names
        }
        for row_index in range(row_count)
    ]

    return pd.DataFrame.from_records(records, columns=column_names)


def _as_column_values(value: Any) -> list[Any] | None:
    if isinstance(value, Mapping):
        return _decode_plotly_typed_array(value)

    if isinstance(value, (str, bytes, bytearray)):
        return None

    if isinstance(value, Sequence):
        return list(value)

    return None


def _decode_plotly_typed_array(value: Mapping[str, Any]) -> list[Any] | None:
    dtype = value.get("dtype")
    encoded_data = value.get("bdata")

    if not isinstance(dtype, str) or not isinstance(encoded_data, str):
        return None

    try:
        array = np.frombuffer(base64.b64decode(encoded_data), dtype=np.dtype(dtype))
    except (TypeError, ValueError, binascii.Error):
        return None

    shape = _parse_plotly_array_shape(value.get("shape"))
    if shape:
        try:
            array = array.reshape(shape)
        except ValueError:
            pass

    return array.tolist()


def _parse_plotly_array_shape(shape: Any) -> tuple[int, ...] | None:
    if isinstance(shape, str):
        try:
            return tuple(int(part.strip()) for part in shape.split(",") if part.strip())
        except ValueError:
            return None

    if isinstance(shape, Sequence) and not isinstance(shape, (str, bytes, bytearray)):
        try:
            return tuple(int(part) for part in shape)
        except (TypeError, ValueError):
            return None

    return None


def _to_excel_cell_value(value: Any) -> Any:
    if isinstance(value, (Mapping, list, tuple)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)

    return value
