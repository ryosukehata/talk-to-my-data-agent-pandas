# ストレージ仕様（ローカル優先・非同期永続化）

対象: レポート保存のインフラ層 `utils/customize/infrastructure/storage/report_storage.py`

## 目的
- 読み込みの体感速度を最大化するため「ローカル優先」を徹底する。
- ローカルの状態を常に正とし、リモート（永続ストレージ）への保存・削除は非同期に行う。
- ローカルになければストレージから取得してローカルを最新化する。

## ポリシー
- 読み込みはローカル優先（存在しなければ取得→ローカルへ反映）
- 書き込み・削除はローカルを原子的に更新後に、非同期でリモートへ反映
- 空データは永続化しない（インデックスが空ならストレージキーを削除）
- 失敗はログ記録し、読み込みの可用性を優先（最終的にローカルが正）

## 実装詳細（関数単位）

- `save(report)` （レポートメタデータの保存）
  - ローカルに原子的に書き込み（JSON）
  - リモート保存を `asyncio.create_task(...)` で非同期スケジュール
  - 行参照: utils/customize/infrastructure/storage/report_storage.py:83, utils/customize/infrastructure/storage/report_storage.py:86

- `get(report_id)` / `_get_once(report_id)` （レポート取得）
  - ローカル優先。ファイル存在・サイズがある場合はローカルを読み込む
  - 無ければストレージから取得してローカルに保存し、その後読み込む
  - 行参照: utils/customize/infrastructure/storage/report_storage.py:120, utils/customize/infrastructure/storage/report_storage.py:130

- `delete(report_id)` （削除）
  - まずローカルのメタデータ・Wordを削除
  - リモート削除を `asyncio.create_task(...)` で非同期スケジュール
  - 行参照: utils/customize/infrastructure/storage/report_storage.py:187, utils/customize/infrastructure/storage/report_storage.py:188

- `save_word_file(report_id, local_path)` （Word保存）
  - ローカルにコピー（壊れていれば入力パスを利用）
  - リモート保存を非同期スケジュール
  - 行参照: utils/customize/infrastructure/storage/report_storage.py:204, utils/customize/infrastructure/storage/report_storage.py:207

- `get_word_file(report_id, local_path)` （Word取得）
  - ローカル優先。ローカルコピーがあればそれを返す
  - 無ければストレージから取得
  - 行参照: utils/customize/infrastructure/storage/report_storage.py:210, utils/customize/infrastructure/storage/report_storage.py:248

- `_get_index()` （インデックス取得）
  - ローカル優先。無ければストレージから取得してローカルに保存
  - 行参照: utils/customize/infrastructure/storage/report_storage.py:241, utils/customize/infrastructure/storage/report_storage.py:248

- `_update_index(report_id, add)` （インデックス更新）
  - 追加時：一時ファイル＋原子的書き込み→非同期でリモート保存→ローカルキャッシュ更新
  - 削除時：空になれば非同期でストレージキー削除、ローカルファイルも削除
  - 空でなければ原子的書き込み→非同期でリモート保存
  - 行参照: utils/customize/infrastructure/storage/report_storage.py:280, utils/customize/infrastructure/storage/report_storage.py:282, utils/customize/infrastructure/storage/report_storage.py:323

## 失敗時の挙動
- リモート保存・削除の失敗はログに記録（非同期タスク内）
- 読み込みはローカルを優先するため、リモート障害でも影響を最小化
- 既知の改善余地：`PersistentStorage.save_to_storage()` の部分失敗ロールバック（次の改修提案に記載）

## データ配置
- ローカルキャッシュディレクトリ: `utils/customize/infrastructure/storage/data/{user_id}`
- ファイル名規則:
  - メタデータ: `{report_id}.json`
  - Word: `{report_id}.docx`
  - インデックス: `report_index.json`

## インデックスの空時ポリシー
- 空配列は永続化しない
- ストレージキー `report_index_{user_id}` を削除、ローカル `report_index.json` も削除
- 行参照: utils/customize/infrastructure/storage/report_storage.py:304

## 注意点
- `PersistentStorage` が利用不可（環境変数未設定など）の場合、`NullPersistentStorage` にフォールバックし、ローカルのみで動作
- 高負荷時の非同期タスクの競合に注意（同じ `report_id` の同時保存は避ける）

