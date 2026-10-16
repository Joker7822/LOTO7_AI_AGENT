# LOTO7 Nested Walk-Forward Comparison

- 評価回数: **120回** (580〜699)
- Research選択: **対象回より前の予測成績だけで選択**
- 現在のResearch Winnerを過去へ後付け: **していない**
- 事前定義モデル: **4個**

| 指標 | Champion reference | Nested Research | Random reference |
|---|---:|---:|---:|
| 平均最大一致 | 2.2583 | 2.3000 | 2.4299 |
| 1口平均一致 | 1.3767 | 1.3983 | 1.3224 |
| 3個以上一致回率 | 33.33% | 34.17% | 43.12% |
| 4個以上一致回率 | 5.00% | 9.17% | 7.47% |
| 平均score | 2.5502 | 2.6282 | 2.7692 |

- Research score差 vs Champion: **+0.0780** (bootstrap 95% CI -0.0953〜+0.2536)
- Research score差 vs Random: **-0.1410** (bootstrap 95% CI -0.3537〜+0.0778)
- Research勝率 vs Champion: **41.7%**
- Research勝率 vs Random: **34.2%**
- 選択モデル回数: adaptive-56ece3c481: 5 / balanced-ac45a2d3fd: 65 / stable-9892a39bad: 50

> nested replayは過去診断専用です。Production昇格は引き続き事前凍結した未来OOSだけで判定します。
