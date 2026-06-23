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

- upstream の Settings modal 全面 redesign は、この fork の template management / custom prompt 操作と衝突が大きいため見送る。
- FontAwesome から Lucide への全面置換、theme tokens の大規模差分は別 PR とする。
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
- `./node_modules/.bin/vitest --run tests/components/AddDataModal.test.tsx tests/components/NewChatModal.test.tsx tests/components/RenameChatModal.test.tsx tests/components/SettingsModal.test.tsx tests/components/DatasetCardActionBar.test.tsx`: 16 passed
- `./node_modules/.bin/tsc -b tsconfig.app.json`: passed
- `./node_modules/.bin/eslint .`: passed with existing warnings only
- `./node_modules/.bin/vitest --run`: 134 passed
- `NODE_OPTIONS='--max-old-space-size=4096' ./node_modules/.bin/vite build`: passed after npmベースで依存を入れ直し。

## 既知事項

- `pnpm --dir app_frontend install --no-lockfile` は pnpm 11 のbuild script承認で `pnpm-workspace.yaml` を生成するため、CI同等確認には使わない。現在のCIは `npm install` を実行する。
- `npm install` はローカルNode 24で `i18next-parser` のengine warningを出す。CI matrixのNode 20/22では該当せず、Node 24 jobもwarning扱いでinstallは成功する。
