# LOTO7 AI Agent Status

- 更新日時 (JST): **2026-09-19T19:20:33+09:00**
- 最新取得回: **第695回 / 2026-09-18**
- 最新Production対象: **第696回（未発行）**
- 未照合予測: **0口**
- モデル: **baseline-5fdb8dc2ad**
- データSHA256: `aa1a6f4e0f443e78be4e68fa79fbbb24f0df862d47726b9afeaef13b8f0d9fcb`
- ソース検証: **verified_two_result_sources**
- 取得状態: **ok**

> Productionの凍結は金曜15:00 JST publisherのみが行います。通常checkpointは既存の凍結台帳を照合・表示するだけです。

## Continuous Research v4

- 研究世代: **3802**
- Production Champion: **baseline-5fdb8dc2ad**
- 最新Research Winner: **signal-g02253-c01-b6030e66c9**
- 候補プール: **17モデル**
- 累積研究評価数: **26613**
- 過去データの研究スコアから本番昇格: **無効（禁止）**
- 現在ソース検証: **verified_two_result_sources**
- 本番昇格に利用可能なソース: **YES**

## Research Signal / Portfolio Separation

- Research Parent: **signal-g02253-c01-b6030e66c9**
- 全期間 Top7 edge vs uniform: **+0.0185**
- 全期間 actual-mass edge vs uniform: **+0.001361**
- 全期間 log edge vs uniform: **-0.016593**
- 全期間 Brier edge vs uniform: **-0.001188**
- 直近120回 log edge vs uniform: **-0.013802**
- Portfolio feedback objective: **-0.1142**
- Signal objective: **-0.0417**
- Research採用: **Portfolio改善だけでは不可。Signal非劣化ゲートも必須**

## Historical Replay Accuracy

- 評価回数: **595回** (101〜695)
- Top7平均本数字一致: **1.3714** / random **1.3243**
- Top7近似両側p: **0.224498** / 判定 **not_confirmed**
- 5口平均最大一致: **2.2504** / random **2.4254**
- 5口平均score差 vs random: **-0.1900**
- 3個以上一致券あり: **36.8%** / random **42.9%**
- 4個以上一致券あり: **7.2%** / random **6.8%**
- 何らかの等級当選があった回: **16.47%**
- 用途: **過去回の精度確認専用。v4 Champion昇格の未来OOS証拠には使用しない**

## Historical Reconciliation

- 独立再照合: **595回 / 2975口**
- 当選口数: **124口** (4.168%)
- 参考購入額: **892,500円**
- 公表当選額ベース参考払戻: **172,900円**
- 参考回収率: **19.37%**
- 予測側実績とloto7.csvの不一致: **0件**

## Nested Champion / Research / Random

- Nested評価回数: **120回** (576〜695)
- 平均score Champion / Research / Random: **2.5393 / 2.6698 / 2.7642**
- Research差 vs Champion: **+0.1305** (95% CI -0.0517〜+0.3218)
- Research差 vs Random: **-0.0944** (95% CI -0.3163〜+0.1302)
- Research勝率 vs Champion / Random: **44.2% / 35.0%**
- 選択方法: **各対象回より前の成績のみで事前定義モデルから選択**

## Formal Challenger

- Formal Challenger: **global-g00001-c01-2ac3662ad1**
- block id: **36d2ec03cdf5da70**
- strict block index: **1**
- block開始対象回: **第692回**
- trusted Future OOS: **3/8回**
- family weight: **0.50000000**
- 必要raw e-value: **40.00**
- 現在の凍結対象回: **第696回**
- Promotion候補数: **1**
- ポリシー: **同一Challengerを8 trusted drawsまで固定し、Champion・事前凍結Random・32-member geometry-matched permutation ensembleの全てに勝つことを要求**

## Strict Future OOS Governance

- ガバナンス版: **strict-oos-governance-v1**
- Matched null版: **matched-permutation-null-v1**
- 凍結済みshadow対象回: **第696回**
- Promotion対象shadow候補数: **1**
- 最終OOS採点回: **695**
- 累積Champion昇格数: **0**
- Uniform Random凍結: **YES** / Matched凍結: **YES**
- strict昇格条件: **8 paired trusted draws / adjusted e-value ≥ 20 / 平均score差 ≥ +0.05 / 勝率 ≥ 55% をChampion・Random・Matched Ensemble(32)の全てで満たす**
- Formal OOS候補: **global-g00001-c01-2ac3662ad1**
- Champion比較 trusted: **3回** / Random比較 trusted: **3回** / Matched比較 trusted: **3回**
- 平均score差 vs Champion / Random / Matched: **+0.4633 / +0.4967 / +0.8700**
- 勝率 vs Champion / Random / Matched: **66.7% / 66.7% / 66.7%**
- raw e-value vs Champion: **1.0633**
- raw e-value vs Random: **1.0601**
- raw e-value vs Matched: **1.0996**
- family-adjusted intersection e-value: **0.5019** / threshold **20.0000**
- 現block必要raw e-value: **40.00**
- Random reference valid: **YES**
- Matched reference valid: **YES**

## Matched Permutation Ensemble

- Ensemble版: **matched-permutation-ensemble-v1**
- Ensemble size: **32**
- Promotionで使用: **YES**
- 第696回事前凍結: **YES**
- Ensemble凍結日時(JST): **2026-09-18T22:48:17+09:00**
- member 0（旧single comparator）凍結日時(JST): **2026-09-18T22:48:17+09:00**
- Null構造: **32個の共通数字ラベル置換。各memberは5口のticket overlap / union coverage / portfolio geometryを元Challengerと同一に保持**
- 集約方法: **32 memberのportfolio score平均を1回のMatched Ensemble基準scoreとして使用**
- 旧single Matched: **監査・telemetry用として保持。Production昇格のMatchedゲートはEnsemble平均を使用**
- Ensemble trusted OOS: **3/8回**
- 平均score差 vs Matched Ensemble: **+0.0822**
- 勝率 vs Matched Ensemble: **66.7%**
- raw e-value vs Matched Ensemble: **1.0038**
- family-adjusted intersection e-value: **0.5019** / threshold **20.0000**
- Holdout Ensemble進捗: **3/26 trusted draws**
- Holdout平均score差 vs Matched Ensemble: **+0.0822**
- Holdout勝率 vs Matched Ensemble: **66.7%**
- Holdout e-value vs Matched Ensemble: **1.0038**
- Holdout Ensemble凍結: **YES**

### Ensemble Rank Diagnostics

- Rank診断版: **matched-ensemble-rank-diagnostics-v1**
- 定義: **percentileはnull内mid-rank、MC p=(1 + #null score ≥ Challenger score)/(32 + 1)**
- Rank診断用途: **diagnostic only（Production昇格判定には未使用。sequential e-processを維持）**
- 単回Monte-Carlo permutation p最小値: **0.0303** (= 1/33)
- Rank診断 trusted OOS: **3/8回**
- 直近(第695回) percentile / MC p: **93.75% / 0.0909**
- 直近 observed+null rank: **3.0/33位相当** (null below/equal/above = 30/0/2)
- trusted平均 percentile / 単回MC p平均: **60.94% / 0.4141**
- Holdout Rank診断: **3/26 trusted draws**
- Holdout直近(第695回) percentile / MC p / rank: **93.75% / 0.0909 / 3.0/33位相当**
- Holdout平均 percentile / 単回MC p平均: **60.94% / 0.4141**

### Ensemble Score Vector Audit

- Score vector監査版: **matched-ensemble-score-vector-audit-v1**
- Hash: **sha256**
- canonical float: **.17g binary64 round-trip decimal string**
- 用途: **diagnostic only。Promotion e-process / 閾値は変更しない**
- Formal 32-member reference SHA-256事前確定: **YES**
- Formal reference SHA-256: **d9d1fc2a4d18f2faad9cbcc49bd53738ffbbdd6fce8b809b9919f2d8a17472d0**
- Holdout 32-member reference SHA-256事前確定: **YES**
- Holdout reference SHA-256: **d9d1fc2a4d18f2faad9cbcc49bd53738ffbbdd6fce8b809b9919f2d8a17472d0**
- Formal score vector audit status: **active**
- 直近score vector: **第695回 / SHA-256 23278db27ea0ef95f3fedcbba27a2f0384fe2abf8be099fb6d49272753fa3116**
- 直近audit record SHA-256: **c3eb07ca4c26d33276f089c8924a237154b98bb5c2155a73bc22ae16f45b3261**
- 直近rank/p replay一致: **YES**
- Holdout直近score vector SHA-256: **23278db27ea0ef95f3fedcbba27a2f0384fe2abf8be099fb6d49272753fa3116**
- Holdout直近rank/p replay一致: **YES**

## Fixed Prospective Holdout

- 状態: **active**
- 固定モデル: **global-g00001-c01-2ac3662ad1**
- 進捗: **3/26 trusted draws** / Matched **3/26**
- 現在の事前凍結対象回: **第696回**
- 平均score差 vs Champion / Random / Matched: **+0.4633 / +0.4967 / +0.8700**
- 勝率 vs Champion / Random / Matched: **66.7% / 66.7% / 66.7%**
- e-value vs Champion / Random / Matched: **1.0633 / 1.0601 / 1.0996**
- Matched reference frozen: **YES**
- 用途: **26 trusted draws固定のprospective診断。途中でconfig変更しない**

## Continuous Runtime

- 最新1回の研究実行時間: **1437秒**
- 直近20回平均: **1234.2秒**
- 累積実測回数: **4924回**
- 実行方式: **終了後、待ち時間なしで次の研究世代へ**
- Git checkpoint: **10世代ごと、または重要イベント発生時**
