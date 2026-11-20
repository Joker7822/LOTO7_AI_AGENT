# LOTO7 Nested Walk-Forward Comparison

- 評価回数: **120回** (585〜704)
- Research選択: **対象回より前の予測成績だけで選択**
- 現在のResearch Winnerを過去へ後付け: **していない**
- 事前定義モデル: **4個**

| 指標 | Champion reference | Nested Research | Random reference |
|---|---:|---:|---:|
| 平均最大一致 | 2.2500 | 2.2917 | 2.4307 |
| 1口平均一致 | 1.3617 | 1.3933 | 1.3232 |
| 3個以上一致回率 | 33.33% | 35.00% | 43.39% |
| 4個以上一致回率 | 5.00% | 9.17% | 7.45% |
| 平均score | 2.5403 | 2.6222 | 2.7708 |

- Research score差 vs Champion: **+0.0819** (bootstrap 95% CI -0.1008〜+0.2547)
- Research score差 vs Random: **-0.1485** (bootstrap 95% CI -0.3700〜+0.0789)
- Research勝率 vs Champion: **43.3%**
- Research勝率 vs Random: **35.0%**
- 選択モデル回数: adaptive-56ece3c481: 5 / balanced-ac45a2d3fd: 60 / stable-9892a39bad: 55

> nested replayは過去診断専用です。Production昇格は引き続き事前凍結した未来OOSだけで判定します。
