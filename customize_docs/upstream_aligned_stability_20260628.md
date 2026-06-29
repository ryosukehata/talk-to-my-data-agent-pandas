# Upstream-Aligned Stability 2026-06-28

## 背景

`main(v0.3.5)` や upstream/main v11.8.2 に比べて、pandas 版 fork で初期分析が失敗しやすくなっていた。
代表例は analyst result 登録時に `最小値=[1.0, np.False_, 3.2]` のような mixed `object` 列を `pyarrow.Table.from_pandas()` に渡し、Arrow が数値列へ変換しようとして失敗するケース。

upstream は Polars DataFrame の `to_arrow()` で登録しているが、この fork では公開境界を pandas のまま維持する。Polars 移行は行わない。

## 方針

- pandas DataFrame を DuckDB/Arrow に登録する直前だけ正規化する。
- 通常の数値、bool、datetime、文字列列は維持する。
- Arrow 変換できない mixed `object` 列、または数値と `bool` / `np.bool_` が混在する `object` 列だけ `string` 化する。
- `run_complete_analysis` は upstream の `RunCompleteAnalysisRequestContext` に寄せ、`stage_message_update()` / `await_message_update()` を使う。
- 外部 Data Store / remote registry は fork 機能として残す。
- database analysis にも `GENERATING_QUERY` / `RUNNING_QUERY` step 更新を入れる。
- outer exception は raw `str(e)` ではなく `_friendly_llm_error(e)` を使う。
- analyst result の CSV download / Excel export は pandas DataFrame 前提に戻す。
- `core.telemetry.OTel.trace` の async generator close 時に別 context の detach error を出さない。

## テスト

追加した主な回帰テスト:

- `最小値=[1.0, np.False_, 3.2]` を含む analysis result が保存・取得できること。
- analyst result の CSV download と Excel export が pandas DataFrame で成功すること。
- `run_complete_analysis` が `ANALYZING_RESULTS` を staged update し、business result を重複 yield しないこと。
- database analysis が context 経由で `GENERATING_QUERY` / `RUNNING_QUERY` を更新すること。
- 初期分析の outer exception が `_friendly_llm_error()` の文言になること。
- `core.telemetry.OTel.trace` の async generator close で `Failed to detach context` が出ないこと。

実行結果:

```text
uv run pytest app_backend/tests/test_llm_client.py -q
12 passed, 3 warnings

uv run pytest app_backend/tests/test_analyst_db_upstream_compat.py app_backend/tests/test_schema_pandas_compat.py -q
11 passed

uv run pytest app_backend/tests/test_base_telemetry.py app_backend/tests/test_api_analysis_execution_v0424_compat.py -q
16 passed

uv run pytest app_backend/tests/test_v1182_compat.py app_backend/tests/test_v1172_compat.py -q
18 passed

uv run ruff check core/src/core/analyst_db.py core/src/core/api.py core/src/core/routers/chats.py core/src/core/routers/datasets.py core/src/core/telemetry/otel.py app_backend/tests/test_analyst_db_upstream_compat.py app_backend/tests/test_schema_pandas_compat.py app_backend/tests/test_api_analysis_execution_v0424_compat.py app_backend/tests/test_base_telemetry.py
All checks passed
```

`test_llm_client.py` では LiteLLM の atexit logging / cleanup warning が出るが、テスト結果は成功。
