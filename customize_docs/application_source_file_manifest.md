# Application Source file manifest

## 背景

GitHub Actions の Pulumi CD で、DataRobot `ApplicationSource` 更新時に `filePath` の重複で 422 が返った。

`infra/settings_app_infra.py` の `get_app_files()` は `utils/**/*.py` で `utils/customize/**/*.py` も収集していたが、その後に `utils/customize/**/*.py` を同じ配置先パスで再追加していた。

## 対応

- `utils/customize/**/*.py` の二重追加を削除する。
- Application Source に渡すファイル一覧の配置先パスを一意化する。
- 同じ配置先に異なるローカルファイルが割り当てられた場合は、DataRobot API 送信前に `ValueError` で失敗させる。
- `ApplicationSource` の置換時に古い source を削除しないよう、Pulumi の `retain_on_delete=True` を設定する。
  - DataRobot 側では古い source が Custom Application から参照中と判定され、DELETE が 422 になることがあるため。
  - 古い source は DataRobot 上に残るが、CD の更新を優先する。
- CD の `pulumi up` に `refresh: true` を設定する。
  - 失敗済み update で Pulumi state に残った pending delete を、次回 update 前に実リソース状態と同期して解消するため。
- refresh は Pulumi program が `app_backend/app_infra.json` を生成する前に state の file hash を読むため、CD 側で事前に `app_infra.json` を作成する。
- refresh は Pulumi program 内の frontend build より前に `app_backend/static/*` の file hash も読むため、CD 側で事前に React frontend を build する。
- frontend build 後も state に旧 hash 付き asset 名が残る場合があるため、refresh 前に Pulumi stack を export し、state が参照する missing file を `.github/scripts/prepare_pulumi_refresh_files.py` で補完する。

## テスト

- `customize_docs/test_application_source_file_manifest.py`
  - `get_app_files()` の返却する配置先パスに重複がないことを検証する。
  - 今回ログに出た `utils/customize/api_endpoints/report.py` が 1 件だけ含まれることを検証する。
- `customize_docs/test_application_source_retention.py`
  - App と Dashboard の `ApplicationSource` に `retain_on_delete=True` が設定されていることを検証する。
- `.github/workflows/pulumi-up.yml`
  - YAML として parse できること、refresh 前の `app_infra.json` 作成 step、frontend build step、state file 補完 step があること、main/dev 両方の Pulumi action に `refresh: true` が設定されていることを確認する。
- `.github/scripts/prepare_pulumi_refresh_files.py`
  - Pulumi state の ApplicationSource `files` から missing file を抽出し、同種の現在 asset または placeholder で補完できることを確認する。
