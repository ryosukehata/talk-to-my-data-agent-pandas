# v0.5.3 integration plan

## 目的

upstream `datarobot-community/talk-to-my-data-agent` の `v0.5.3` 差分を、pandas 前提と既存カスタム機能を維持したまま `dev` へ統合する。
あわせて、このリポジトリで `main` 向けに出ている open PR を `dev` 側の統合対象へ巻き込む。

## 現在地

- 作成ブランチ: `codex/v0.5.3-integration-plan`
- 起点: `origin/dev` `7e994ec`
- upstream tag: `v0.5.2` `6e6b80b`, `v0.5.3` `be8ba20`
- `git merge-base --is-ancestor v0.5.2 origin/dev` は `1`。内容として v0.5.2 は取り込み済みだが、履歴上は upstream tag が祖先ではない。
- `v0.5.2..v0.5.3` の upstream 差分は 64 files, 1810 insertions, 588 deletions。

## 標準方針

- 一括 merge ではなく、`v0.5.2..v0.5.3` の差分を小さい PR に分けて移植する。
- Polars 差分は pandas へ再移植しない。ただし、同じ不具合が現行 pandas 実装にも存在する場合は、pandas 実装としてテスト付きで直す。
- upstream の theme provider / light theme は v0.5.2 PR で先行採用済みのため、v0.5.3 では差分を重複適用しない。
- `utils/customize/*` と report builder / custom prompts / template selector は維持する。upstream 側に存在しないため、単純 merge で削除させない。
- `main` 向け Dependabot PR は統合PR内で取り込むが、互換性リスクのあるものはテストを追加してから採用する。

## v0.5.3 採用判断

| 項目 | 判断 | 理由 |
| --- | --- | --- |
| Sidebar / layout refresh | 採用候補 | `app_frontend/src/components/ui/sidebar.tsx`, `sheet.tsx`, `Sidebar.tsx`, `Layout.tsx` が主差分。既存 custom navigation と Settings 導線を壊さない条件で採用する。 |
| Light theme support | 差分確認のみ | v0.5.2 PR で upstream `ThemeProvider` / `theme/*` を先行採用済み。v0.5.3 側の残差分だけ確認する。 |
| Chat message persistence | 採用候補 | `chat-messages/hooks.ts`, `types.ts`, `Chats.tsx` 周辺。既存 chat API と report/custom prompt 導線への影響をテストで固定する。 |
| UI registry components | 採用候補 | `collapsible`, `command`, `radio-group`, `tabs`, `toggle-group`, `sonner` 等。v0.5.2 で入れた UI primitive と衝突するため、component 単位で比較する。 |
| `TokenUsageDisplay` 削除 | 条件付き採用 | 表示要件が既存UIに残っていないことをテスト/画面確認してから削除する。 |
| `knip` CI 追加 | 条件付き採用 | custom prompts / reports / templates は upstream にないため、unused 判定に巻き込まれやすい。ignore 設定を先に整える。 |
| `utils/api.py` sample size 100 -> 500 | 採用候補 | pandas 実装でも意味がある安全な差分。回帰テストを先に追加する。 |
| `utils/data_cleansing_helpers.py` first-column threshold | 原則見送り | upstream は Polars 前提。現行 pandas cleansing に同じ誤変換がある場合だけ pandas 実装として別途対応する。 |
| Streamlit legacy差分 | 原則見送り | v0.5.2 で非推奨案内のみ採用済み。legacy Streamlit の機能改修はしない。 |

## main 向け open PR の巻き込み

### このリポジトリ

| PR | 対象 | 方針 | 注意点 |
| --- | --- | --- | --- |
| [#77](https://github.com/ryosukehata/talk-to-my-data-agent-pandas/pull/77) | `resources/app_usage_dashboard/requirements.txt`: `requests 2.32.2 -> 2.33.0` | 採用候補 | resource dashboard の依存だけ。install smoke test を追加/実行する。 |
| [#78](https://github.com/ryosukehata/talk-to-my-data-agent-pandas/pull/78) | `resources/app_usage_dashboard/requirements.txt`: `streamlit 1.44.1 -> 1.54.0` | 条件付き採用 | Streamlit 1.54 は breaking change を含む。dashboard が `st.experimental_*` に依存していないか確認する。 |
| [#79](https://github.com/ryosukehata/talk-to-my-data-agent-pandas/pull/79) | `requirements.txt`, `app_backend/requirements.txt`: `pillow 11.3.0 -> 12.2.0` | 条件付き採用 | PR は unstable。`app_backend/pyproject.toml` も `pillow==11.3.0` のため、採用するなら pyproject も揃える。 |

### upstream main 向け open PR

| PR | 判断 | 理由 |
| --- | --- | --- |
| [upstream #14](https://github.com/datarobot-community/talk-to-my-data-agent/pull/14) | 採用候補 | `.env.template` のコメント移動のみ。競合が軽ければ v0.5.3 docs/config PR に含める。 |
| [upstream #26](https://github.com/datarobot-community/talk-to-my-data-agent/pull/26) | 見送り | custom dictionary + frontend + `core/` 前提の大きな差分。現在の pandas/customize 構成とは別設計PRで扱う。 |
| upstream Dependabot PRs | 見送り寄り | `actions/checkout@6`, `pydantic-settings==2.11.0`, `kaleido==1.1.0`。CI/runtime影響が大きいため、v0.5.3統合からは分離する。 |

## PR分割案

### PR0: v0.5.2 baseline

目的: v0.5.2 が内容上取り込み済みであることを履歴にも反映し、v0.5.3 の merge-base を正常化する。

手順:

1. `origin/dev` から `codex/upstream-sync-v0.5.2-baseline` を作成する。
2. `git merge -s ours --no-ff v0.5.2^{commit}` を実行する。
3. 内容差分が出ていないことを確認する。

確認:

- `git merge-base --is-ancestor v0.5.2 HEAD`
- `git diff --stat HEAD^1..HEAD`
- `uv run pytest app_backend/tests customize_docs -q`

### PR1: v0.5.3 frontend shell/sidebar

目的: sidebar / layout / mobile sheet まわりを upstream v0.5.3 に寄せる。

対象:

- `app_frontend/src/components/Sidebar.tsx`
- `app_frontend/src/components/ui/sidebar.tsx`
- `app_frontend/src/components/ui/sheet.tsx`
- `app_frontend/src/pages/Layout.tsx`
- `app_frontend/src/assets/chat-light.svg`
- `app_frontend/src/theme/theme-provider.tsx`

TDD:

1. Sidebar が Datasets / Chats / Settings を表示し、Settings modal を開けることを固定する。
2. light/dark theme で DataRobot logo が切り替わることを固定する。
3. mobile viewport で sidebar sheet が開閉できることを Playwright または RTL で固定する。

確認:

- `npm --prefix app_frontend test`
- `npm --prefix app_frontend run lint`
- `npm --prefix app_frontend run build`
- Browser で Data / Chats / Settings を確認する。

### PR2: v0.5.3 chat/data UI integration

目的: chat persistence と data UI の v0.5.3 差分を既存 custom UI と統合する。

対象:

- `app_frontend/src/api/chat-messages/*`
- `app_frontend/src/pages/Chats.tsx`
- `app_frontend/src/components/chat/*`
- `app_frontend/src/components/data/*`
- `app_frontend/src/components/DataSourceSelector.tsx`
- `app_frontend/src/components/AddDataModal.tsx`

TDD:

1. chat message API hooks/types が既存 API response と一致することを固定する。
2. persisted messages が app restart 相当の reload 後にも表示される想定をテストする。
3. data type editing warning が表示され、既存 dataset action bar が壊れないことを固定する。
4. custom prompts / reports / templates の import と画面導線が残ることを確認する。

### PR3: v0.5.3 backend / cleansing

目的: pandas 前提を維持しながら v0.5.3 の非Polars backend差分だけを採用する。

対象:

- `utils/api.py`
- `utils/data_cleansing_helpers.py`
- 必要に応じて `app_backend/tests/*`

TDD:

1. `cleanse_dataframe()` が最大 500 行を sample に使うことを固定する。
2. 先頭列の ID 文字列が numeric conversion されない挙動が現行 pandas 実装にも必要か確認する。
3. `execute_python` の allowed modules に `polars` が追加されていないことを維持する。

確認:

- `uv run pytest app_backend/tests customize_docs -q`
- `uv run ruff check utils/api.py utils/data_cleansing_helpers.py`

### PR4: main PR dependency rollup

目的: `main` 向け Dependabot PR #77/#78/#79 を `dev` 統合へ巻き込む。

対象:

- `resources/app_usage_dashboard/requirements.txt`
- `requirements.txt`
- `app_backend/requirements.txt`
- `app_backend/pyproject.toml`

TDD/確認:

1. `python3 -m pip install -r resources/app_usage_dashboard/requirements.txt` を確認する。
2. `streamlit` 1.54 で dashboard が import できる smoke test を追加する。
3. `pillow` 12.2 を採用する場合は root/app_backend requirements と `app_backend/pyproject.toml` を揃える。
4. `uv run pytest app_backend/tests customize_docs -q` と `python-deps-install-test` 相当を実行する。

## 最終確認

v0.5.3 全PRが `dev` に入った後に確認する。

- `git merge-base --is-ancestor v0.5.3 dev`
- `npm --prefix app_frontend test`
- `npm --prefix app_frontend run lint`
- `npm --prefix app_frontend run build`
- `uv run pytest app_backend/tests customize_docs -q`
- `uv run ruff format --check .`
- `uv run ruff check .`

## 実装しないもの

- Polars 実装を pandas へ移植する作業。
- `core/` package 再編の先行取り込み。
- upstream #26 の custom dictionary 全面採用。
- legacy Streamlit の機能改修。

## 実装メモ

- 2026-06-08: `dev` が内容上 `v0.5.2` 済みであるため、`v0.5.2` は `ours` baseline merge として履歴に反映した。その上で upstream `v0.5.3` を通常 merge し、衝突箇所は upstream の light theme/sidebar 実装を優先しながら pandas 実装と既存 custom prompts / reports / templates 導線を維持した。
- Frontend は v0.5.3 の `SidebarProvider`, `sheet`, `chat-light.svg`, chat draft persistence, UI primitive 更新を採用した。既存 fork 側の `Button` variant (`default`, `outline`, `secondaryRound`) と `testId` prop は互換 API として残した。
- `AddDataModal` は upstream の `Loader2` loading icon に統一し、古い `loader.svg` 参照を削除した。
- Backend cleansing は pandas 前提を維持したまま、`cleanse_dataframe()` の sample 上限を 500 行へ更新した。`data_cleansing_helpers` は Polars へ移植せず、先頭列だけ numeric conversion threshold を 100% にする upstream の誤変換対策を pandas 実装として採用した。
- 追加テスト: `app_backend/tests/test_data_cleansing_v053_compat.py`。先頭列 ID の誤数値化防止と、sample 上限 500 行を検証する。
- Test setup は v0.5.3 の responsive sidebar が `window.matchMedia` を使うため、`app_frontend/tests/setupTests.ts` に jsdom 用 mock を追加した。
