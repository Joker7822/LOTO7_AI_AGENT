# LOTO7 AI Agent Status

- 更新日時 (JST): **2026-08-29T02:03:12+09:00**
- 最新取得回: **第692回 / 2026-08-28**
- 最新予測対象: **第693回**
- 未照合予測: **5口**
- モデル: **baseline-5fdb8dc2ad**
- データSHA256: `12e55f5d26e25b243d0ad754ce4886fed189ae1bc89901d367d8f6aa89ea7403`
- ソース検証: **verified_two_result_sources**
- 取得状態: **ok**

> `degraded_single_result_source` の場合、楽天の結果は取得済みですが、みずほ銀行側の同一回結果を機械解析できていません。不一致が検出された場合は処理を停止します。

## Continuous Research v4

- 研究世代: **2688**
- Production Champion: **baseline-5fdb8dc2ad**
- 最新Research Winner: **signal-g02253-c01-b6030e66c9**
- 候補プール: **17モデル**
- 累積研究評価数: **18815**
- 過去データの研究スコアから本番昇格: **無効（禁止）**
- 現在ソース検証: **verified_two_result_sources**
- 本番昇格に利用可能なソース: **YES**

## Research Signal / Portfolio Separation

- Research Parent: **signal-g02253-c01-b6030e66c9**
- 全期間 Top7 edge vs uniform: **+0.0169**
- 全期間 actual-mass edge vs uniform: **+0.001278**
- 全期間 log edge vs uniform: **-0.016789**
- 全期間 Brier edge vs uniform: **-0.001207**
- 直近120回 log edge vs uniform: **-0.014902**
- Portfolio feedback objective: **-0.1203**
- Signal objective: **-0.0427**
- Research採用: **Portfolio改善だけでは不可。Signal非劣化ゲートも必須**

## Historical Replay Accuracy

- 評価回数: **592回** (101〜692)
- Top7平均本数字一致: **1.3716** / random **1.3243**
- Top7近似両側p: **0.223775** / 判定 **not_confirmed**
- 5口平均最大一致: **2.2500** / random **2.4257**
- 5口平均score差 vs random: **-0.1911**
- 3個以上一致券あり: **36.7%** / random **42.9%**
- 4個以上一致券あり: **7.3%** / random **6.8%**
- 何らかの等級当選があった回: **16.39%**
- 用途: **過去回の精度確認専用。v4 Champion昇格の未来OOS証拠には使用しない**

## Historical Reconciliation

- 独立再照合: **592回 / 2960口**
- 当選口数: **123口** (4.155%)
- 参考購入額: **888,000円**
- 公表当選額ベース参考払戻: **172,000円**
- 参考回収率: **19.37%**
- 予測側実績とloto7.csvの不一致: **0件**

## Nested Champion / Research / Random

- Nested評価回数: **120回** (573〜692)
- 平均score Champion / Research / Random: **2.5474 / 2.6663 / 2.7602**
- Research差 vs Champion: **+0.1188** (95% CI -0.0675〜+0.3063)
- Research差 vs Random: **-0.0940** (95% CI -0.3108〜+0.1437)
- Research勝率 vs Champion / Random: **44.2% / 35.8%**
- 選択方法: **各対象回より前の成績のみで事前定義モデルから選択**

## Formal Challenger

- Formal Challenger: **global-g00001-c01-2ac3662ad1**
- block id: **36d2ec03cdf5da70**
- block開始対象回: **第692回**
- trusted Future OOS: **1/8回**
- 現在の凍結対象回: **第693回**
- Promotion候補数: **1**
- ポリシー: **同一Challengerを8 trusted drawsまで固定。他shadowはResearch-only**

## OOS Governance v4

- 凍結済みshadow対象回: **第693回**
- Promotion対象shadow候補数: **1**
- 最終OOS採点回: **692**
- 累積Champion昇格数: **0**
- 昇格条件: **信頼済み未来OOS 8回以上 / e-value ≥ 20 / 平均score差 ≥ 0.05 / 勝率 ≥ 55%**
- 現Championに対するFormal OOS候補: **global-g00001-c01-2ac3662ad1**
- 信頼済みOOS回数: **1**
- e-value: **1.0000**
- 平均score差: **0.0000**
- OOS勝率: **0.0%**

## Continuous Runtime

- 最新1回の研究実行時間: **100秒**
- 直近20回平均: **99.2秒**
- 累積実測回数: **3568回**
- 実行方式: **終了後、待ち時間なしで次の研究世代へ**
- Git checkpoint: **10世代ごと、または重要イベント発生時**
