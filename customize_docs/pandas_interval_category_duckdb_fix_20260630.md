# pandas Intervalカテゴリ列のDuckDB保存エラー対応

## 背景

pandas版では、LLM生成分析コードが `pd.cut` / `pd.qcut` を使うと、結果DataFrameに `CategoricalDtype` かつカテゴリが `IntervalDtype` の列が含まれることがある。

この列を `pyarrow.Table.from_pandas()` 経由でDuckDB 1.3.2へ登録すると、DuckDB側で `Attempted to dereference shared_ptr that is NULL!` の内部エラーが発生する。

upstreamは内部DataFrameをPolarsへ寄せており、保存時は `pl.DataFrame.to_arrow()` を使うため、このpandas固有のIntervalカテゴリ列をそのままDuckDBへ渡す経路がない。

## 方針

最小変更として、LLM生成コードやレポート生成には触れず、DuckDB保存直前のDataFrame正規化だけを拡張する。

`DatasetHandler._normalize_dataframe_for_arrow()` で以下を文字列化する。

- `IntervalDtype` 列
- `CategoricalDtype` かつカテゴリが `IntervalDtype` の列

既存のobject列混在型フォールバックは維持する。

## テスト

追加テスト:

- `test_extract_and_store_datasets_handles_interval_category_column`

検証内容:

- `pd.qcut` で作成したIntervalカテゴリ列を含む分析結果DataFrameを `extract_and_store_datasets()` で保存できること
- 保存後に `dataset_id` が設定されること
- DuckDBから復元したIntervalカテゴリ列が文字列として取得できること

実行結果:

```text
uv run pytest app_backend/tests/test_analyst_db_upstream_compat.py
9 passed
```
