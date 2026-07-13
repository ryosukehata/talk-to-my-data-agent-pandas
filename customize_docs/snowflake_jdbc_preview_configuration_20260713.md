# Snowflake JDBC Preview configuration

## 背景

2026-07-13 時点の database 接続経路は upstream v11.10.1 に合わせ、`snowflake` / `sap` / `bigquery` / `datarobot_jdbc` を DataRobot JDBC Preview 経路へ統一している。

## 仕様

- `DATABASE_CONNECTION_TYPE=snowflake` を選んだ場合でも、実行時は `JdbcPreviewOperator` を使う。
- 標準経路では `JDBC_URI` に接続先、warehouse、database、schema、role などを含め、必要に応じて `JDBC_CONNECTION_PARAMETERS` に user/password または key 認証情報を渡す。
- 互換経路として、`DATABASE_CONNECTION_TYPE=snowflake` かつ `JDBC_URI` が未設定の場合だけ、`SNOWFLAKE_ACCOUNT` / `SNOWFLAKE_WAREHOUSE` / `SNOWFLAKE_DATABASE` / `SNOWFLAKE_SCHEMA` / `SNOWFLAKE_ROLE` などの旧 Snowflake 専用変数から Snowflake JDBC 設定へ変換する。
- `SNOWFLAKE_KEY_PATH` は DataRobot JDBC Preview へ `private_key_file` として渡さない。DataRobot 側からローカルファイルパスを読めないため、デプロイ時に PEM ファイル内容を `private_key_base64` へ変換する。
- 明示的に `JDBC_URI` が設定されている場合は、その値を優先する。不正な `JDBC_URI` が設定されていても旧 Snowflake 変数へ fallback しない。
- 変換ロジックは upstream 差分として追いやすいように `core/src/core/customize/snowflake_jdbc_compat.py` に集約する。

## 例

```env
DATABASE_CONNECTION_TYPE=snowflake
JDBC_URI=jdbc:snowflake://<account_identifier>.snowflakecomputing.com/?warehouse=COMPUTE_WH&db=SNOWFLAKE_SAMPLE_DATA&schema=TPCH_SF1&role=PUBLIC
JDBC_CONNECTION_PARAMETERS='{"user": "snowflake_user", "password": "snowflake_password"}'
```

## テスト

- `core/tests/test_v1182_core.py::test_snowflake_legacy_env_values_build_jdbc_preview_operator`
  - 旧 `SNOWFLAKE_*` 変数から Snowflake JDBC Preview 設定を組み立てることを固定する。
- `core/tests/test_v1182_core.py::test_snowflake_legacy_key_file_uses_base64_private_key_parameter`
  - `SNOWFLAKE_KEY_PATH` を `private_key_file` ではなく `private_key_base64` に変換することを固定する。
- `core/tests/test_v1182_core.py::test_snowflake_legacy_env_does_not_hide_invalid_explicit_jdbc_uri`
  - 明示された不正な `JDBC_URI` を旧 Snowflake 変数で隠さないことを固定する。

## 2026-07-13 deployment error investigation

添付ログでは Pulumi の `get_database_credentials("snowflake")` が `JdbcPreviewOperator.validate_connection()` を呼び、DataRobot JDBC Preview API で `400 client error: Invalid parameter value null for parameter type {1}` により失敗していた。

原因は、旧 `SNOWFLAKE_KEY_PATH` を JDBC parameter の `private_key_file` として渡していたこと。DataRobot JDBC Preview は DataRobot 側で JDBC を実行するため、ローカルの `rsa_key.p8` パスを読めない。

実接続検証では以下の結果だった。

- `private_key_file=<local path>`: 同じ `Invalid parameter value null...` で失敗
- `private_key_base64=<DER bytes base64>`: `Private key provided is invalid...` で失敗
- `private_key_base64=<PEM file bytes base64>`: `SELECT 1` に成功

このため、互換変換では PEM ファイル内容を base64 化して `private_key_base64` に渡す。
