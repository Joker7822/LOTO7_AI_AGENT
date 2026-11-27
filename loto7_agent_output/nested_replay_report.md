# LOTO7 Nested Walk-Forward Comparison

- 評価回数: **120回** (586〜705)
- Research選択: **対象回より前の予測成績だけで選択**
- 現在のResearch Winnerを過去へ後付け: **していない**
- 事前定義モデル: **4個**

| 指標 | Champion reference | Nested Research | Random reference |
|---|---:|---:|---:|
| 平均最大一致 | 2.2417 | 2.3000 | 2.4279 |
| 1口平均一致 | 1.3600 | 1.3967 | 1.3223 |
| 3個以上一致回率 | 33.33% | 35.83% | 43.15% |
| 4個以上一致回率 | 5.00% | 9.17% | 7.42% |
| 平均score | 2.5318 | 2.6338 | 2.7668 |

- Research score差 vs Champion: **+0.1020** (bootstrap 95% CI -0.0778〜+0.2781)
- Research score差 vs Random: **-0.1330** (bootstrap 95% CI -0.3585〜+0.0937)
- Research勝率 vs Champion: **44.2%**
- Research勝率 vs Random: **35.8%**
- 選択モデル回数: adaptive-56ece3c481: 5 / balanced-ac45a2d3fd: 59 / stable-9892a39bad: 56

> nested replayは過去診断専用です。Production昇格は引き続き事前凍結した未来OOSだけで判定します。
