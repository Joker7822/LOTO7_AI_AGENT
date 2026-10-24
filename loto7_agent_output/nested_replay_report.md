# LOTO7 Nested Walk-Forward Comparison

- 評価回数: **120回** (581〜700)
- Research選択: **対象回より前の予測成績だけで選択**
- 現在のResearch Winnerを過去へ後付け: **していない**
- 事前定義モデル: **4個**

| 指標 | Champion reference | Nested Research | Random reference |
|---|---:|---:|---:|
| 平均最大一致 | 2.2583 | 2.2917 | 2.4307 |
| 1口平均一致 | 1.3717 | 1.3933 | 1.3242 |
| 3個以上一致回率 | 33.33% | 34.17% | 43.18% |
| 4個以上一致回率 | 5.00% | 9.17% | 7.53% |
| 平均score | 2.5497 | 2.6193 | 2.7707 |

- Research score差 vs Champion: **+0.0697** (bootstrap 95% CI -0.1052〜+0.2448)
- Research score差 vs Random: **-0.1514** (bootstrap 95% CI -0.3643〜+0.0769)
- Research勝率 vs Champion: **40.8%**
- Research勝率 vs Random: **34.2%**
- 選択モデル回数: adaptive-56ece3c481: 5 / balanced-ac45a2d3fd: 64 / stable-9892a39bad: 51

> nested replayは過去診断専用です。Production昇格は引き続き事前凍結した未来OOSだけで判定します。
