# Submit Actuals Telemetry Restore

## 背景

2026-06-22 の router split 後、チャット実行経路の
`core.routers.chats.run_complete_analysis_task()` から
`core.api.run_complete_analysis()` へ `telemetry_json` が渡されなくなっていた。

`run_complete_analysis()` 配下の LLM 呼び出しは `telemetry_json is not None` の場合だけ
`async_submit_actuals_to_datarobot()` を起動するため、通常チャット経路では actuals submit
まで到達していなかった。

## 変更内容

- 旧 `rest_api.py` と同様に、チャット request の `x-user-email` と最後のユーザーメッセージを
  `telemetry_json` として復元した。
- `run_complete_analysis()` 呼び出しに `telemetry_json=telemetry_json` を渡すようにした。
- 回帰テストとして、router task が `telemetry_json` を `run_complete_analysis()` に渡すことを固定した。

## テスト方針

- RED: `run_complete_analysis_task()` が `telemetry_json` を渡さない現状で失敗することを確認。
- GREEN: `telemetry_json` 復元後に同テストが通ることを確認。
- 既存回帰: `run_complete_analysis()` 内部の telemetry propagation と router split の既存テストを実行する。
