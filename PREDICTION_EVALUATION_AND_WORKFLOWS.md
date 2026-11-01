# 分離指標・運用簡素化（2026-11-01）

## 変更の狙い

モデルの予測能力を過去の一致数だけで評価しない。Production、Champion、事前凍結の将来OOS、当せん結果、研究試行予算は一切変更せず、読み取り専用の比較スナップショットを構築する。

## 指標の分離

| 区分 | 入力（既存の成果物） | 表示 | 主張しないこと |
|---|---|---|---|
| 過去の一致数 | historical_replay_summary.json | Top7平均・一様理論平均との差 | 将来の的中率向上 |
| ランダム対照 | historical_replay_summary.json | 同条件の5口ランダム比較・最大一致数差・スコア差 | 厳密な将来OOS |
| 確率予測 | champion_calibration_oos_state.json | 事前凍結未来log-score改善・Brier改善／trusted回数 | ECEやProduction昇格 |
| 参考払戻 | historical_reconciliation_summary.json | 参考購入額・払戻額・回収率 | 実購入・実現損益・将来利益 |
| 将来OOSの境界 | future_holdout_evidence.json | 進捗・事前登録の時期・確認状態 | 過去検証と将来検証の合算 |

**単位の違う数値を加算しません。** 異なるモデル・期間の数値を混同しません。欠損は0扱いせず未確認、SHA・件数・照合結果が整合しない参考配当は証拠不整合です。

- スクリプト： python evaluation_scorecard.py --out-dir loto7_agent_output --format markdown
- JSON形式： python evaluation_scorecard.py --out-dir loto7_agent_output --format json
- ダッシュボード： dashboard_status_snapshot.py が同じ関数を呼び、prediction_metricsを公開JSONに追加します。元の集計のSHA256はprovenanceで保持します。
- ECEとreliability curveは個別37数字の事前固定確率と結果の組が必要です。集計済みの平均log/Brierから再構築しません。

## GitHub Actionsの負荷と依存関係

2026-11-01時点で49個のworkflowファイルがあり、本番発行、二ソース照合、研究と監査、ダッシュボード公開が混在しています。

- 変更前：Browser Ops Snapshotは4回/時の定期起動に加え、7つのproducer完了に反応していました。
- 変更後：2回/時（UTC毎時13分・43分）と、「LOTO7 Independent Result Corroboration」「Weekly Production Publisher」完了に反応します。
- 研究状態の表示は30分程度遅延する場合があります。照合済み抽せんと本番公開は即時更新の入口を維持します。
- 定期・完了通知ジョブはフルテストを毎回実行せず、PR、push、手動実行で実施します。
- python workflow_inventory.py は全workflowのcron、workflow_run参照、git push・write宣言を棚卸しします。
- 既存のconcurrency制限とmain再取得・再試行を維持します。予測台帳はコミットしません。

**残る制約**：GitHub Pagesの内蔵ブランチデプロイはmainの更新頻度に依存します。今回はダッシュボード由来の更新を削減しますが、他の研究ジョブによるmain更新でのデプロイ競合は残り得ます。完全解消にはPagesのデプロイ方式変更や研究成果物のブランチ分離を別途評価する必要があります。今回ProductionやPagesの公開方式を変更しません。

## 確認手順

    python -m pytest -q tests/test_evaluation_scorecard.py tests/test_workflow_inventory.py tests/test_dashboard_status_snapshot.py
    node --test docs/tests/*.test.mjs
    python workflow_inventory.py --format markdown
    python evaluation_scorecard.py --format markdown

すべての新規コードは標準ライブラリのみです。継続研究、Production、将来OOSの制御面には書込み処理を追加していません。
