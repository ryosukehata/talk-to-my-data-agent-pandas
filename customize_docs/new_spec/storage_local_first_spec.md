# ストレージ仕様（ローカル優先・同期永続化）

対象: レポート保存のインフラ層 `utils/customize/infrastructure/storage/report_storage.py`

## 目的
- 読み込みの体感速度を最大化するため「ローカル優先」を徹底する。
- ローカルを原子的に更新したうえで、リモート（永続ストレージ）への保存・削除完了を待つ。
- ローカルになければストレージから取得してローカルを最新化する。
- 新しいアプリ run でもレポート一覧を復元できるよう、metadata と index は `save()` 完了時点で永続化済みにする。

## ポリシー
- 読み込みはローカル優先（存在しなければ取得→ローカルへ反映）
- 書き込み・削除はローカルを原子的に更新後に、リモート反映完了まで待つ
- 空データは永続化しない（インデックスが空ならストレージキーを削除）
- リモート保存失敗は呼び出し元へ伝播し、成功扱いでデータ欠落しないようにする

## 実装詳細（関数単位）

- `save(report)` （レポートメタデータの保存）
  - ローカルに原子的に書き込み（JSON）
  - リモート保存完了まで `await` する
  - 行参照: utils/customize/infrastructure/storage/report_storage.py:83, utils/customize/infrastructure/storage/report_storage.py:86

- `get(report_id)` / `_get_once(report_id)` （レポート取得）
  - ローカル優先。ファイル存在・サイズがある場合はローカルを読み込む
  - 無ければストレージから取得してローカルに保存し、その後読み込む
  - 行参照: utils/customize/infrastructure/storage/report_storage.py:120, utils/customize/infrastructure/storage/report_storage.py:130

- `delete(report_id)` （削除）
  - まずローカルのメタデータ・Wordを削除
  - リモート削除完了まで `await` する
  - 行参照: utils/customize/infrastructure/storage/report_storage.py:187, utils/customize/infrastructure/storage/report_storage.py:188

- `save_word_file(report_id, local_path)` （Word保存）
  - ローカルにコピー（壊れていれば入力パスを利用）
  - リモート保存完了まで `await` する
  - 行参照: utils/customize/infrastructure/storage/report_storage.py:204, utils/customize/infrastructure/storage/report_storage.py:207

- `get_word_file(report_id, local_path)` （Word取得）
  - ローカル優先。ローカルコピーがあればそれを返す
  - 無ければストレージから取得
  - 行参照: utils/customize/infrastructure/storage/report_storage.py:210, utils/customize/infrastructure/storage/report_storage.py:248

- `_get_index()` （インデックス取得）
  - ローカル優先。無ければストレージから取得してローカルに保存
  - 行参照: utils/customize/infrastructure/storage/report_storage.py:241, utils/customize/infrastructure/storage/report_storage.py:248

- `_update_index(report_id, add)` （インデックス更新）
  - 追加時：ローカル index を原子的に書き込み→リモート保存完了まで `await`
  - 削除時：空になればストレージキー削除完了まで `await` し、ローカルファイルも削除
  - 空でなければ原子的書き込み→リモート保存完了まで `await`
  - 行参照: utils/customize/infrastructure/storage/report_storage.py:280, utils/customize/infrastructure/storage/report_storage.py:282, utils/customize/infrastructure/storage/report_storage.py:323

## 失敗時の挙動
- リモート保存・削除の失敗は呼び出し元へ伝播する。
- 読み込みは引き続きローカルを優先するため、同一 run 内の体感速度は維持する。
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
- 同じ `report_id` の同時保存は避ける。

## 2026-06-30 修正メモ

- 旧実装では `asyncio.create_task(...)` で metadata / index / Word 保存を投げっぱなしにしていた。
- 特に index 更新では、一時ファイルを非同期 task に渡した直後に削除していたため、PersistentStorage へ `report_index_{user_id}` が保存されないことがあった。
- 新しい run ではローカルキャッシュが空のため、index が永続化されていないと metadata が残っていても一覧に出ない。
- `ReportStorage.save()` / `_update_index()` / `save_word_file()` / `delete()` は、永続化または削除が完了するまで `await` する。
