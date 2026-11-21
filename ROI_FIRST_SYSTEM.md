# LOTO7 — 回収率優先の全体改修設計

更新：2026年11月22日（日本時間）。第704回（2026年11月20日）までの公表実績による研究評価。

## 結論

**回収率の主指標は「公表払戻金合計 ÷ 同条件の仮想購入費」**。予測順位AIのモデル、35数字を5口に組み分ける本番AI、仮想払戻と実際の発行を区別し、**前回までのデータのみ**を使う研究用ROI選択戦略・費用監査・本番凍結前のセキュリティ検証を連結した。

ただし、**過去の仮想回収率が上がっても、未来の黒字・予測優位性は立証されない**。公正な37数字中7数字の抽せんでは、同一35数字の相互非重複な5分割はすべて同じ事前当せん分布を持つ。過去の高配当4等などの幸運を学習したように見せることを禁止する。

## 本番と研究の境界

1. **確定ソース**：`loto7.csv`、独立2ソースの照合、データのSHA-256が一致する場合だけ新規本番候補を用意する。
2. **予測順位**：発行済みChampionを厳格に使用し、37数字から上位35数字を選択する。
3. **組合せ**：`combination_agent35_core.py` は過去のペア共起を強く縮小して最大18回の口間交換を行い、5口×7数字、35数字の不変を維持する。`production_ticket_geometry35.py` と研究は同一実装を呼ぶ。
4. **本番発行**：`weekly_production_prediction.py` は金曜の正式発行時のみ凍結する。`audit_ledger.append_current_predictions` は決定的な再学習と配置SHA、発行用の回収率ガバナンス設定を独立再計算・検査し、先行発行があれば再発行しない。
5. **回収率研究**：`research/production_combination_round2_replay.py` で第2回から全回を逐次再生。`roi_first_governance.py` が払戻、直近、年別、最大勝ち寄与を計算。`roi_online_selector.py` は直前52回以上の**確定済み**比較結果のみから研究用次戦略を選ぶ。ターゲット回の賞金は選択後にだけ記録。
6. **費用とリスク**：`roi_operational_risk.py` は1回・4回・13回の仮想支出、累積損益と最悪連続損失を表示。将来期待ROIが検証できない場合、購入推奨と購入自動化を禁止。
7. **発行済み予測の別監査**：`research/roi_issued_financial_audit.py` は本番 `predictions.csv` の有効発行予測だけを、`actual_results.csv` と結合。研究で作った仮想予測とは絶対に合算しない。実際に購入した証拠はこのシステムにはない。
8. **統計的な採用判断**：履歴内の払戻差・極端値除外・探索的paired sign-flipは参考値。新しい本番方式の将来収益・当せん優位性を認めるには、**新たに予測凍結した将来OOS結果**と独立の人間レビューが必要。

## 数字の読替え

- 5口×300円＝**1回1,500円**。3,515口＝**1,054,500円**（全703回）。
- **履歴の回収率は仮想購入額に対する公表払戻率**。実際の購入額・個人の回収率ではない。
- 第2〜100回は組合せAIを訓練できない。第101回以降のみ学習済み組合せAIの比較とする。
- 公正抽せんの同一35数字非重複5口の1等確率は **5 / 10,295,472**。順位と組合せを変えるだけでは数学上の確率は増えない。
- チケット発行と購入は異なる。本システムは購入実行しない。

## 再現手順

```bash
python -m pytest -q tests/test_roi_end_to_end.py tests/test_roi_first_governance.py tests/test_production_combination_agent35.py tests/test_production_combination_round2_replay.py
python research/production_combination_round2_replay.py --csv loto7.csv --champion loto7_agent_output/model_champion.json --source-validation loto7_agent_output/source_validation.json --out-dir research/production_combination_round2_replay
python research/roi_issued_financial_audit.py --out-dir loto7_agent_output --report-dir research/roi_issued_output
```

### 保存する証拠

- `summary.json`, `rounds_2_to_latest.csv`, `tickets_2_to_latest.csv` — 再学習・第2回からの予測・口別照合
- `ROI_REPORT.md`, `roi_priority_summary.json` — 純粋な履歴の回収率監査
- `ROI_SHADOW_REPORT.md`, `roi_sequential_shadow.json` — 直前のみでROI方針を選択した仮想検証
- `ROI_RISK_REPORT.md`, `roi_budget_risk.json` — 仮想購入費と最大損失窓
- `issued_production/issued_roi_audit.{json,md}` — 正式に発行された予測に**限定**した別会計

これらの研究証拠から、本番Championや発行済み予測を直接書き換えない。
