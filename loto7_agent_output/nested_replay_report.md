# LOTO7 Nested Walk-Forward Comparison

- 評価回数: **120回** (582〜701)
- Research選択: **対象回より前の予測成績だけで選択**
- 現在のResearch Winnerを過去へ後付け: **していない**
- 事前定義モデル: **4個**

| 指標 | Champion reference | Nested Research | Random reference |
|---|---:|---:|---:|
| 平均最大一致 | 2.2583 | 2.3000 | 2.4299 |
| 1口平均一致 | 1.3750 | 1.3983 | 1.3237 |
| 3個以上一致回率 | 33.33% | 35.00% | 43.23% |
| 4個以上一致回率 | 5.00% | 9.17% | 7.42% |
| 平均score | 2.5500 | 2.6311 | 2.7693 |

- Research score差 vs Champion: **+0.0811** (bootstrap 95% CI -0.0993〜+0.2603)
- Research score差 vs Random: **-0.1382** (bootstrap 95% CI -0.3635〜+0.0893)
- Research勝率 vs Champion: **41.7%**
- Research勝率 vs Random: **35.0%**
- 選択モデル回数: adaptive-56ece3c481: 5 / balanced-ac45a2d3fd: 63 / stable-9892a39bad: 52

> nested replayは過去診断専用です。Production昇格は引き続き事前凍結した未来OOSだけで判定します。
