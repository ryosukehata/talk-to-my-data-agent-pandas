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
- `CUSTOM_JOB_SCHEDULE_ID` は `custom_job.schedule_id` を export する。
- schedule 作成のための `CustomJobPostActions` と、事前削除の
  `CustomJobScheduleCleanup` を削除する。

## テスト

- `customize_docs/test_custom_job_schedule_resource.py`
  - schedule が provider の `CustomJobScheduleArgs` として構成されることを確認する。
  - Pulumi stack 定義に手動 schedule post-action が残っていないことを確認する。
