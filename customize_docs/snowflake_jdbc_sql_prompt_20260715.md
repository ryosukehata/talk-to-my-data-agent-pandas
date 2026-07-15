# Snowflake JDBC SQL prompt constraints

## 変更内容

DataRobot JDBC Preview は生成SQLを派生テーブルとして実行する。そのため、Snowflake のSQL生成に使用される `core/src/core/customize/prompts.py` の `SYSTEM_PROMPT_SNOWFLAKE` を更新した。

- `code` は末尾セミコロンなしの単一 `SELECT` または `WITH`/CTE + `SELECT` に限定する。
- データベース名・スキーマ名を含むプレースホルダーやテンプレート変数を禁止する。
- サンプルデータおよびデータディクショナリーで提供された完全一致のテーブル参照だけを使用する。
- 順序付き `ARRAY_AGG` は `ARRAY_AGG(DISTINCT expression) WITHIN GROUP (ORDER BY expression)` に限定する。
- LLMの応答はJSONのみとし、Markdownコードフェンスおよび `code` 内の非SQLテキストを禁止する。
- JDBC派生テーブルで実行できないセッション依存文（`SHOW`、`DESCRIBE`、`EXPLAIN`、`CALL`、`SET`など）を禁止する。
- `ARRAY_AGG` で `DISTINCT` と `WITHIN GROUP` を併用する場合、集約対象と順序式を同一にする。
- リトライ時は、直前の構文・識別子・プレースホルダー・集約順序の失敗パターンを繰り返さない。

旧来の `Warehouse: {warehouse}` / `Database: {database}` は JDBC の `get_system_prompt()` では展開されず、生成SQLに混入する可能性があるため削除した。

## テスト

- `core/tests/test_v1182_core.py::test_snowflake_jdbc_system_prompt_requires_derived_table_safe_sql`
  - JDBC Snowflake operator が実際に返すシステムプロンプトに、JSON出力・JDBC実行・`ARRAY_AGG`・リトライの全制約が存在すること、未展開の環境プレースホルダーがないことを検証する。

## 構文確認

Snowflake公式ドキュメントにより、`ARRAY_AGG` の並び順指定には `WITHIN GROUP` を使う構成を確認した。
