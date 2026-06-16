# Upstream follow-up backlog

このファイルは、upstream 追従で意図的に後回しにした構造変更や、次の大きめの同期作業で再評価すべき課題を管理する。

## v11.5.1 で残した構造課題

v11.5.1 取り込みでは、既存の pandas 公開挙動、customize routes、session middleware、static frontend fallback、root Pulumi project、既存 CI 実行範囲を壊さないことを優先した。そのため、以下は処理済み baseline の外に残した将来課題として扱う。

### Router split の全面移行

- upstream の `core/src/core/routers/*` 分割へ移行し、monolithic な `core.rest_api` への依存を減らす。
- 移行時は `get_initialized_db`、`run_complete_analysis_task`、customize routes、backend monkeypatch tests、static frontend fallback、session middleware の互換を先にテストで固定する。
- `utils.rest_api` / `core.rest_api` の互換 re-export をいつ削減できるかも併せて判断する。

### Infra package の大移動

- upstream の `infra/Pulumi.yaml` / `infra/infra/*` 構成へ寄せるかを再評価する。
- 現行の root `Pulumi.yaml`、`pulumi-up.yml`、`infra/settings_*`、custom job、cleanup job、monitoring、report builder feature flags、ApplicationSource file manifest への影響を小さい PR で切り分ける。
- 移行する場合は `customize_docs/test_application_source_file_manifest.py`、`customize_docs/test_pulumi_workflow_refresh.py`、custom job / optional resource のテストを先に拡張する。

### Lock file / workflow 再編

- upstream の backend / core / frontend / infra workflow 分割と lock 管理へ寄せるかを検討する。
- ただし、この fork では `app_backend/tests` だけでなく `customize_docs` tests が仕様回帰を守っているため、CI 実行範囲を狭めない。
- pandas 維持方針と矛盾する依存更新、Polars 前提の lock 差分、DataRobot deploy workflow への影響は別PRで検証する。

### pandas から Polars への境界再評価

- 現時点では pandas 公開挙動を維持するが、将来 upstream 追従コストが大きくなった場合は、`AnalystDataset.to_df()`、generated code、dictionary、cleansing、frontend dataset表示への影響を見積もる。
- 移行する場合も一括置換ではなく、登録境界、analysis result、dictionary generation など境界単位で TDD する。
