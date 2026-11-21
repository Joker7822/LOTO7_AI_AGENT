# LOTO7 AI Agent Status

- 更新日時 (JST): **2026-11-21T12:33:27+09:00**
- 最新取得回: **第704回 / 2026-11-20**
- 最新Production対象: **第705回（未発行）**
- 未照合予測: **0口**
- モデル: **baseline-5fdb8dc2ad+production-disjoint35-layout-v1**
- データSHA256: `dd26a11d78267c8d73925700ab88f6b246b22153f06ee12a064cf19695fdcc2c`
- ソース検証: **verified_two_result_sources**
- 取得状態: **ok**

> Productionの凍結は金曜13:00〜15:00 JSTのProduction publisher系統のみが行います。通常checkpointは既存の凍結台帳を照合・表示するだけです。

## Continuous Research v4

- 研究世代: **6792**
- Production Champion: **baseline-5fdb8dc2ad**
- 最新Research Winner: **signal-g05814-c01-a0b6c7d9c2**
- 候補プール: **16モデル**
- 累積研究評価数: **47543**
- 過去データの研究スコアから本番昇格: **無効（禁止）**
- 現在ソース検証: **verified_two_result_sources**
- 本番昇格に利用可能なソース: **YES**

## Research Signal / Portfolio Separation

- Research Parent: **signal-g05814-c01-a0b6c7d9c2**
- 全期間 Top7 edge vs uniform: **+0.0217**
- 全期間 actual-mass edge vs uniform: **+0.001274**
- 全期間 log edge vs uniform: **-0.017998**
- 全期間 Brier edge vs uniform: **-0.001325**
- 直近120回 log edge vs uniform: **-0.017673**
- Portfolio feedback objective: **+0.2417**
- Signal objective: **-0.0464**
- Research採用: **Portfolio改善だけでは不可。Signal非劣化ゲートも必須**

## Historical Replay Accuracy

- 評価回数: **604回** (101〜704)
- Top7平均本数字一致: **1.3659** / random **1.3243**
- Top7近似両側p: **0.280136** / 判定 **not_confirmed**
- 5口平均最大一致: **2.2450** / random **2.4246**
- 5口平均score差 vs random: **-0.1961**
- 3個以上一致券あり: **36.6%** / random **42.9%**
- 4個以上一致券あり: **7.1%** / random **6.8%**
- 何らかの等級当選があった回: **16.56%**
- 用途: **過去回の精度確認専用。v4 Champion昇格の未来OOS証拠には使用しない**

## Historical Reconciliation

- 独立再照合: **604回 / 3020口**
- 当選口数: **127口** (4.205%)
- 参考購入額: **906,000円**
- 公表当選額ベース参考払戻: **175,900円**
- 参考回収率: **19.42%**
- 予測側実績とloto7.csvの不一致: **0件**

## Nested Champion / Research / Random

- Nested評価回数: **120回** (585〜704)
- 平均score Champion / Research / Random: **2.5403 / 2.6222 / 2.7708**
- Research差 vs Champion: **+0.0819** (95% CI -0.1008〜+0.2547)
- Research差 vs Random: **-0.1485** (95% CI -0.3700〜+0.0789)
- Research勝率 vs Champion / Random: **43.3% / 35.0%**
- 選択方法: **各対象回より前の成績のみで事前定義モデルから選択**

## Formal Challenger

- Formal Challenger: **evo-g04766-c01-a63936bd65**
- block id: **e48bc9ec5d6c52c5**
- strict block index: **2**
- block開始対象回: **第702回**
- trusted Future OOS: **3/8回**
- family weight: **0.16666667**
- 必要raw e-value: **120.00**
- 現在の凍結対象回: **第705回**
- Promotion候補数: **1**
- ポリシー: **同一Challengerを8 trusted drawsまで固定し、Champion・事前凍結Random・32-member geometry-matched permutation ensembleの全てに勝つことを要求**

## Strict Future OOS Governance

- ガバナンス版: **strict-oos-governance-v1**
- Matched null版: **matched-permutation-null-v1**
- 凍結済みshadow対象回: **第705回**
- Promotion対象shadow候補数: **1**
- 最終OOS採点回: **704**
- 累積Champion昇格数: **0**
- Uniform Random凍結: **YES** / Matched凍結: **YES**
- strict昇格条件: **8 paired trusted draws / adjusted e-value ≥ 20 / 平均score差 ≥ +0.05 / 勝率 ≥ 55% をChampion・Random・Matched Ensemble(32)の全てで満たす**
- Formal OOS候補: **evo-g04766-c01-a63936bd65**
- Champion比較 trusted: **3回** / Random比較 trusted: **3回** / Matched比較 trusted: **3回**
- 平均score差 vs Champion / Random / Matched: **+0.7967 / +0.7633 / -1.4467**
- 勝率 vs Champion / Random / Matched: **66.7% / 33.3% / 33.3%**
- raw e-value vs Champion: **1.1126**
- raw e-value vs Random: **1.1030**
- raw e-value vs Matched: **0.8052**
- family-adjusted intersection e-value: **0.1501** / threshold **20.0000**
- 現block必要raw e-value: **120.00**
- Random reference valid: **YES**
- Matched reference valid: **YES**

## Matched Permutation Ensemble

- Ensemble版: **matched-permutation-ensemble-v1**
- Ensemble size: **32**
- Promotionで使用: **YES**
- 第705回事前凍結: **YES**
- Ensemble凍結日時(JST): **2026-11-21T02:35:05+09:00**
- member 0（旧single comparator）凍結日時(JST): **2026-11-21T02:35:05+09:00**
- Null構造: **32個の共通数字ラベル置換。各memberは5口のticket overlap / union coverage / portfolio geometryを元Challengerと同一に保持**
- 集約方法: **32 memberのportfolio score平均を1回のMatched Ensemble基準scoreとして使用**
- 旧single Matched: **監査・telemetry用として保持。Production昇格のMatchedゲートはEnsemble平均を使用**
- Ensemble trusted OOS: **3/8回**
- 平均score差 vs Matched Ensemble: **-0.7367**
- 勝率 vs Matched Ensemble: **33.3%**
- raw e-value vs Matched Ensemble: **0.9006**
- family-adjusted intersection e-value: **0.1501** / threshold **20.0000**
- Holdout Ensemble進捗: **11/26 trusted draws**
- Holdout平均score差 vs Matched Ensemble: **-0.1374**
- Holdout勝率 vs Matched Ensemble: **36.4%**
- Holdout e-value vs Matched Ensemble: **0.9233**
- Holdout Ensemble凍結: **YES**

### Ensemble Rank Diagnostics

- Rank診断版: **matched-ensemble-rank-diagnostics-v1**
- 定義: **percentileはnull内mid-rank、MC p=(1 + #null score ≥ Challenger score)/(32 + 1)**
- Rank診断用途: **diagnostic only（Production昇格判定には未使用。sequential e-processを維持）**
- 単回Monte-Carlo permutation p最小値: **0.0303** (= 1/33)
- Rank診断 trusted OOS: **3/8回**
- 直近(第704回) percentile / MC p: **78.12% / 0.3333**
- 直近 observed+null rank: **8.0/33位相当** (null below/equal/above = 22/6/4)
- trusted平均 percentile / 単回MC p平均: **28.12% / 0.7677**
- Holdout Rank診断: **11/26 trusted draws**
- Holdout直近(第704回) percentile / MC p / rank: **62.50% / 0.4242 / 13.0/33位相当**
- Holdout平均 percentile / 単回MC p平均: **49.86% / 0.5427**

### Ensemble Score Vector Audit

- Score vector監査版: **matched-ensemble-score-vector-audit-v1**
- Hash: **sha256**
- canonical float: **.17g binary64 round-trip decimal string**
- 用途: **diagnostic only。Promotion e-process / 閾値は変更しない**
- Formal 32-member reference SHA-256事前確定: **YES**
- Formal reference SHA-256: **18561fc805ed6290a0bc234a3643c2801320eaf1b023603cb691fadfcfd87971**
- Holdout 32-member reference SHA-256事前確定: **YES**
- Holdout reference SHA-256: **1c18cee0416dbdf298d26962dcccb682615fd9912c5f9044330c6a9b29229d28**
- Formal score vector audit status: **active**
- 直近score vector: **第704回 / SHA-256 79354fc3341cfe35e68983b12ea2dd0e3d3b0418d8fd9d6d1815ede6b8e935f6**
- 直近audit record SHA-256: **5b95f4ddf67896b94b8ddca7ff35b06a96adca4b63d3050b57d0b2d5f6687ba2**
- 直近rank/p replay一致: **YES**
- Holdout直近score vector SHA-256: **090b5245ce541a4669f2507f83ea6aa1441c5d0531083e15b1bf151d195ab274**
- Holdout直近rank/p replay一致: **YES**

## Fixed Prospective Holdout

- 状態: **active**
- 固定モデル: **global-g00001-c01-2ac3662ad1**
- 進捗: **11/26 trusted draws** / Matched **11/26**
- 現在の事前凍結対象回: **第705回**
- 平均score差 vs Champion / Random / Matched: **+0.0155 / -0.0964 / -0.3491**
- 勝率 vs Champion / Random / Matched: **54.5% / 45.5% / 36.4%**
- e-value vs Champion / Random / Matched: **0.9747 / 0.9118 / 0.7998**
- Matched reference frozen: **YES**
- 用途: **26 trusted draws固定のprospective診断。途中でconfig変更しない**

## Sakura Credential Rotation

- 状態: **pending_external_rotation_verification**
- Verification version: **sakura-credential-rotation-verification-v1**
- Credential generation: **未検証**
- secret値をSTATUS/Gitへ記録: **NO**

## Continuous Runtime

- 最新1回の研究実行時間: **732秒**
- 直近20回平均: **490.1秒**
- 累積実測回数: **8452回**
- 実行方式: **終了後、待ち時間なしで次の研究世代へ**
- Git checkpoint: **10世代ごと、または重要イベント発生時**

## Fixed Future OOS Evidence Claim

- Claim status: **not_confirmed_holdout_incomplete**
- 進捗: **11/26 trusted** / Matched **11/26**
- Protocol lock verified: **True**
- Confirmation policy preregistered before first outcome: **False**
- vs Random: mean delta **-0.0964** / win **45.5%** / e **0.9118**
- vs Matched Ensemble(32): mean delta **-0.1374** / win **36.4%** / e **0.9233**
- 26/26完了前は confirmed を出さない。
