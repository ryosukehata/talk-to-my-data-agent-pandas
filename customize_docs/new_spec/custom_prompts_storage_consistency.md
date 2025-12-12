# custom_prompts と 永続ストレージ保存の不整合と改善方針

対象: `utils/customize/custom_prompts.py`（ユーザーカスタムプロンプト保存）とストレージ層（`utils/customize/cache.py` / `utils/persistent_storage.py`）の保存動作の差異による不安定性。

## 課題
- 非同期コンテキストで保存がスキップされる
  - `PersistentCache.save_from_file()` はイベントループ稼働時（FastAPI の `async` ハンドラ内など）に警告を出して早期 return する設計。結果として永続ストレージへのアップロードが行われず、保存が不安定化するケースがある。
- 空配列の扱い不一致（初期/削除時の永続化）
  - 読み込み側 `get_or_load_json()` は「空リストは永続化しない」方針（`persist_when` により空は非永続化）だが、削除側 `delete_prompt()` は空になった後でもローカルに書き込み、`save_from_file()` 経由で空 JSON を永続化する。初期状態ではファイルが存在しないのに、削除後は空ファイルが存在するという整合性の不一致が起きる。
- 環境変数未設定時のサイレントフォールバック
  - `PersistentStorage` は `APPLICATION_ID` 未設定で例外→`custom_prompts` 側は `NullPersistentStorage` にフォールバックし、ローカル書き込みのみで「保存成功」ログが出る。利用者からは成功に見えるが実際は永続化されない。
- ストレージ更新の部分的失敗時のリーク可能性
  - `save_to_storage()` は「アップロード→KeyValue更新→旧ファイル削除」の順。KeyValue 更新が失敗すると、新・旧どちらかのファイルがリークする可能性があり、復旧ロジックがない。
- タイムスタンプ比較の競合可能性（同時保存/分散時計）
  - 新旧判定に `time.time_ns()` の比較を使用。連続呼び出しや分散環境の時計差で稀に逆転する可能性がある（極低頻度だがゼロではない）。
- ローカルファイルの相対配置依存
  - `user_prompt_{user_id}.json` を CWD に生成するため、作業ディレクトリ・権限に依存。マルチプロセスや異なる起動環境で書き込み失敗や衝突のリスクが増す。

## 解決方針
- 非同期保存の扱いを統一
  - API 層（FastAPI）の `async` コンテキストからは `await PersistentCache._save_from_file_async()` を呼ぶ、または `save_from_file()` を「イベントループ稼働時は `asyncio.create_task(...)` でスケジュール」するように修正して、早期 return をやめる。
  - `UserPrompts` に `async def save_prompt_async()` / `async def delete_prompt_async()` を追加し、エンドポイントからは非同期版を使用する。
- 空は保存しないポリシーに統一
  - `delete_prompt()` 後に空になった場合は、ローカルファイルを消し、`PersistentStorage.delete_file(key)` を呼んでストレージのリンクとファイルを削除する。空 JSON の永続化は行わないよう統一する。
  - 代替として、保存系で `persist_when` 相当の判定（空なら保存しない）を適用し、空のときは `save_from_file()` を呼ばない。
- フォールバックの可視化とヘルスチェック
  - `NullPersistentStorage` へフォールバック時は警告ログを強化し、API レスポンスや UI に「永続化無効」状態を明示する。
  - アプリ起動時に必須環境変数（`APPLICATION_ID`, `DATAROBOT_ENDPOINT`, `DATAROBOT_API_TOKEN`）を検証し、失敗時は起動を止める（fail fast）または機能フラグで永続化の有効/無効を露出する。
- 更新失敗時のロールバック/ガーベジコレクション
  - `save_to_storage()` に例外ハンドリングを追加し、KeyValue 更新失敗時は新規アップロードファイルを削除してロールバック。旧ファイル削除失敗時はリトライまたは定期 GC ジョブ（既存の `resources/job_cleanup` を活用）を設定。
- 単調増加バージョンの導入
  - `time.time_ns()` 依存から、単調増加のバージョン（`monotonic_ns()` や連番）へ切り替え。KeyValue の `comment` フィールドにバージョンを保持してオプティミスティックロック（保存前に最新バージョンを再確認）を行う。
- ローカルキャッシュディレクトリの固定化
  - `utils/customize/cache` 配下でアプリ用のキャッシュディレクトリ（例：`./.cache/prompts/`）を管理し、そこで原子的に書き換え。CWD 依存を排除し、権限設定やクリーンアップポリシーを明示する。

## 実装観点（補足）
- `custom_prompts` は「ローカル→ストレージ」の二段保存。ローカルは `atomic_write_json()` により安全だが、ストレージは非同期・外部 I/O 依存のため、API ハンドラのライフサイクルに合わせた非同期化が必須。
- KeyValue の JSON には `catalogId` と `timestamp` を保持している。更新の整合性を高めるため、バージョンと更新者（user_id）も付加することを推奨。
- 初期ロードの `persist_when`（空は非永続化）と削除時の動作を一致させることで、状態の直感的一貫性を担保できる。

