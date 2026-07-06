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
- 2026-07-06 の `Pulumi Up` workflow では、Pulumi 実行前の
  `Build frontend assets for Pulumi refresh` step で `npm install` が `ECONNRESET`
  により失敗した。
  - upstream の frontend workflow と同じく `npm install` を使う。
  - `app_frontend/package-lock.json` は git 管理されていないため、`npm ci` や
    `actions/setup-node` の `cache-dependency-path` は使わない。
  - registry fetch の一時失敗に備えて `npm install` を 3 回まで再試行する。
- workflow の事前 build 成果物を `infra/infra/app_backend.py` の `get_app_backend_app_files()` で直接読む。
- 既存 Pulumi state に残った `command:local:Command` は update 前に
  stack export JSON から prune し、`pulumi stack import` で反映する。
  - 失敗した replacement が複数残ると同一 URN が曖昧になり、`pulumi state delete`
    では削除できないため。
- CI では `SKIP_PULUMI_CUSTOM_JOBS=true` も設定し、`pulumi-datarobot` provider の
  CustomJob 更新を避ける。
  - command resource を外した後も `datarobot:index:CustomJob Usage Export Job`
    の更新完了直後に update が終了しないため。
  - 既存 DataRobot CustomJob は削除せず、Pulumi state からのみ prune する。
- CI では `DISALLOW_MONITORING_RESOURCES=true` も設定し、usage dashboard と
  monitoring datasets も Pulumi state からのみ prune する。
  - CustomJob を外した後も `Data Analyst Dashboard [dev]` の更新が完了せず、
    update が終了しないため。
- CI では main app の `Data Analyst App Source` も Pulumi state から prune する。
  - `ApplicationSource` / `CustomApplication` 更新後に旧 source を delete original
    しようとして、DataRobot API が 422 `This entity is in use by a custom application`
    を返すため。
  - 既存 DataRobot app source は削除せず、新しい source 作成と app 更新だけを
    Pulumi に実行させる。
- ローカル実行では env を設定しない限り、従来通り Pulumi 内で frontend build を実行する。

## テスト

- `customize_docs/test_pulumi_frontend_build.py`
  - Pulumi stack が事前 build 済み frontend assets を直接使えることを確認する。
- `customize_docs/test_pulumi_workflow_refresh.py`
  - workflow が `command:local:Command` state を事前 prune することを確認する。
  - workflow が branch に対応した resource name で App Source / monitoring state を
    事前 prune することを確認する。
  - Pulumi action に `SKIP_PULUMI_FRONTEND_BUILD=true` が渡ることを確認する。
  - frontend assets build で `npm install` と fetch retry が設定されることを確認する。
  - git 管理されていない `package-lock.json` に依存する npm cache 設定を入れないことを確認する。
- `customize_docs/test_prune_pulumi_state_resources.py`
  - stack export から対象 type の resources と、その依存参照を削除することを確認する。
