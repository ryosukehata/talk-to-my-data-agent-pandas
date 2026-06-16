import pandas as pd
from utils.schema import DataDictionary


def test_data_dictionary_from_analyst_df_stringifies_tuple_columns() -> None:
    df = pd.DataFrame(
        [[100, 200]],
        columns=pd.Index(
            [
                ("black_friday", 0.0),
                ("holiday", 1.0),
            ]
        ),
    )

    dictionary = DataDictionary.from_analyst_df(df)

    assert [column.column for column in dictionary.column_descriptions] == [
        "('black_friday', 0.0)",
        "('holiday', 1.0)",
    ]
    assert [column.data_type for column in dictionary.column_descriptions] == [
        "int64",
        "int64",
    ]
