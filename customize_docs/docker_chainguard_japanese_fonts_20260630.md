# Docker Chainguard FIPS Japanese Font Support

## 背景

DataRobot の Python FIPS dev ベースイメージへ移行するため、Dockerfile のベースイメージを `datarobot/mirror_chainguard_datarobot.com_python-fips:3.12-dev` に変更する。

既存の Dockerfile は Debian slim 前提で `apt-get` を使って `fonts-noto-cjk` を導入していたが、Chainguard/Wolfi 系イメージでは `apk` を使う。

## 実装方針

- ベースイメージを DataRobot mirror の Chainguard Python FIPS 3.12 dev に変更する。
- 日本語表示に必要な `font-noto-cjk` と、フォント検出に必要な `fontconfig` を `apk add --no-cache` で導入する。
- `fc-cache -f` でフォントキャッシュを更新する。
- `poetry` と `uv` は `python -m pip install --no-cache-dir poetry uv` で導入する。
- Debian 前提の `SHELL ["/bin/bash", ...]` と `apt-get` は削除する。
- Plotly の静的画像出力では `Noto Sans CJK JP, Noto Sans JP, sans-serif` を指定し、Wolfi の `font-noto-cjk` で見つかりやすい `Noto Sans CJK JP` を優先する。
- Pulumi はデフォルトで `docker/Dockerfile` から `datarobot.ExecutionEnvironment` を作成し、その `version_id` を `ApplicationSource.base_environment_version_id` に渡す。
- 既存環境を使いたい場合だけ `APPLICATION_EXECUTION_ENVIRONMENT_ID` / `APPLICATION_EXECUTION_ENVIRONMENT_VERSION_ID` を指定して Pulumi 管理の Dockerfile 環境をバイパスする。
- CD の `pulumi-up.yml` では既存環境 ID を渡さないため、通常の CD も Pulumi 管理の Dockerfile 環境を使う。

## テスト

`app_backend/tests/test_dockerfile_runtime_contract.py` で以下を検証する。

- Dockerfile が `datarobot/mirror_chainguard_datarobot.com_python-fips:3.12-dev` を使用していること。
- `apk add --no-cache` で `fontconfig` と `font-noto-cjk` を導入していること。
- `apt-get` が残っていないこと。
- Pulumi が `USE_JAPANESE_FONT_ENV` なしで Dockerfile の `ExecutionEnvironment` を作成し、`version_id` を ApplicationSource に渡すこと。
- CD workflow が既存環境 ID を渡さず、Pulumi 管理の Dockerfile 環境を使うこと。
- `RunChartsResult` が `fig1` / `fig2` の Plotly figure 復元時に日本語フォントのフォールバックを設定すること。

## 検証メモ

- `task infra:install`: 成功。
- `uv run --project infra pulumi version`: 成功。
- `infra/` で `pulumi stack select dev --non-interactive`: 成功。
- `infra/` で `.env` を読み込んだ `uv run pulumi preview --non-interactive`: `deployed_llm.py` が要求する `TEXTGEN_DEPLOYMENT_ID` 未設定で停止。Dockerfile 環境作成ロジックに到達する前の LLM 設定不足。
