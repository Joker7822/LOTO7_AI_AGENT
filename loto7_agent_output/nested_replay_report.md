# LOTO7 Nested Walk-Forward Comparison

- 評価回数: **120回** (575〜694)
- Research選択: **対象回より前の予測成績だけで選択**
- 現在のResearch Winnerを過去へ後付け: **していない**
- 事前定義モデル: **4個**

| 指標 | Champion reference | Nested Research | Random reference |
|---|---:|---:|---:|
| 平均最大一致 | 2.2500 | 2.3333 | 2.4258 |
| 1口平均一致 | 1.3800 | 1.4117 | 1.3213 |
| 3個以上一致回率 | 32.50% | 35.83% | 42.86% |
| 4個以上一致回率 | 5.00% | 10.83% | 7.40% |
| 平均score | 2.5393 | 2.6812 | 2.7634 |

- Research score差 vs Champion: **+0.1419** (bootstrap 95% CI -0.0443〜+0.3218)
- Research score差 vs Random: **-0.0822** (bootstrap 95% CI -0.3031〜+0.1572)
- Research勝率 vs Champion: **45.0%**
- Research勝率 vs Random: **35.8%**
- 選択モデル回数: adaptive-56ece3c481: 5 / balanced-ac45a2d3fd: 70 / stable-9892a39bad: 45

> nested replayは過去診断専用です。Production昇格は引き続き事前凍結した未来OOSだけで判定します。
