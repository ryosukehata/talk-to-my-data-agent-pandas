# Main CD Existing Execution Environment

## 背景

dev で作成済みの DataRobot Execution Environment を main の Pulumi Up でも再利用できるようにする。

このリポジトリの CD workflow は `dev` branch と `main` branch のどちらも GitHub Environment `main` を参照するため、単純に secret を追加すると `dev` の Pulumi Up にも同じ既存環境 ID が渡る。dev は引き続き Dockerfile から Pulumi 管理の Execution Environment を作る挙動を維持し、main のみ既存環境 ID を参照する。

## 実装

`.github/workflows/pulumi-up.yml` の `jobs.update.env` に以下を追加する。

- `APPLICATION_EXECUTION_ENVIRONMENT_ID`
- `APPLICATION_EXECUTION_ENVIRONMENT_VERSION_ID`

どちらも `github.ref == 'refs/heads/main'` のときだけ GitHub secret を渡し、`dev` では空文字を渡す。`infra/infra/app_backend.py` は空文字を未指定として扱うため、dev では既存どおり Dockerfile から Execution Environment を作成する。

## GitHub secret

main で既存環境を使う場合は、GitHub Environment `main` に以下を設定する。

- `APPLICATION_EXECUTION_ENVIRONMENT_ID`: dev で作成済みの Execution Environment ID
- `APPLICATION_EXECUTION_ENVIRONMENT_VERSION_ID`: 特定バージョンに固定したい場合だけ設定

## テスト

- `customize_docs/test_pulumi_workflow_refresh.py`
  - Pulumi Up workflow が main 限定で既存環境 secret を env に渡すことを確認する。
- `app_backend/tests/test_dockerfile_runtime_contract.py`
  - `dev` では空文字になり、Pulumi 管理の Dockerfile 環境を維持する契約を確認する。
