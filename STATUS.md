# LOTO7 AI Agent Status

- 更新日時 (JST): **2026-11-12T08:16:58+09:00**
- 最新取得回: **第702回 / 2026-11-06**
- 最新Production対象: **第703回（未発行）**
- 未照合予測: **0口**
- モデル: **baseline-5fdb8dc2ad+production-disjoint35-layout-v1**
- データSHA256: `e05bea1debf088a52daedfc9ecb488ca7db11e273ac16f348f3fda19ac626637`
- ソース検証: **verified_two_result_sources**
- 取得状態: **ok**

> Productionの凍結は金曜13:00〜15:00 JSTのProduction publisher系統のみが行います。通常checkpointは既存の凍結台帳を照合・表示するだけです。

## Continuous Research v4

- 研究世代: **6190**
- Production Champion: **baseline-5fdb8dc2ad**
- 最新Research Winner: **signal-g05814-c01-a0b6c7d9c2**
- 候補プール: **16モデル**
- 累積研究評価数: **43329**
- 過去データの研究スコアから本番昇格: **無効（禁止）**
- 現在ソース検証: **verified_two_result_sources**
- 本番昇格に利用可能なソース: **YES**

## Research Signal / Portfolio Separation

- Research Parent: **signal-g05814-c01-a0b6c7d9c2**
- 全期間 Top7 edge vs uniform: **+0.0229**
- 全期間 actual-mass edge vs uniform: **+0.001314**
- 全期間 log edge vs uniform: **-0.017849**
- 全期間 Brier edge vs uniform: **-0.001314**
- 直近120回 log edge vs uniform: **-0.017375**
- Portfolio feedback objective: **+0.2633**
- Signal objective: **-0.0458**
- Research採用: **Portfolio改善だけでは不可。Signal非劣化ゲートも必須**

## Historical Replay Accuracy

- 評価回数: **602回** (101〜702)
- Top7平均本数字一致: **1.3671** / random **1.3243**
- Top7近似両側p: **0.267105** / 判定 **not_confirmed**
- 5口平均最大一致: **2.2475** / random **2.4249**
- 5口平均score差 vs random: **-0.1934**
- 3個以上一致券あり: **36.7%** / random **42.9%**
- 4個以上一致券あり: **7.1%** / random **6.8%**
- 何らかの等級当選があった回: **16.61%**
- 用途: **過去回の精度確認専用。v4 Champion昇格の未来OOS証拠には使用しない**

## Historical Reconciliation

- 独立再照合: **602回 / 3010口**
- 当選口数: **127口** (4.219%)
- 参考購入額: **903,000円**
- 公表当選額ベース参考払戻: **175,900円**
- 参考回収率: **19.48%**
- 予測側実績とloto7.csvの不一致: **0件**

## Nested Champion / Research / Random

- Nested評価回数: **120回** (583〜702)
- 平均score Champion / Research / Random: **2.5379 / 2.6311 / 2.7689**
- Research差 vs Champion: **+0.0932** (95% CI -0.0815〜+0.2688)
- Research差 vs Random: **-0.1379** (95% CI -0.3612〜+0.0903)
- Research勝率 vs Champion / Random: **42.5% / 35.0%**
- 選択方法: **各対象回より前の成績のみで事前定義モデルから選択**

## Formal Challenger

- Formal Challenger: **evo-g04766-c01-a63936bd65**
- block id: **e48bc9ec5d6c52c5**
- strict block index: **2**
- block開始対象回: **第702回**
- trusted Future OOS: **1/8回**
- family weight: **0.16666667**
- 必要raw e-value: **120.00**
- 現在の凍結対象回: **第703回**
- Promotion候補数: **1**
- ポリシー: **同一Challengerを8 trusted drawsまで固定し、Champion・事前凍結Random・32-member geometry-matched permutation ensembleの全てに勝つことを要求**

## Strict Future OOS Governance

- ガバナンス版: **strict-oos-governance-v1**
- Matched null版: **matched-permutation-null-v1**
- 凍結済みshadow対象回: **第703回**
- Promotion対象shadow候補数: **1**
- 最終OOS採点回: **702**
- 累積Champion昇格数: **0**
- Uniform Random凍結: **YES** / Matched凍結: **YES**
- strict昇格条件: **8 paired trusted draws / adjusted e-value ≥ 20 / 平均score差 ≥ +0.05 / 勝率 ≥ 55% をChampion・Random・Matched Ensemble(32)の全てで満たす**
- Formal OOS候補: **evo-g04766-c01-a63936bd65**
- Champion比較 trusted: **1回** / Random比較 trusted: **1回** / Matched比較 trusted: **1回**
- 平均score差 vs Champion / Random / Matched: **+0.0000 / -0.0400 / -2.5100**
- 勝率 vs Champion / Random / Matched: **0.0% / 0.0% / 0.0%**
- raw e-value vs Champion: **1.0000**
- raw e-value vs Random: **0.9982**
- raw e-value vs Matched: **0.8859**
- family-adjusted intersection e-value: **0.1539** / threshold **20.0000**
- 現block必要raw e-value: **120.00**
- Random reference valid: **YES**
- Matched reference valid: **YES**

## Matched Permutation Ensemble

- Ensemble版: **matched-permutation-ensemble-v1**
- Ensemble size: **32**
- Promotionで使用: **YES**
- 第703回事前凍結: **YES**
- Ensemble凍結日時(JST): **2026-11-07T02:01:54+09:00**
- member 0（旧single comparator）凍結日時(JST): **2026-11-07T02:01:54+09:00**
- Null構造: **32個の共通数字ラベル置換。各memberは5口のticket overlap / union coverage / portfolio geometryを元Challengerと同一に保持**
- 集約方法: **32 memberのportfolio score平均を1回のMatched Ensemble基準scoreとして使用**
- 旧single Matched: **監査・telemetry用として保持。Production昇格のMatchedゲートはEnsemble平均を使用**
- Ensemble trusted OOS: **1/8回**
- 平均score差 vs Matched Ensemble: **-1.6859**
- 勝率 vs Matched Ensemble: **0.0%**
- raw e-value vs Matched Ensemble: **0.9234**
- family-adjusted intersection e-value: **0.1539** / threshold **20.0000**
- Holdout Ensemble進捗: **9/26 trusted draws**
- Holdout平均score差 vs Matched Ensemble: **-0.1554**
- Holdout勝率 vs Matched Ensemble: **33.3%**
- Holdout e-value vs Matched Ensemble: **0.9291**
- Holdout Ensemble凍結: **YES**

### Ensemble Rank Diagnostics

- Rank診断版: **matched-ensemble-rank-diagnostics-v1**
- 定義: **percentileはnull内mid-rank、MC p=(1 + #null score ≥ Challenger score)/(32 + 1)**
- Rank診断用途: **diagnostic only（Production昇格判定には未使用。sequential e-processを維持）**
- 単回Monte-Carlo permutation p最小値: **0.0303** (= 1/33)
- Rank診断 trusted OOS: **1/8回**
- 直近(第702回) percentile / MC p: **0.00% / 1.0000**
- 直近 observed+null rank: **33.0/33位相当** (null below/equal/above = 0/0/32)
- trusted平均 percentile / 単回MC p平均: **0.00% / 1.0000**
- Holdout Rank診断: **9/26 trusted draws**
- Holdout直近(第702回) percentile / MC p / rank: **21.88% / 0.8182 / 26.0/33位相当**
- Holdout平均 percentile / 単回MC p平均: **52.60% / 0.5152**

### Ensemble Score Vector Audit

- Score vector監査版: **matched-ensemble-score-vector-audit-v1**
- Hash: **sha256**
- canonical float: **.17g binary64 round-trip decimal string**
- 用途: **diagnostic only。Promotion e-process / 閾値は変更しない**
- Formal 32-member reference SHA-256事前確定: **YES**
- Formal reference SHA-256: **e02cac69b46c25cab7bfc9f5873678b4d573d49c822aceb3af4b81a40ad47383**
- Holdout 32-member reference SHA-256事前確定: **YES**
- Holdout reference SHA-256: **31895f0547fd8b5b7c374ceda9bca2705ccb45404a85f0c7d47ae0935a1123e8**
- Formal score vector audit status: **active**
- 直近score vector: **第702回 / SHA-256 4f16a578ef15c23471ce57fad5d3d22c832971d8e846f37977bf60b9958651d6**
- 直近audit record SHA-256: **95368c10b693c1f1a0b095b76c98581539745c686c72792478873eade71e0994**
- 直近rank/p replay一致: **YES**
- Holdout直近score vector SHA-256: **3a12300e9dfe85f746b755c24f269a4a54ddc179930fecd3a8f018e95cdd1f61**
- Holdout直近rank/p replay一致: **YES**

## Fixed Prospective Holdout

- 状態: **active**
- 固定モデル: **global-g00001-c01-2ac3662ad1**
- 進捗: **9/26 trusted draws** / Matched **9/26**
- 現在の事前凍結対象回: **第703回**
- 平均score差 vs Champion / Random / Matched: **-0.2422 / -0.3722 / -0.2611**
- 勝率 vs Champion / Random / Matched: **44.4% / 44.4% / 44.4%**
- e-value vs Champion / Random / Matched: **0.8825 / 0.8327 / 0.8533**
- Matched reference frozen: **YES**
- 用途: **26 trusted draws固定のprospective診断。途中でconfig変更しない**

## Sakura Credential Rotation

- 状態: **pending_external_rotation_verification**
- Verification version: **sakura-credential-rotation-verification-v1**
- Credential generation: **未検証**
- secret値をSTATUS/Gitへ記録: **NO**

## Continuous Runtime

- 最新1回の研究実行時間: **1537秒**
- 直近20回平均: **1434.0秒**
- 累積実測回数: **7774回**
- 実行方式: **終了後、待ち時間なしで次の研究世代へ**
- Git checkpoint: **10世代ごと、または重要イベント発生時**

## Fixed Future OOS Evidence Claim

- Claim status: **not_confirmed_holdout_incomplete**
- 進捗: **9/26 trusted** / Matched **9/26**
- Protocol lock verified: **True**
- Confirmation policy preregistered before first outcome: **False**
- vs Random: mean delta **-0.3722** / win **44.4%** / e **0.8327**
- vs Matched Ensemble(32): mean delta **-0.1554** / win **33.3%** / e **0.9291**
- 26/26完了前は confirmed を出さない。
