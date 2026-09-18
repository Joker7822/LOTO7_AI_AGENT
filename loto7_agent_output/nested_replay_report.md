# LOTO7 Nested Walk-Forward Comparison

- 評価回数: **120回** (576〜695)
- Research選択: **対象回より前の予測成績だけで選択**
- 現在のResearch Winnerを過去へ後付け: **していない**
- 事前定義モデル: **4個**

| 指標 | Champion reference | Nested Research | Random reference |
|---|---:|---:|---:|
| 平均最大一致 | 2.2500 | 2.3250 | 2.4266 |
| 1口平均一致 | 1.3800 | 1.4100 | 1.3220 |
| 3個以上一致回率 | 32.50% | 35.00% | 42.84% |
| 4個以上一致回率 | 5.00% | 10.83% | 7.40% |
| 平均score | 2.5393 | 2.6698 | 2.7642 |

- Research score差 vs Champion: **+0.1305** (bootstrap 95% CI -0.0517〜+0.3218)
- Research score差 vs Random: **-0.0944** (bootstrap 95% CI -0.3163〜+0.1302)
- Research勝率 vs Champion: **44.2%**
- Research勝率 vs Random: **35.0%**
- 選択モデル回数: adaptive-56ece3c481: 5 / balanced-ac45a2d3fd: 69 / stable-9892a39bad: 46

> nested replayは過去診断専用です。Production昇格は引き続き事前凍結した未来OOSだけで判定します。
