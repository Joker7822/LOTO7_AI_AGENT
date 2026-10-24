# LOTO7 AI Agent Status

- 更新日時 (JST): **2026-10-24T10:43:52+09:00**
- 最新取得回: **第700回 / 2026-10-23**
- 最新Production対象: **第701回（未発行）**
- 未照合予測: **0口**
- モデル: **baseline-5fdb8dc2ad**
- データSHA256: `5e4fa6fcc544604e52d591b75076365ff190664ecc508f853f27671f8af595cf`
- ソース検証: **degraded_single_result_source**
- 取得状態: **degraded**

> Productionの凍結は金曜13:00〜15:00 JSTのProduction publisher系統のみが行います。通常checkpointは既存の凍結台帳を照合・表示するだけです。

## Continuous Research v4

- 研究世代: **5119**
- Production Champion: **baseline-5fdb8dc2ad**
- 最新Research Winner: **signal-g04789-c01-29ccf32ff6**
- 候補プール: **17モデル**
- 累積研究評価数: **35832**
- 過去データの研究スコアから本番昇格: **無効（禁止）**
- 現在ソース検証: **degraded_single_result_source**
- 本番昇格に利用可能なソース: **NO**

## Research Signal / Portfolio Separation

- Signal分離評価: **初回再評価待ち**

## Historical Replay Accuracy

- 評価回数: **600回** (101〜700)
- Top7平均本数字一致: **1.3683** / random **1.3243**
- Top7近似両側p: **0.254455** / 判定 **not_confirmed**
- 5口平均最大一致: **2.2483** / random **2.4247**
- 5口平均score差 vs random: **-0.1923**
- 3個以上一致券あり: **36.7%** / random **42.9%**
- 4個以上一致券あり: **7.2%** / random **6.8%**
- 何らかの等級当選があった回: **16.50%**
- 用途: **過去回の精度確認専用。v4 Champion昇格の未来OOS証拠には使用しない**

## Historical Reconciliation

- 独立再照合: **600回 / 3000口**
- 当選口数: **126口** (4.200%)
- 参考購入額: **900,000円**
- 公表当選額ベース参考払戻: **174,900円**
- 参考回収率: **19.43%**
- 予測側実績とloto7.csvの不一致: **0件**

## Nested Champion / Research / Random

- Nested評価回数: **120回** (581〜700)
- 平均score Champion / Research / Random: **2.5497 / 2.6193 / 2.7707**
- Research差 vs Champion: **+0.0697** (95% CI -0.1052〜+0.2448)
- Research差 vs Random: **-0.1514** (95% CI -0.3643〜+0.0769)
- Research勝率 vs Champion / Random: **40.8% / 34.2%**
- 選択方法: **各対象回より前の成績のみで事前定義モデルから選択**

## Formal Challenger

- Formal Challenger: **global-g00001-c01-2ac3662ad1**
- block id: **36d2ec03cdf5da70**
- strict block index: **1**
- block開始対象回: **第692回**
- trusted Future OOS: **7/8回**
- family weight: **0.50000000**
- 必要raw e-value: **40.00**
- 現在の凍結対象回: **第701回**
- Promotion候補数: **1**
- ポリシー: **同一Challengerを8 trusted drawsまで固定し、Champion・事前凍結Random・32-member geometry-matched permutation ensembleの全てに勝つことを要求**

## Strict Future OOS Governance

- ガバナンス版: **strict-oos-governance-v1**
- Matched null版: **matched-permutation-null-v1**
- 凍結済みshadow対象回: **第701回**
- Promotion対象shadow候補数: **1**
- 最終OOS採点回: **700**
- 累積Champion昇格数: **0**
- Uniform Random凍結: **YES** / Matched凍結: **YES**
- strict昇格条件: **8 paired trusted draws / adjusted e-value ≥ 20 / 平均score差 ≥ +0.05 / 勝率 ≥ 55% をChampion・Random・Matched Ensemble(32)の全てで満たす**
- Formal OOS候補: **global-g00001-c01-2ac3662ad1**
- Champion比較 trusted: **7回** / Random比較 trusted: **7回** / Matched比較 trusted: **7回**
- 平均score差 vs Champion / Random / Matched: **-0.0029 / -0.4257 / +0.0757**
- 勝率 vs Champion / Random / Matched: **42.9% / 42.9% / 57.1%**
- raw e-value vs Champion: **0.9881**
- raw e-value vs Random: **0.8489**
- raw e-value vs Matched: **0.9722**
- family-adjusted intersection e-value: **0.4244** / threshold **20.0000**
- 現block必要raw e-value: **40.00**
- Random reference valid: **YES**
- Matched reference valid: **YES**

## Matched Permutation Ensemble

- Ensemble版: **matched-permutation-ensemble-v1**
- Ensemble size: **32**
- Promotionで使用: **YES**
- 第701回事前凍結: **YES**
- Ensemble凍結日時(JST): **2026-10-24T09:52:56+09:00**
- member 0（旧single comparator）凍結日時(JST): **2026-10-24T09:52:56+09:00**
- Null構造: **32個の共通数字ラベル置換。各memberは5口のticket overlap / union coverage / portfolio geometryを元Challengerと同一に保持**
- 集約方法: **32 memberのportfolio score平均を1回のMatched Ensemble基準scoreとして使用**
- 旧single Matched: **監査・telemetry用として保持。Production昇格のMatchedゲートはEnsemble平均を使用**
- Ensemble trusted OOS: **7/8回**
- 平均score差 vs Matched Ensemble: **-0.0767**
- 勝率 vs Matched Ensemble: **42.9%**
- raw e-value vs Matched Ensemble: **0.9659**
- family-adjusted intersection e-value: **0.4244** / threshold **20.0000**
- Holdout Ensemble進捗: **7/26 trusted draws**
- Holdout平均score差 vs Matched Ensemble: **-0.0767**
- Holdout勝率 vs Matched Ensemble: **42.9%**
- Holdout e-value vs Matched Ensemble: **0.9659**
- Holdout Ensemble凍結: **YES**

### Ensemble Rank Diagnostics

- Rank診断版: **matched-ensemble-rank-diagnostics-v1**
- 定義: **percentileはnull内mid-rank、MC p=(1 + #null score ≥ Challenger score)/(32 + 1)**
- Rank診断用途: **diagnostic only（Production昇格判定には未使用。sequential e-processを維持）**
- 単回Monte-Carlo permutation p最小値: **0.0303** (= 1/33)
- Rank診断 trusted OOS: **7/8回**
- 直近(第700回) percentile / MC p: **26.56% / 0.8182**
- 直近 observed+null rank: **24.5/33位相当** (null below/equal/above = 6/5/21)
- trusted平均 percentile / 単回MC p平均: **58.04% / 0.4589**
- Holdout Rank診断: **7/26 trusted draws**
- Holdout直近(第700回) percentile / MC p / rank: **26.56% / 0.8182 / 24.5/33位相当**
- Holdout平均 percentile / 単回MC p平均: **58.04% / 0.4589**

### Ensemble Score Vector Audit

- Score vector監査版: **matched-ensemble-score-vector-audit-v1**
- Hash: **sha256**
- canonical float: **.17g binary64 round-trip decimal string**
- 用途: **diagnostic only。Promotion e-process / 閾値は変更しない**
- Formal 32-member reference SHA-256事前確定: **YES**
- Formal reference SHA-256: **3730f8285b45dbf3690fc4ba88118be7a664c3a65a792f4d93a0217681e69634**
- Holdout 32-member reference SHA-256事前確定: **YES**
- Holdout reference SHA-256: **3730f8285b45dbf3690fc4ba88118be7a664c3a65a792f4d93a0217681e69634**
- Formal score vector audit status: **active**
- 直近score vector: **第700回 / SHA-256 1f47e8afdc1a2dbbc30e214b2d9c526fa3d1c568d6fb5261b401b9b4e7feddcd**
- 直近audit record SHA-256: **226f6787f468e68e388079f925b63e87c033a978c8bae622464685e97b3abc0f**
- 直近rank/p replay一致: **YES**
- Holdout直近score vector SHA-256: **1f47e8afdc1a2dbbc30e214b2d9c526fa3d1c568d6fb5261b401b9b4e7feddcd**
- Holdout直近rank/p replay一致: **YES**

## Fixed Prospective Holdout

- 状態: **active**
- 固定モデル: **global-g00001-c01-2ac3662ad1**
- 進捗: **7/26 trusted draws** / Matched **7/26**
- 現在の事前凍結対象回: **第701回**
- 平均score差 vs Champion / Random / Matched: **-0.0029 / -0.4257 / +0.0757**
- 勝率 vs Champion / Random / Matched: **42.9% / 42.9% / 57.1%**
- e-value vs Champion / Random / Matched: **0.9881 / 0.8489 / 0.9722**
- Matched reference frozen: **YES**
- 用途: **26 trusted draws固定のprospective診断。途中でconfig変更しない**

## Sakura Credential Rotation

- 状態: **pending_external_rotation_verification**
- Verification version: **sakura-credential-rotation-verification-v1**
- Credential generation: **未検証**
- secret値をSTATUS/Gitへ記録: **NO**

## Continuous Runtime

- 最新1回の研究実行時間: **98秒**
- 直近20回平均: **98.0秒**
- 累積実測回数: **6511回**
- 実行方式: **終了後、待ち時間なしで次の研究世代へ**
- Git checkpoint: **10世代ごと、または重要イベント発生時**

## Fixed Future OOS Evidence Claim

- Claim status: **not_confirmed_holdout_incomplete**
- 進捗: **7/26 trusted** / Matched **7/26**
- Protocol lock verified: **True**
- vs Random: mean delta **-0.4257** / win **42.9%** / e **0.8489**
- vs Matched Ensemble(32): mean delta **-0.0767** / win **42.9%** / e **0.9659**
- 26/26完了前は confirmed を出さない。
