# Chat Export Plotly Trace Fix

## 背景

チャットをExcelエクスポートすると、チャートデータシートに以下の pandas 例外が出ることがあった。

- `Error: All arrays must be of the same length`
- `Error: Mixing dicts with non-Series may lead to ambiguous ordering.`

## 原因

`core/src/core/routers/chats.py` のチャートエクスポート処理で、Plotly figure JSON の trace dict をほぼそのまま `pd.DataFrame(...)` に渡していた。

Plotly trace には `x` / `y` のような配列データだけでなく、`line` / `marker` のような入れ子dict、`type` / `name` のようなメタデータ、長さが揃わない配列が含まれることがある。そのため pandas の列形式DataFrame生成条件に合わず、上記例外が発生していた。

## 改善方針

pandas 公式ドキュメント上も、列形式の dict は配列長が揃った表形式データ向けであり、Plotly trace 全体のJSON構造を直接渡す用途ではない。チャートエクスポートでは以下の正規化を行う。

- trace の配列値だけをExcel向けの列として扱う
- `type` / `name` などのメタデータと、`line` / `marker` などの入れ子dictは表データから除外する
- 配列長が揃わない場合は最大長に合わせ、不足分は空セルにする
- Plotly typed array JSON (`dtype` / `bdata`) は配列へ復元できる場合だけ列化する
- DataFrame作成は `DataFrame.from_records(...)` に渡せる行レコードへ変換してから行う

## 変更内容

- `core.customize.infrastructure.export.chat_export.plotly_trace_to_dataframe()` を追加
- `core/src/core/routers/chats.py` のチャートデータシート生成で、trace dict の直接DataFrame化を廃止

## テスト

追加・確認したテスト:

- 長さの違う `x/y` 配列を持つPlotly traceで pandas 例外が出ず、不足分が空値になること
- `line` / `marker` のような入れ子dictを持つPlotly traceで pandas 例外が出ず、表データ列だけが出力されること
- 実際のチャットExcelエクスポート関数で、問題のあるPlotly traceが `Chart Processing Error` ではなく `Chart 1` シートとして出力されること

実行コマンド:

```bash
uv run pytest app_backend/tests/test_schema_pandas_compat.py -q
uv run pytest app_backend/tests -q
uv run ruff check core/src/core/customize/infrastructure/export/chat_export.py core/src/core/customize/infrastructure/export/__init__.py core/src/core/routers/chats.py app_backend/tests/test_schema_pandas_compat.py
```
