# Infrastructure Storage 改善方針（コードレベル）

対象: `utils/customize/infrastructure/storage/report_storage.py` と基盤層 `utils/customize/cache.py` / `utils/persistent_storage.py`

## 目的
- 保存の不安定性（非同期文脈・空データの取り扱い・部分失敗）を解消し、`custom_prompts` と同様の整合的なポリシー（空は保存しない、原子的書き込み、明確なロールバック）に揃える。

## 実装変更の要点（ReportStorage）
- インデックス削除時の空永続化禁止
  - ファイル参照: utils/customize/infrastructure/storage/report_storage.py:271
  - 変更: レポート削除でインデックスが空になった場合、`save_to_storage` による空JSONの永続化を行わず、`delete_file(self._index_key())` を呼び出し、ローカルキャッシュも削除。
  - 理由: `PersistentCache.get_or_load_json()` のポリシー（空は非永続化）と整合させ、初期状態と削除後状態の一貫性を保つ。

- 原子性の維持と一時ファイル利用（追記時）
  - ファイル参照: utils/customize/infrastructure/storage/report_storage.py:254
  - 仕様: 追記時は `tempfile.NamedTemporaryFile` と `atomic_write_json` を利用して差分保存→`save_to_storage`。例外時は確実に一時ファイルを削除する（現実装踏襲）。

- 取得の堅牢性（リトライ）
  - ファイル参照: utils/customize/infrastructure/storage/report_storage.py:99
  - 仕様: 1〜2秒のバックオフ付き最大 `max_retries` 回のリトライを実装済み。I/O一時障害に耐性。

## 実装変更の要点（PersistentCache）
- 非同期API文脈での保存スキップ回避
  - ファイル参照: utils/customize/cache.py:68, utils/customize/cache.py:109
  - 現状: イベントループ稼働時は警告を出して早期 `return`。
  - 方針: API側からは `await _save_from_file_async()` / `await _fetch_to_file_async()` を直接利用し、同期ラッパを避ける。同期ラッパを使う場合は `asyncio.create_task(...)` によるスケジュール化で早期 `return` をやめる（別PR）。

- 空データの永続化禁止の徹底
  - ファイル参照: utils/customize/cache.py:142
  - 現状: `persist_when` により空時は保存しない設計。
  - 方針: 呼び出し側（ReportStorage, custom_prompts）でも空時に `save_from_file` を呼ばない明示ロジックを維持し、削除時は `delete_file(key)` を用いる。

## 実装変更の要点（PersistentStorage）
- 更新時の部分失敗への対処（ロールバック）
  - ファイル参照: utils/persistent_storage.py:220, utils/persistent_storage.py:234
  - 現状: アップロード→KeyValue更新→旧ファイル削除。KeyValue更新失敗時のロールバックは未実装。
  - 方針: 例外時に新規アップロードファイルを削除するロールバック、旧ファイル削除失敗時は警告ログとGCジョブ（`resources/job_cleanup`）で回収（次PRで対応）。

- 競合対策（バージョン）
  - ファイル参照: utils/persistent_storage.py:220
  - 現状: `time.time_ns()` 比較。
  - 方針: `time.monotonic_ns()` または保存回数の連番に切替。KeyValue `comment` にバージョンを保持してオプティミスティックロックを検討（次PR）。

## 具体的変更の差分
- 変更済み
  - utils/customize/infrastructure/storage/report_storage.py:271 以降
    - インデックスが空になった場合にストレージキーとローカルファイルを削除するように修正。

- 追加提案（次の改修）
  - `custom_prompts.UserPrompts` に `async` 版メソッド追加し、APIからは `await` で呼び出す。
  - `PersistentCache.save_from_file()` の「イベントループ稼働時はreturn」を `create_task` に変更。
  - `PersistentStorage.save_to_storage()` に try/except を追加し KeyValue更新失敗時に `delete_file(catalogId)` ロールバック。

## テスト観点
- 削除時のインデックス空化動作
  - 前提: インデックスに1件のみ。
  - 手順: `delete(report_id)` 実行。
  - 検証: ストレージの `report_index_{user_id}` が存在しない、ローカル `report_index.json` が削除される。

- 追加保存時の追記動作
  - 手順: `save(report)` を2件分。
  - 検証: インデックスに2件、`save_to_storage` 呼び出し回数が増える、内容整合。

- 非同期文脈での保存
  - 前提: FastAPIエンドポイントから呼び出し。
  - 検証: `save_word_file` / `save` が await で動作し、保存スキップが発生しない。
