# LOTO7 Nested Walk-Forward Comparison

- 評価回数: **120回** (579〜698)
- Research選択: **対象回より前の予測成績だけで選択**
- 現在のResearch Winnerを過去へ後付け: **していない**
- 事前定義モデル: **4個**

| 指標 | Champion reference | Nested Research | Random reference |
|---|---:|---:|---:|
| 平均最大一致 | 2.2583 | 2.3000 | 2.4286 |
| 1口平均一致 | 1.3800 | 1.4000 | 1.3218 |
| 3個以上一致回率 | 33.33% | 34.17% | 43.02% |
| 4個以上一致回率 | 5.00% | 9.17% | 7.40% |
| 平均score | 2.5505 | 2.6283 | 2.7669 |

- Research score差 vs Champion: **+0.0778** (bootstrap 95% CI -0.1032〜+0.2508)
- Research score差 vs Random: **-0.1385** (bootstrap 95% CI -0.3602〜+0.0829)
- Research勝率 vs Champion: **41.7%**
- Research勝率 vs Random: **34.2%**
- 選択モデル回数: adaptive-56ece3c481: 5 / balanced-ac45a2d3fd: 66 / stable-9892a39bad: 49

> nested replayは過去診断専用です。Production昇格は引き続き事前凍結した未来OOSだけで判定します。
