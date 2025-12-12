# Report Storage: ユーザーIDが `anonymous` になる問題

## 背景

レポート保存処理では `ReportStorage` にユーザーIDを渡して DataRobot Catalog/PersistentStorage 上の
ユーザー別領域へメタデータ・Wordファイルを格納する。ところが実際のAPI呼び出しではユーザーIDが
常に `anonymous` として保存され、異なるユーザーのデータが同一領域に混在する恐れがあった。

## 原因

`utils/customize/api_endpoints/report.py` の `get_user_id` が `x-user-id` または `x-user-email`
ヘッダーのみを参照し、それ以外の経路で付与されたユーザー情報を無視していた。

本番相当のリクエストでは `request.state.session.datarobot_account_info` に `uid` や `email`
が格納されるため、ヘッダーに `x-user-id` を持たないケースでは `anonymous` が返却されていた。

## 課題

- セッション経由のユーザー情報も解決して正しい `uid` を返す必要がある。
- 既存の `ReportStorage` ディレクトリ構造はユーザーIDをディレクトリ名に使うため、
  `anonymous` で保存された既存レポートの整理／移行方針を検討する必要がある。
- 将来の拡張に備え、ユーザー識別子の取得優先順位を仕様化し、回帰テストを追加する必要がある。

## 対応チェックリスト

- [x] `get_user_id` で `request.state.session.datarobot_account_info.uid` を優先的に参照する
- [ ] `request.state.session` を利用できない環境向けに `x-user-email` ヘッダー → 名前空間UUID のフォールバック可否を再検討
- [ ] 既存に `anonymous` 保存されたレポートをユーザー別に再配置する計画を策定
- [ ] セッション情報が欠落している場合のロギング／警告を追加
- [ ] ユーザーID解決ロジックのユニットテストを追加
