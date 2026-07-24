# Dashboard Unexpected Finish KeyError

## 事象

Usage DashboardのUnexpected Finish Trend描画時に、次の例外でStreamlitアプリの
実行が停止し、後続のワードクラウドが表示されなかった。

```text
KeyError: False
```

`filtered["stopUnexpected"] is True` はpandas Seriesの要素比較ではなく、Series
オブジェクト自体と `True` の同一性比較になる。その結果は常に単一の `False` となり、
DataFrameが列名 `False` を参照していた。

## 変更内容

- `Series.eq(True)` で `stopUnexpected` を要素単位に比較し、該当行だけを集計する。
- Streamlit 1.54で非推奨となった `use_container_width=True` を、Plotlyチャートと
  詳細ログテーブルの全9箇所で `width="stretch"` に置き換える。

## テスト

`customize_docs/test_app_usage_dashboard_visualizations.py` で次を確認する。

- `stopUnexpected` のTrue/Falseが混在するデータを日別に正しく集計できる。
- Dashboardに `use_container_width` が残っておらず、9箇所すべてが
  `width="stretch"` を使用する。
