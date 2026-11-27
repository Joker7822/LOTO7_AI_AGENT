# LOTO7 AI Agent Status

- 更新日時 (JST): **2026-11-28T06:49:06+09:00**
- 最新取得回: **第705回 / 2026-11-27**
- 最新Production対象: **第706回（未発行）**
- 未照合予測: **0口**
- モデル: **baseline-5fdb8dc2ad+production-ai-ranked35-roi-cash-v2**
- データSHA256: `9114a6f11003e7cc590e317f50b08da7cfc32cd5dfb1b9779432b032eca87b80`
- ソース検証: **verified_two_result_sources**
- 取得状態: **ok**

> Productionの凍結は金曜13:00〜15:00 JSTのProduction publisher系統のみが行います。通常checkpointは既存の凍結台帳を照合・表示するだけです。

## Continuous Research v4

- 研究世代: **6931**
- Production Champion: **baseline-5fdb8dc2ad**
- 最新Research Winner: **signal-g06845-c01-6183c9b064**
- 候補プール: **16モデル**
- 累積研究評価数: **48516**
- 過去データの研究スコアから本番昇格: **無効（禁止）**
- 現在ソース検証: **verified_two_result_sources**
- 本番昇格に利用可能なソース: **YES**

## Research Signal / Portfolio Separation

- Signal分離評価: **初回再評価待ち**

## Historical Replay Accuracy

- 評価回数: **605回** (101〜705)
- Top7平均本数字一致: **1.3653** / random **1.3243**
- Top7近似両側p: **0.286794** / 判定 **not_confirmed**
- 5口平均最大一致: **2.2446** / random **2.4247**
- 5口平均score差 vs random: **-0.1970**
- 3個以上一致券あり: **36.5%** / random **42.9%**
- 4個以上一致券あり: **7.1%** / random **6.8%**
- 何らかの等級当選があった回: **16.53%**
- 用途: **過去回の精度確認専用。v4 Champion昇格の未来OOS証拠には使用しない**

## Historical Reconciliation

- 独立再照合: **605回 / 3025口**
- 当選口数: **127口** (4.198%)
- 参考購入額: **907,500円**
- 公表当選額ベース参考払戻: **175,900円**
- 参考回収率: **19.38%**
- 予測側実績とloto7.csvの不一致: **0件**

## Nested Champion / Research / Random

- Nested評価回数: **120回** (586〜705)
- 平均score Champion / Research / Random: **2.5318 / 2.6338 / 2.7668**
- Research差 vs Champion: **+0.1020** (95% CI -0.0778〜+0.2781)
- Research差 vs Random: **-0.1330** (95% CI -0.3585〜+0.0937)
- Research勝率 vs Champion / Random: **44.2% / 35.8%**
- 選択方法: **各対象回より前の成績のみで事前定義モデルから選択**

## Formal Challenger

- Formal Challenger: **evo-g04766-c01-a63936bd65**
- block id: **e48bc9ec5d6c52c5**
- strict block index: **2**
- block開始対象回: **第702回**
- trusted Future OOS: **4/8回**
- family weight: **0.16666667**
- 必要raw e-value: **120.00**
- 現在の凍結対象回: **第706回**
- Promotion候補数: **1**
- ポリシー: **同一Challengerを8 trusted drawsまで固定し、Champion・事前凍結Random・32-member geometry-matched permutation ensembleの全てに勝つことを要求**

## Strict Future OOS Governance

- ガバナンス版: **strict-oos-governance-v1**
- Matched null版: **matched-permutation-null-v1**
- 凍結済みshadow対象回: **第706回**
- Promotion対象shadow候補数: **1**
- 最終OOS採点回: **705**
- 累積Champion昇格数: **0**
- Uniform Random凍結: **YES** / Matched凍結: **YES**
- strict昇格条件: **8 paired trusted draws / adjusted e-value ≥ 20 / 平均score差 ≥ +0.05 / 勝率 ≥ 55% をChampion・Random・Matched Ensemble(32)の全てで満たす**
- Formal OOS候補: **evo-g04766-c01-a63936bd65**
- Champion比較 trusted: **4回** / Random比較 trusted: **4回** / Matched比較 trusted: **4回**
- 平均score差 vs Champion / Random / Matched: **+0.5975 / +0.8375 / -1.4325**
- 勝率 vs Champion / Random / Matched: **50.0% / 50.0% / 25.0%**
- raw e-value vs Champion: **1.1126**
- raw e-value vs Random: **1.1580**
- raw e-value vs Matched: **0.7590**
- family-adjusted intersection e-value: **0.1469** / threshold **20.0000**
- 現block必要raw e-value: **120.00**
- Random reference valid: **YES**
- Matched reference valid: **YES**

## Matched Permutation Ensemble

- Ensemble版: **matched-permutation-ensemble-v1**
- Ensemble size: **32**
- Promotionで使用: **YES**
- 第706回事前凍結: **YES**
- Ensemble凍結日時(JST): **2026-11-28T03:59:55+09:00**
- member 0（旧single comparator）凍結日時(JST): **2026-11-28T03:59:55+09:00**
- Null構造: **32個の共通数字ラベル置換。各memberは5口のticket overlap / union coverage / portfolio geometryを元Challengerと同一に保持**
- 集約方法: **32 memberのportfolio score平均を1回のMatched Ensemble基準scoreとして使用**
- 旧single Matched: **監査・telemetry用として保持。Production昇格のMatchedゲートはEnsemble平均を使用**
- Ensemble trusted OOS: **4/8回**
- 平均score差 vs Matched Ensemble: **-0.6770**
- 勝率 vs Matched Ensemble: **25.0%**
- raw e-value vs Matched Ensemble: **0.8811**
- family-adjusted intersection e-value: **0.1469** / threshold **20.0000**
- Holdout Ensemble進捗: **12/26 trusted draws**
- Holdout平均score差 vs Matched Ensemble: **-0.1558**
- Holdout勝率 vs Matched Ensemble: **33.3%**
- Holdout e-value vs Matched Ensemble: **0.9088**
- Holdout Ensemble凍結: **YES**

### Ensemble Rank Diagnostics

- Rank診断版: **matched-ensemble-rank-diagnostics-v1**
- 定義: **percentileはnull内mid-rank、MC p=(1 + #null score ≥ Challenger score)/(32 + 1)**
- Rank診断用途: **diagnostic only（Production昇格判定には未使用。sequential e-processを維持）**
- 単回Monte-Carlo permutation p最小値: **0.0303** (= 1/33)
- Rank診断 trusted OOS: **4/8回**
- 直近(第705回) percentile / MC p: **32.81% / 0.6970**
- 直近 observed+null rank: **22.5/33位相当** (null below/equal/above = 10/1/21)
- trusted平均 percentile / 単回MC p平均: **29.30% / 0.7500**
- Holdout Rank診断: **12/26 trusted draws**
- Holdout直近(第705回) percentile / MC p / rank: **51.56% / 0.5455 / 16.5/33位相当**
- Holdout平均 percentile / 単回MC p平均: **50.00% / 0.5429**

### Ensemble Score Vector Audit

- Score vector監査版: **matched-ensemble-score-vector-audit-v1**
- Hash: **sha256**
- canonical float: **.17g binary64 round-trip decimal string**
- 用途: **diagnostic only。Promotion e-process / 閾値は変更しない**
- Formal 32-member reference SHA-256事前確定: **YES**
- Formal reference SHA-256: **d775f5c7530197adeffb7173762da58fbcee9277540617373f73e4edc612614d**
- Holdout 32-member reference SHA-256事前確定: **YES**
- Holdout reference SHA-256: **b08c476f8e9f3a80af4fc82eb3f2f62f537bf7e1847b13744a94c81f2f623f32**
- Formal score vector audit status: **active**
- 直近score vector: **第705回 / SHA-256 87ddd5e4c359071780964ec80a368355b2ae80a2fc3e2b9cf581d4ae6729a969**
- 直近audit record SHA-256: **527a1e26e1dae376b87b8ab73e5b02f88672b1b54fa7a9c56925e6695bc851a9**
- 直近rank/p replay一致: **YES**
- Holdout直近score vector SHA-256: **dd62475f72e1ee98f732a29725f6377cbdb80783181f55fcc9cbbf9006fa681d**
- Holdout直近rank/p replay一致: **YES**

## Fixed Prospective Holdout

- 状態: **active**
- 固定モデル: **global-g00001-c01-2ac3662ad1**
- 進捗: **12/26 trusted draws** / Matched **12/26**
- 現在の事前凍結対象回: **第706回**
- 平均score差 vs Champion / Random / Matched: **+0.0142 / +0.0000 / -0.5850**
- 勝率 vs Champion / Random / Matched: **50.0% / 50.0% / 33.3%**
- e-value vs Champion / Random / Matched: **0.9747 / 0.9537 / 0.6958**
- Matched reference frozen: **YES**
- 用途: **26 trusted draws固定のprospective診断。途中でconfig変更しない**

## Continuous Runtime

- 最新1回の研究実行時間: **65秒**
- 直近20回平均: **64.7秒**
- 累積実測回数: **8643回**
- 実行方式: **終了後、待ち時間なしで次の研究世代へ**
- Git checkpoint: **10世代ごと、または重要イベント発生時**

## Fixed Future OOS Evidence Claim

- Claim status: **not_confirmed_holdout_incomplete**
- 進捗: **12/26 trusted** / Matched **12/26**
- Protocol lock verified: **True**
- Confirmation policy preregistered before first outcome: **False**
- vs Random: mean delta **+0.0000** / win **50.0%** / e **0.9537**
- vs Matched Ensemble(32): mean delta **-0.1558** / win **33.3%** / e **0.9088**
- 26/26完了前は confirmed を出さない。
