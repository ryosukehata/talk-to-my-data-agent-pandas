# v11.5.3 frontend integration plan

## 目的

upstream `v11.5.3` の frontend 挙動修正を、現行 fork の template / custom prompt / report builder UI を維持したまま取り込む。

## 対象

- Settings modal に runtime `APP_VERSION` を表示。
- DataRobot account 表示で `firstName` / `lastName` を優先し、表示名が空の場合は `Connected as` 行を隠す。
- chat 作成 / rename 入力に 200 文字上限と上限到達メッセージを追加。
- Data Registry / Remote Data Connections が seat license で 403 の場合、React Query retry を止め、該当選択肢を disabled にする。
- local file upload 画面に privacy notice と Privacy Policy link を追加。
- Raw Rows タブでは dictionary download action を表示しない。
- `USER_ACCESS_DENIED` を利用者向けメッセージへ localize する。

## 見送り

- Settings modal は fork の template reload 操作を維持しつつ、upstream の `Field` primitive ベース UI に追従済み。
- FontAwesome から Lucide への全面置換、theme tokens / UI primitives / prettier 設定の upstream 追従は、2026-06-23 の追加対応で取り込み済み。
- frontend workflow / coverage reporting は infra PR で扱う。

## TDD

### RED

- `AddDataModal.test.tsx`
  - privacy notice と Privacy Policy link を表示すること。
  - `USER_ACCESS_DENIED` のとき Data Registry selector を隠し、Remote Data Registry radio を disabled にすること。
  - `USER_ACCESS_DENIED` のとき Remote Data Connections radio を disabled にすること。
- `NewChatModal.test.tsx` / `RenameChatModal.test.tsx`
  - chat name input に `maxLength=200` が設定されること。
  - 200 文字到達時に warning を表示すること。
- `SettingsModal.test.tsx`
  - `firstName` / `lastName` を connected user として表示すること。
  - 表示名が空の場合 `Connected as` 行を隠すこと。
  - `window.ENV.APP_VERSION` がある場合 version を表示すること。
- `DatasetCardActionBar.test.tsx`
  - description tab では download action を表示し、raw rows tab では隠すこと。

### GREEN

- `app_frontend/src/constants/chat.ts` に `MAX_CHAT_NAME_LENGTH` を追加。
- dataset / datasource hooks に `USER_ACCESS_DENIED` retry 抑止を追加。
- AddDataModal / DataSourceSelector に access denied state と privacy notice を追加。
- SettingsModal に account name fallback と app version 表示を追加。
- DatasetCardActionBar で Raw Rows tab の download action を非表示。

## 検証

- 2026-06-23 dev追従
  - `origin/dev` (`c779f30`) を `codex/v1153-frontend` へmerge。
  - `DatasetResponse` は `api-requests.ts` 内部でのみ使う型のため、`knip` の未使用export検出に合わせて非export化。
  - CI workflow は `npm install` / `npm run lint` / `npm run test` / `npm run knip` のため、npmベースで再検証。
  - `npm install --package-lock=false`: passed
  - `npm run lint && npm run test && npm run knip`: passed。lintは既存warning 6件のみ、Vitestは 134 passed、knipはconfiguration hintsのみ。
  - `npm run build`: passed。
  - `DATAROBOT_API_TOKEN=token DATAROBOT_ENDPOINT=endpoint uv run --all-extras --dev pytest tests/test_main.py tests/test_v1153_backend_compat.py`: 18 passed, 3 skipped。
- 2026-06-23 frontend upstream追加追従
  - Vite Codespaces dev base を upstream `v11.5.3` と同じ `5173` 基準へ戻し、fork独自の static `8080` proxy / `_dr_env.js` dev proxy を削除。
  - `index.html` は local `window.ENV.APP_VERSION = "local"` の inline fallback へ戻し、`_dr_env.js` は build external のみ維持。
  - theme tokens / theme provider / 既存 UI primitives を upstream `v11.5.3` に合わせ、fork独自機能で使う追加 primitive は維持。
  - FontAwesome 依存と import を削除し、既存画面の icon を `lucide-react` へ置換。
  - `axios` manifest を `>=1.13.5 <1.14.0` に更新し、`eslint-plugin-better-tailwindcss` と upstream prettier script 設定を復帰。
  - `Start your first chart here` を `Start your first chat here` に修正し、各 locale の翻訳も更新。
  - upstream Button / Badge variant 変更に合わせ、呼び出し側とテスト期待値を更新。
  - `react-syntax-highlighter` は現行依存に型定義がないため、`vite-env.d.ts` に最小 ambient declaration を追加して build を安定化。
  - `npm install --package-lock=false`: passed。ローカル Node 24 では `i18next-parser` の engine warning と npm audit warning が出る。
  - `npm run prettier && npm run lint && npm run test && npm run knip && npm run build`: passed。lintは既存warning 4件のみ、Vitestは 134 passed、knipはconfiguration hintsのみ、buildは既存chunk size warningのみ。
- 2026-06-23 v11.5.3差分再確認
  - `field.tsx` と `public/assets/datarobot_favicon.png` は upstream `v11.5.3` の asset / UI primitive parity として復帰。
  - `.gitignore` は upstream 同様に `coverage` を ignore し、fork の lockfileなし npm 運用として `package-lock.json` ignore は維持。
  - `getBaseUrl()` は upstream と同じく runtime base 未設定時に `/` を返すように戻し、`getApiUrl()` は `//api` にならないよう path join を補正。notebook static frontend の `APP_BASE_URL` / `API_PORT` / `IS_STATIC_FRONTEND` 対応は維持。
  - SettingsModal は fork 独自の template reload / save footer を維持しつつ、upstream `v11.5.3` にあった DataRobot refresh / API key update / manage API keys link の test id と外部リンクアイコンを復帰。
  - `npm run prettier && npm run lint && npm run test && npm run knip && npm run build`: passed。lintは既存warning 4件のみ、Vitestは 136 passed、knipはconfiguration hintsのみ、buildは既存chunk size warningのみ。
- 2026-06-23 追加UIのupstream primitive追従
  - fork で追加した Settings の template reload セクションを `Field` / `FieldDescription` / `FieldSeparator` ベースに変更。
  - Settings の保存フッターと local pending state を外し、upstream と同じ即時反映の Switch UI に戻した。
  - DataRobot connection 表示は upstream と同じ `firstName` / `lastName` のみを表示名に使い、`username` fallback は表示しない。
  - Settings 周辺 locale は `Dark theme` / `Include BOM in CSV exports` / `Enter API key` など upstream `v11.5.3` のキーへ更新し、追加 template reload キーも各 locale に追加。
  - Template selector の custom prompt loading / update notice は hard-coded blue/gray から `Alert` primitive と theme token に変更。
  - Template list の custom prompt delete action は `destructive` button variant に変更し、開発用 `console.log` を削除。
  - `npm run test -- tests/components/SettingsModal.test.tsx`: 6 passed。
  - `npm run test -- tests/components/SettingsModal.test.tsx tests/components/CustomFeatureEntrypoints.test.tsx`: 8 passed。
  - `npm run prettier && npm run lint && npm run test && npm run knip && npm run build`: passed。lintは既存warning 4件のみ、Vitestは 137 passed、knipはconfiguration hintsのみ、buildは既存chunk size warningのみ。
- `./node_modules/.bin/vitest --run tests/components/AddDataModal.test.tsx tests/components/NewChatModal.test.tsx tests/components/RenameChatModal.test.tsx tests/components/SettingsModal.test.tsx tests/components/DatasetCardActionBar.test.tsx`: 16 passed
- `./node_modules/.bin/tsc -b tsconfig.app.json`: passed
- `./node_modules/.bin/eslint .`: passed with existing warnings only
- `./node_modules/.bin/vitest --run`: 134 passed
- `NODE_OPTIONS='--max-old-space-size=4096' ./node_modules/.bin/vite build`: passed after npmベースで依存を入れ直し。

## 既知事項

- `pnpm --dir app_frontend install --no-lockfile` は pnpm 11 のbuild script承認で `pnpm-workspace.yaml` を生成するため、CI同等確認には使わない。現在のCIは `npm install` を実行する。
- `npm install` はローカルNode 24で `i18next-parser` のengine warningを出す。CI matrixのNode 20/22では該当せず、Node 24 jobもwarning扱いでinstallは成功する。
