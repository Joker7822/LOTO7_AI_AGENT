# Policy Overrides — オペレーター指定採用の分離台帳

この文書は、**統計的な Future OOS 昇格とは別手続き**である
「オペレーター（ユーザー）指定による Production 採用」を、
通常の Champion 昇格と混同されないように分離して記録するためのものです。

## 原則

- Policy Override は統計的優位性の証明ではなく、昇格ゲート
  （未来 OOS 回数、e-value、勝率、平均 score 差）を**通過したことにはなりません**。
- Override の対象・範囲・根拠・未検証である旨は、対象ごとに
  `policy_overrides/` 配下の機械可読レジストリに記録します。
- Override は既発行の凍結予測・Champion 本体・登録済み Future OOS 台帳を
  書き換えません。
- Override で採用した方式の将来成績は、通常昇格とは**別会計**で集計し、
  昇格ゲートの証拠に合算しません。
- Override には見直し条件を必ず付けます。条件到達時に継続可否を再判断し、
  結果をこの台帳に追記します。

## 登録済み Override

| ID | 対象 | 範囲 | 状態 | レジストリ |
|---|---|---|---|---|
| roi-cash-v2-20261122 | production-ai-ranked35-roi-cash-v2 | 第705回以降の未発行 Production の5口配置（数字選択は Champion のまま） | active / 未検証 | policy_overrides/roi_cash_v2.json |

詳細な経緯は ROI_CASH_V2_PRODUCTION_ADOPTION.md を参照してください。
本台帳はその採用を「統計的昇格」へ読み替えるものではありません。
