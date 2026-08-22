# LOTO7 Nested Walk-Forward Comparison

- 評価回数: **120回** (572〜691)
- Research選択: **対象回より前の予測成績だけで選択**
- 現在のResearch Winnerを過去へ後付け: **していない**
- 事前定義モデル: **4個**

| 指標 | Champion reference | Nested Research | Random reference |
|---|---:|---:|---:|
| 平均最大一致 | 2.2500 | 2.3083 | 2.4247 |
| 1口平均一致 | 1.3683 | 1.4000 | 1.3185 |
| 3個以上一致回率 | 32.50% | 35.00% | 42.94% |
| 4個以上一致回率 | 5.00% | 10.00% | 7.27% |
| 平均score | 2.5381 | 2.6458 | 2.7614 |

- Research score差 vs Champion: **+0.1077** (bootstrap 95% CI -0.0721〜+0.2907)
- Research score差 vs Random: **-0.1156** (bootstrap 95% CI -0.3357〜+0.1155)
- Research勝率 vs Champion: **43.3%**
- Research勝率 vs Random: **35.0%**
- 選択モデル回数: adaptive-56ece3c481: 5 / balanced-ac45a2d3fd: 73 / stable-9892a39bad: 42

> nested replayは過去診断専用です。Production昇格は引き続き事前凍結した未来OOSだけで判定します。
