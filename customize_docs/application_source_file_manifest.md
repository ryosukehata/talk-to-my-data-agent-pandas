# Application Source file manifest

## 背景

GitHub Actions の Pulumi CD で、DataRobot `ApplicationSource` 更新時に `filePath` の重複で 422 が返った。

`infra/settings_app_infra.py` の `get_app_files()` は `utils/**/*.py` で `utils/customize/**/*.py` も収集していたが、その後に `utils/customize/**/*.py` を同じ配置先パスで再追加していた。

## 対応

- `utils/customize/**/*.py` の二重追加を削除する。
- Application Source に渡すファイル一覧の配置先パスを一意化する。
- 同じ配置先に異なるローカルファイルが割り当てられた場合は、DataRobot API 送信前に `ValueError` で失敗させる。

## テスト

- `customize_docs/test_application_source_file_manifest.py`
  - `get_app_files()` の返却する配置先パスに重複がないことを検証する。
  - 今回ログに出た `utils/customize/api_endpoints/report.py` が 1 件だけ含まれることを検証する。
