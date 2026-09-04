# LOTO7 Nested Walk-Forward Comparison

- 評価回数: **120回** (574〜693)
- Research選択: **対象回より前の予測成績だけで選択**
- 現在のResearch Winnerを過去へ後付け: **していない**
- 事前定義モデル: **4個**

| 指標 | Champion reference | Nested Research | Random reference |
|---|---:|---:|---:|
| 平均最大一致 | 2.2583 | 2.3333 | 2.4245 |
| 1口平均一致 | 1.3833 | 1.4133 | 1.3201 |
| 3個以上一致回率 | 32.50% | 35.83% | 42.86% |
| 4個以上一致回率 | 5.00% | 10.83% | 7.32% |
| 平均score | 2.5479 | 2.6813 | 2.7614 |

- Research score差 vs Champion: **+0.1334** (bootstrap 95% CI -0.0532〜+0.3225)
- Research score差 vs Random: **-0.0801** (bootstrap 95% CI -0.3045〜+0.1481)
- Research勝率 vs Champion: **44.2%**
- Research勝率 vs Random: **35.8%**
- 選択モデル回数: adaptive-56ece3c481: 5 / balanced-ac45a2d3fd: 71 / stable-9892a39bad: 44

> nested replayは過去診断専用です。Production昇格は引き続き事前凍結した未来OOSだけで判定します。
