# Pulumi Custom Job schedule

## 背景

GitHub Actions の Pulumi CD で、`ApplicationSource` 更新と `CustomApplication`
更新は完了した後、`custom:resource:CustomJobPostActions
custom-job-post-actions` の表示を最後に処理が進まなくなった。

`CustomJobPostActions` は `pulumi.Output.apply()` の中で DataRobot API を直接呼び、
Usage Export Job の schedule を作成していた。ログ上は schedule 作成 API が 201 を返して
いたが、ComponentResource が完了扱いにならず Pulumi update が待ち続けた。

## 対応

- Usage Export Job の schedule は `pulumi-datarobot` provider の
  `CustomJob(schedule=CustomJobScheduleArgs(...))` で管理する。
- `CUSTOM_JOB_SCHEDULE_ID` の stack export は削除する。
  - 既存 CustomJob の `schedule_id` が provider 側で解決されない場合に、stack output
    待ちで update が止まる余地をなくすため。
- schedule 作成のための `CustomJobPostActions` と、事前削除の
  `CustomJobScheduleCleanup` を削除する。
- 既存 Pulumi state に残った上記 component は、CD の refresh 前に
  `.github/scripts/find_pulumi_state_resources.py` で URN を抽出し、
  `pulumi state delete` で削除する。
  - これらは ComponentResource であり、物理 DataRobot resource は持たない。

## テスト

- `customize_docs/test_custom_job_schedule_resource.py`
  - schedule が provider の `CustomJobScheduleArgs` として構成されることを確認する。
  - Pulumi stack 定義に手動 schedule post-action が残っていないことを確認する。
- `customize_docs/test_find_pulumi_state_resources.py`
  - stack export から古い custom job component の URN だけを抽出することを確認する。
- `customize_docs/test_pulumi_workflow_refresh.py`
  - refresh 前に古い custom job component state を削除する step があることを確認する。
