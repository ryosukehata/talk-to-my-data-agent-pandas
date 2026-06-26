# Upstream follow-up backlog

このファイルは、upstream 追従で意図的に後回しにした構造変更や、次の大きめの同期作業で再評価すべき課題を管理する。

## v11.5.1 で残した構造課題

v11.5.1 取り込みでは、既存の pandas 公開挙動、customize routes、session middleware、static frontend fallback、root Pulumi project、既存 CI 実行範囲を壊さないことを優先した。そのため、以下は処理済み baseline の外に残した将来課題として扱う。

### Router split の全面移行

- upstream の `core/src/core/routers/*` 分割へ移行し、monolithic な `core.rest_api` への依存を減らす。
- 移行時は `get_initialized_db`、`run_complete_analysis_task`、customize routes、backend monkeypatch tests、static frontend fallback、session middleware の互換を先にテストで固定する。
- `utils.rest_api` / `core.rest_api` の互換 re-export をいつ削減できるかも併せて判断する。

### Infra package の大移動 (2026-06-26 対応済み)

- PR #103 follow-upで upstream の `infra/Pulumi.yaml` / `infra/infra/*` 構成へ移行した。
- 旧 `infra/settings_*` と直下 `infra/components` は削除し、ApplicationSource file manifest、custom job、cleanup job、monitoring、report builder feature flags は `infra/infra/app_backend.py` に移した。
- 回帰は `customize_docs/test_v11_5_3_infra_config.py`、`customize_docs/test_application_source_file_manifest.py`、`customize_docs/test_custom_job_schedule_resource.py` で固定する。

### Lock file / workflow 再編

- upstream の backend / core / frontend / infra workflow 分割と lock 管理へ寄せるかを検討する。
- ただし、この fork では `app_backend/tests` だけでなく `customize_docs` tests が仕様回帰を守っているため、CI 実行範囲を狭めない。
- pandas 維持方針と矛盾する依存更新、Polars 前提の lock 差分、DataRobot deploy workflow への影響は別PRで検証する。

## v11.5.3 frontend マージ後に再評価した課題

### React 静的配信方式の upstream 追従 (2026-06-27 対応済み)

- `origin/dev` に frontend PR #102 が merge 済みになったため、upstream `v11.5.3` の `TemplateResponse` / Vite manifest ベースのReact配信方式を評価した。
- 更新追従コストを下げるため、`app_backend/app/__init__.py`、`app_backend/templates/index.html`、`app_backend/tests/test_main.py` は upstream `v11.5.3` と一致させた。
- fork側で必要な差分は、monorepo import 用の `app_backend/tests/conftest.py` 補助と、upstreamの非キャッシュ `create_app()` 挙動に合わせた既存追加テストの期待値更新だけに限定した。
- 実装とテスト方針は `customize_docs/v11_5_3_static_frontend_manifest.md` に分離して記録した。

### pandas から Polars への境界再評価

- 現時点では pandas 公開挙動を維持するが、将来 upstream 追従コストが大きくなった場合は、`AnalystDataset.to_df()`、generated code、dictionary、cleansing、frontend dataset表示への影響を見積もる。
- 移行する場合も一括置換ではなく、登録境界、analysis result、dictionary generation など境界単位で TDD する。
