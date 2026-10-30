# Production 5口・35数字完全重複なしポリシー

施行対象：**第702回（2026-11-06）以降に新規発行するProduction予測**。
反映日：2026-10-31 JST。

## 結論
* 1口7数字を5口発行する。**合計35枠はすべて異なる数字**（使用35/37、未使用2）。
* 正規発行元は `weekly_production_prediction.py`、生成・検証元は `production_ticket_geometry35.py` (`production-disjoint35-layout-v1`)。
* 乱数は回番号から固定する。一様シャッフルの券割当であり、既存Championの学習順位で特定の数字を選ぶ運用ではない。数学上の一等確率は改善しない。
* すでに発行・凍結された第701回以前の予測・結果・将来OOSは**変更しない**。過去データの遡及改ざんは禁止する。

## Fail-closed 実装箇所
1. **正規凍結台帳への書込前**：`audit_ledger.append_current_predictions` は第702回以降に `ticket_policy`、モデル方式、5口35数字を検証し、どれか崩れたら5口とも追加しない。
2. **初回の本番発行**：`weekly_production_prediction.publish` は候補CSVの数字配置と凍結後の台帳を検証する。
3. **既存本番の再発行**：正規台帳が第702回以降で重複／不足／古いモデル方式なら拒否し、凍結値を置き換えない。
4. **GitHub Pages表示**：`public_issued_prediction.forecast_group` は第702回以降に不正な5口を公開せず、発行状態の `ticket_policy` も照合する。
5. **さくらDB同期**：`prediction_db_sync.build_payload` は第702回以降の有効予測を対象回ごとにまとめ、5口35数字でない場合はAPIに送らない。
6. **GitHub Actions**：通常発行・fallback・手動再発行のいずれも、commit／DB同期前に `python production_ticket_geometry35.py --verify-canonical` で正規台帳を監査する。

## 発行の前提
* 金曜日13:00–19:59 JSTのみ実行許可（13:00–15:00が標準の発行枠。遅延救済は19:59まで）。
* 前回抽せんの独立2ソース検証、ソースCSVのSHA256整合が必須。
* 既発行の同一対象回は上書き・二重発行しない。
* モデルChampionの更新は別の将来OOS昇格ルールのみ。過去再予測の成績は昇格根拠とならない。

## 自動監査
```bash
python -m pytest -q tests/test_production_ticket_geometry35.py tests/test_public_issued_prediction.py tests/test_prediction_db_sync.py tests/test_weekly_production_schedule.py
python production_ticket_geometry35.py --verify-canonical --out-dir loto7_agent_output
```
第701回が最新発行である間は監査結果 `historical_immutable`。第702回以降は新規本番発行後に `disjoint35_pass` を要求する。次回の本番結果をまだ発行していない段階で「第702回の5口発行済み」とは主張しない。
