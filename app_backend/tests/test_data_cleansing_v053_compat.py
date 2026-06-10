import asyncio
import importlib

import pandas as pd
import pytest
from utils.data_cleansing_helpers import process_column
from utils.schema import AnalystDataset, CleansedColumnReport, DataFrameWrapper


def test_process_column_requires_full_numeric_success_for_first_column() -> None:
    mostly_numeric_values = [str(value) for value in range(1, 10)] + ["A10"]
    df = pd.DataFrame(
        {
            "customer_id": mostly_numeric_values,
            "amount": mostly_numeric_values,
        }
    )

    _, customer_id_series, customer_id_report = process_column(
        df,
        "customer_id",
        df,
    )
    _, amount_series, amount_report = process_column(df, "amount", df)

    assert customer_id_report.conversion_type is None
    assert customer_id_series.equals(df["customer_id"])
    assert amount_report.conversion_type == "simple_clean"
    assert pd.api.types.is_float_dtype(amount_series)
    assert pd.isna(amount_series.iloc[-1])


def test_cleanse_dataframe_samples_up_to_500_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATAROBOT_API_TOKEN", "test-token")
    monkeypatch.setenv("DATAROBOT_ENDPOINT", "https://example.com")
    monkeypatch.setenv("OTEL_SDK_DISABLED", "true")

    api = importlib.import_module("utils.api")
    captured_sample_sizes: list[int] = []

    def fake_process_column(
        full_df: pd.DataFrame,
        column_name: str,
        sample_df: pd.DataFrame,
    ) -> tuple[str, pd.Series, CleansedColumnReport]:
        captured_sample_sizes.append(len(sample_df))
        return (
            column_name,
            full_df[column_name],
            CleansedColumnReport(new_column_name=column_name),
        )

    monkeypatch.setattr(api, "process_column", fake_process_column)
    df = pd.DataFrame({"value": range(700)})
    dataset = AnalystDataset(name="sample", data=DataFrameWrapper(df))

    asyncio.run(api.cleanse_dataframe(dataset))

    assert captured_sample_sizes == [500]
