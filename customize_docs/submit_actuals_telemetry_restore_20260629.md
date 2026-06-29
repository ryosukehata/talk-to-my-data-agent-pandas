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
- actuals submit の association ID は、LLM Gateway レスポンス直下の
  `datarobot_association_id` を使うようにした。`datarobot_moderations.association_id` は
  moderation 用の ID で、prediction export の `association_id` とは一致しないため使用しない。
- `datarobot_association_id` が取得できない場合は、別IDへフォールバックせずにエラーにする。

## 実APIでの整合性確認

対象デプロイ: `6a4230d722173b17e5a9b960`

2026-06-29 に実際の chat completions API と prediction data export を突き合わせた。

- probe: `codex_assoc_probe_20260629T113247Z`
- chat response の `datarobot_association_id`: `112498d1-dede-493f-b70c-5482d101a1a8`
- chat response の `datarobot_moderations.association_id`: `c42fafa6-7edb-4387-8ba6-d9b7a0de3b31`
- export dataset: `6a42588466aaee5f1729ed60`
- export version: `6a42588466aaee5f1729ed61`

prediction export CSV では、`datarobot_association_id` と同じ
`112498d1-dede-493f-b70c-5482d101a1a8` の行が 1 件存在し、同じ行に actual_value が付いた。
一方で `datarobot_moderations.association_id` の行は 0 件だった。

## テスト方針

- RED: `run_complete_analysis_task()` が `telemetry_json` を渡さない現状で失敗することを確認。
- GREEN: `telemetry_json` 復元後に同テストが通ることを確認。
- 既存回帰: `run_complete_analysis()` 内部の telemetry propagation と router split の既存テストを実行する。
- association ID: `datarobot_association_id` を使い、`datarobot_moderations.association_id` に
  フォールバックしないことを単体テストで固定する。
