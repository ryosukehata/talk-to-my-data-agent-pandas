# Pulumi frontend build

## 背景

GitHub Actions の Pulumi CD では、workflow 側で frontend assets を事前に build してから
Pulumi update を実行している。

一方で Pulumi stack 内にも `command:local:Command` の frontend build resource があり、
毎回 `triggers=[time.time()]` で replacement されていた。ApplicationSource /
CustomApplication / CustomJob の更新が完了した後も Pulumi update が終了しない run で、
cleanup 時に `pulumi-resource-command` process が残っていた。

## 対応

- CI では `SKIP_PULUMI_FRONTEND_BUILD=true` を設定し、Pulumi stack 内の
  `command:local:Command` frontend build resource を作らない。
- workflow の事前 build 成果物を `settings_app_infra.get_app_files()` で直接読む。
- 既存 Pulumi state に残った `command:local:Command` は update 前に
  stack export JSON から prune し、`pulumi stack import` で反映する。
  - 失敗した replacement が複数残ると同一 URN が曖昧になり、`pulumi state delete`
    では削除できないため。
- CI では `SKIP_PULUMI_CUSTOM_JOBS=true` も設定し、`pulumi-datarobot` provider の
  CustomJob 更新を避ける。
  - command resource を外した後も `datarobot:index:CustomJob Usage Export Job`
    の更新完了直後に update が終了しないため。
  - 既存 DataRobot CustomJob は削除せず、Pulumi state からのみ prune する。
- ローカル実行では env を設定しない限り、従来通り Pulumi 内で frontend build を実行する。

## テスト

- `customize_docs/test_pulumi_frontend_build.py`
  - Pulumi stack が事前 build 済み frontend assets を直接使えることを確認する。
- `customize_docs/test_pulumi_workflow_refresh.py`
  - workflow が `command:local:Command` state を事前 prune することを確認する。
  - Pulumi action に `SKIP_PULUMI_FRONTEND_BUILD=true` が渡ることを確認する。
- `customize_docs/test_prune_pulumi_state_resources.py`
  - stack export から対象 type の resources と、その依存参照を削除することを確認する。
