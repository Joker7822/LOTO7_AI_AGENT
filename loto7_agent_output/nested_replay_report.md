# LOTO7 Nested Walk-Forward Comparison

- 評価回数: **120回** (577〜696)
- Research選択: **対象回より前の予測成績だけで選択**
- 現在のResearch Winnerを過去へ後付け: **していない**
- 事前定義モデル: **4個**

| 指標 | Champion reference | Nested Research | Random reference |
|---|---:|---:|---:|
| 平均最大一致 | 2.2500 | 2.3167 | 2.4271 |
| 1口平均一致 | 1.3800 | 1.4100 | 1.3226 |
| 3個以上一致回率 | 32.50% | 35.00% | 42.86% |
| 4個以上一致回率 | 5.00% | 10.00% | 7.37% |
| 平均score | 2.5393 | 2.6552 | 2.7646 |

- Research score差 vs Champion: **+0.1159** (bootstrap 95% CI -0.0656〜+0.2978)
- Research score差 vs Random: **-0.1095** (bootstrap 95% CI -0.3299〜+0.1194)
- Research勝率 vs Champion: **43.3%**
- Research勝率 vs Random: **35.0%**
- 選択モデル回数: adaptive-56ece3c481: 5 / balanced-ac45a2d3fd: 68 / stable-9892a39bad: 47

> nested replayは過去診断専用です。Production昇格は引き続き事前凍結した未来OOSだけで判定します。
