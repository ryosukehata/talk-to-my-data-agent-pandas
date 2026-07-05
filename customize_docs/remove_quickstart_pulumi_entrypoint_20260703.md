# quickstart.py 削除と Pulumi 起動経路整理

## 背景

CD は `.github/workflows/pulumi-up.yml` で `infra/` を working directory にし、`task install` 後に `pulumi/actions@v6` から `pulumi up` を実行している。

一方、旧 `quickstart.py` は root Pulumi project と root `requirements.txt` 前提の独自セットアップ経路で、現在の `infra/Pulumi.yaml` と `infra/pyproject.toml` を使う構成とずれていた。

## 方針

- upstream に無い `quickstart.py` は削除する。
- README の手順は `dr start` と Taskfile に統一する。
- リソース削除手順も root `pulumi down` ではなく `task infra:down-yes` に統一する。
- 手動 Pulumi 実行は `infra/` で `uv run pulumi ...` を使う手順にする。
- Windows 用 `set_env.bat` と PowerShell 用 `Set-Env.ps1` から `quickstart.py` import 依存を外す。
- エージェント向け手順も `dr start` / `task deploy` に更新する。

## テスト

- `customize_docs/test_quickstart_removed.py`
  - `quickstart.py` が存在しないこと。
  - README が旧 `quickstart.py` / root `requirements.txt` / root `pulumi down` 手順を案内していないこと。
  - `set_env.bat` / `Set-Env.ps1` が `quickstart.py` に依存していないこと。
  - `AGENTS.md` が `dr start` / `task deploy` を案内していること。
