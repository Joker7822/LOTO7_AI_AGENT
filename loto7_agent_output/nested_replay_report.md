# LOTO7 Nested Walk-Forward Comparison

- 評価回数: **120回** (578〜697)
- Research選択: **対象回より前の予測成績だけで選択**
- 現在のResearch Winnerを過去へ後付け: **していない**
- 事前定義モデル: **4個**

| 指標 | Champion reference | Nested Research | Random reference |
|---|---:|---:|---:|
| 平均最大一致 | 2.2500 | 2.3167 | 2.4284 |
| 1口平均一致 | 1.3800 | 1.4033 | 1.3230 |
| 3個以上一致回率 | 32.50% | 35.00% | 42.94% |
| 4個以上一致回率 | 5.00% | 10.00% | 7.42% |
| 平均score | 2.5393 | 2.6545 | 2.7667 |

- Research score差 vs Champion: **+0.1153** (bootstrap 95% CI -0.0673〜+0.3003)
- Research score差 vs Random: **-0.1122** (bootstrap 95% CI -0.3306〜+0.1141)
- Research勝率 vs Champion: **42.5%**
- Research勝率 vs Random: **35.0%**
- 選択モデル回数: adaptive-56ece3c481: 5 / balanced-ac45a2d3fd: 67 / stable-9892a39bad: 48

> nested replayは過去診断専用です。Production昇格は引き続き事前凍結した未来OOSだけで判定します。
