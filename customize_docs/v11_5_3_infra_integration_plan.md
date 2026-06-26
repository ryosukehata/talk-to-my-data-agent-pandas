# v11.5.3 インフラ取り込み計画

## 目的

upstream `v11.5.3` のうち、デプロイ・runtime parameter・起動資材に関わる差分を、このリポジトリの既存Pulumi構成に合わせて取り込む。

## 取り込む範囲

- `.env.template` に `USE_BUILDER_API_TOKEN=false` を追加する。
- DataRobotアプリケーションのruntime parameterに `USE_BUILDER_API_TOKEN` を渡す。
- `infra/configurations/llm/*` を upstream `v11.5.3` と同じ Pulumi resource style に戻し、アプリruntime parameterに同じキーを渡す。
- `infra/` を upstream `v11.5.3` と同じ `infra/Pulumi.yaml` / `infra/infra/*` package構成へ寄せる。
- デプロイ資材にgit由来の `VERSION` ファイルを含める。
- `app_backend/start-app.sh` を、`uv` がある環境とprebuilt Python環境の両方で起動できるようにする。

## 今回見送る範囲

- frontend CIの `npm ci` 化とcoverage job追加は見送る。現状の `app_frontend/package.json` と `package-lock.json` が同期しておらず、`npm ci` が失敗するため。
- upstreamの `tests/e2e/Taskfile.yaml` 前提のTaskfile差分は見送る。このリポジトリには該当ディレクトリがまだ存在しないため。
- 生成済みlockfile・requirementsの大規模更新は見送る。backend/frontend/infraのPR分割を維持し、今回のruntime parameter取り込みに必要な最小差分へ限定する。

## テスト方針

- `customize_docs/test_v11_5_3_infra_config.py`
  - `.env.template` がbuilder token toggleを文書化していること。
  - 全LLM設定ファイルが upstream と同じ `ApplicationSourceRuntimeParameterValueArgs` / `CustomModelRuntimeParameterValueArgs` の構成を持ち、`USE_BUILDER_API_TOKEN` をアプリruntime parameterへ渡すこと。
  - `infra/infra/app_backend.py` がLLM設定ファイルのruntime parameterをアプリruntime parameterへ取り込むこと。
  - `infra/` が upstream 型の split package 構成になり、旧 `settings_*` 構成が残っていないこと。
  - `start-app.sh` が `uv` とprebuilt Python fallbackの両方を持つこと。
  - `VERSION` ファイル生成処理とgitignoreが揃っていること。

## 検証結果

- `uv run pytest customize_docs/test_v11_5_3_infra_config.py -q`
- `uv run pytest customize_docs/test_v11_5_3_infra_config.py customize_docs/test_llm_runtime_parameters.py customize_docs/test_application_source_file_manifest.py app_backend/tests/test_llm_configuration.py -q`
- 2026-06-23 最新 `dev` 追従後、旧 `pulumi-up.yml` / `python-unit-tests.yml` 前提の仕様テストを新しい backend/core/frontend/infra 分割 workflow 前提へ更新。
  - `uv run pytest customize_docs/test_v11_5_3_infra_config.py customize_docs/test_llm_runtime_parameters.py customize_docs/test_application_source_file_manifest.py customize_docs/test_pulumi_workflow_refresh.py customize_docs/test_taskfile_deployment_dx.py -q`: 13 passed
- 2026-06-26 PR #103 follow-upで、`infra/configurations/llm/*` の import-safe helper を削除し、upstream `v11.5.3` と同じトップレベル Pulumi resource 構成へ戻した。外部DataRobot接続が必要な import 実行テストは行わず、ASTでruntime parameter契約を検証する。
  - `uv run --project app_backend pytest app_backend/tests/test_llm_configuration.py -q`: 4 passed
  - `uv run pytest customize_docs/test_v11_5_3_infra_config.py -q`: 5 passed
- 2026-06-26 追加follow-upで、`infra/Pulumi.yaml` / `infra/infra/*` / `infra/feature_flags/*` を upstream 型へ移行した。旧 `infra/settings_*` と直下 `infra/components` は削除し、既存のApplicationSource manifest、optional custom jobs、monitoring、cleanup jobは `infra/infra/app_backend.py` に移した。
- 2026-06-27 追加follow-upで、実デプロイ済みTextGen deploymentを使う構成に合わせ、既定の `infra/infra/llm.py` symlink、`.datarobot/cli/llm.yml` のdefault、`.env.template`、READMEを `deployed_llm.py` 基準へ変更した。
- 2026-06-27 CD復元PRで、upstreamの分割CI構成は維持しつつ、このリポジトリ固有の `.github/workflows/pulumi-up.yml` を再追加した。workflowは `main` / `dev` へのpushで `infra/` Pulumi projectから `pulumi up --refresh` を実行し、従来のOpenAI利用に合わせて `blueprint_with_external_llm.py` と `OPENAI_*` secrets を使う。
