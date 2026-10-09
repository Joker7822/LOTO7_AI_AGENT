# LOTO7 AI Agent Status

- 更新日時 (JST): **2026-10-10T05:52:57+09:00**
- 最新取得回: **第698回 / 2026-10-09**
- 最新Production対象: **第699回（未発行）**
- 未照合予測: **0口**
- モデル: **baseline-5fdb8dc2ad**
- データSHA256: `75b03b7af1aa7294811b90a3167a06139617717823686c64bb04e6cc2257b8f4`
- ソース検証: **verified_two_result_sources**
- 取得状態: **ok**

> Productionの凍結は金曜13:00〜15:00 JSTのProduction publisher系統のみが行います。通常checkpointは既存の凍結台帳を照合・表示するだけです。

## Continuous Research v4

- 研究世代: **4584**
- Production Champion: **baseline-5fdb8dc2ad**
- 最新Research Winner: **signal-g02253-c01-b6030e66c9**
- 候補プール: **17モデル**
- 累積研究評価数: **32087**
- 過去データの研究スコアから本番昇格: **無効（禁止）**
- 現在ソース検証: **verified_two_result_sources**
- 本番昇格に利用可能なソース: **YES**

## Research Signal / Portfolio Separation

- Research Parent: **signal-g02253-c01-b6030e66c9**
- 全期間 Top7 edge vs uniform: **+0.0185**
- 全期間 actual-mass edge vs uniform: **+0.001332**
- 全期間 log edge vs uniform: **-0.016674**
- 全期間 Brier edge vs uniform: **-0.001204**
- 直近120回 log edge vs uniform: **-0.015136**
- Portfolio feedback objective: **-0.1004**
- Signal objective: **-0.0423**
- Research採用: **Portfolio改善だけでは不可。Signal非劣化ゲートも必須**

## Historical Replay Accuracy

- 評価回数: **598回** (101〜698)
- Top7平均本数字一致: **1.3712** / random **1.3243**
- Top7近似両側p: **0.225217** / 判定 **not_confirmed**
- 5口平均最大一致: **2.2508** / random **2.4245**
- 5口平均score差 vs random: **-0.1884**
- 3個以上一致券あり: **36.8%** / random **42.9%**
- 4個以上一致券あり: **7.2%** / random **6.8%**
- 何らかの等級当選があった回: **16.56%**
- 用途: **過去回の精度確認専用。v4 Champion昇格の未来OOS証拠には使用しない**

## Historical Reconciliation

- 独立再照合: **598回 / 2990口**
- 当選口数: **126口** (4.214%)
- 参考購入額: **897,000円**
- 公表当選額ベース参考払戻: **174,900円**
- 参考回収率: **19.50%**
- 予測側実績とloto7.csvの不一致: **0件**

## Nested Champion / Research / Random

- Nested評価回数: **120回** (579〜698)
- 平均score Champion / Research / Random: **2.5505 / 2.6283 / 2.7669**
- Research差 vs Champion: **+0.0778** (95% CI -0.1032〜+0.2508)
- Research差 vs Random: **-0.1385** (95% CI -0.3602〜+0.0829)
- Research勝率 vs Champion / Random: **41.7% / 34.2%**
- 選択方法: **各対象回より前の成績のみで事前定義モデルから選択**

## Formal Challenger

- Formal Challenger: **global-g00001-c01-2ac3662ad1**
- block id: **36d2ec03cdf5da70**
- strict block index: **1**
- block開始対象回: **第692回**
- trusted Future OOS: **6/8回**
- family weight: **0.50000000**
- 必要raw e-value: **40.00**
- 現在の凍結対象回: **第699回**
- Promotion候補数: **1**
- ポリシー: **同一Challengerを8 trusted drawsまで固定し、Champion・事前凍結Random・32-member geometry-matched permutation ensembleの全てに勝つことを要求**

## Strict Future OOS Governance

- ガバナンス版: **strict-oos-governance-v1**
- Matched null版: **matched-permutation-null-v1**
- 凍結済みshadow対象回: **第699回**
- Promotion対象shadow候補数: **1**
- 最終OOS採点回: **698**
- 累積Champion昇格数: **0**
- Uniform Random凍結: **YES** / Matched凍結: **YES**
- strict昇格条件: **8 paired trusted draws / adjusted e-value ≥ 20 / 平均score差 ≥ +0.05 / 勝率 ≥ 55% をChampion・Random・Matched Ensemble(32)の全てで満たす**
- Formal OOS候補: **global-g00001-c01-2ac3662ad1**
- Champion比較 trusted: **6回** / Random比較 trusted: **6回** / Matched比較 trusted: **6回**
- 平均score差 vs Champion / Random / Matched: **-0.2350 / -0.7317 / -0.3200**
- 勝率 vs Champion / Random / Matched: **33.3% / 33.3% / 50.0%**
- raw e-value vs Champion: **0.9310**
- raw e-value vs Random: **0.8022**
- raw e-value vs Matched: **0.8800**
- family-adjusted intersection e-value: **0.4011** / threshold **20.0000**
- 現block必要raw e-value: **40.00**
- Random reference valid: **YES**
- Matched reference valid: **YES**

## Matched Permutation Ensemble

- Ensemble版: **matched-permutation-ensemble-v1**
- Ensemble size: **32**
- Promotionで使用: **YES**
- 第699回事前凍結: **YES**
- Ensemble凍結日時(JST): **2026-10-10T01:21:46+09:00**
- member 0（旧single comparator）凍結日時(JST): **2026-10-10T01:21:46+09:00**
- Null構造: **32個の共通数字ラベル置換。各memberは5口のticket overlap / union coverage / portfolio geometryを元Challengerと同一に保持**
- 集約方法: **32 memberのportfolio score平均を1回のMatched Ensemble基準scoreとして使用**
- 旧single Matched: **監査・telemetry用として保持。Production昇格のMatchedゲートはEnsemble平均を使用**
- Ensemble trusted OOS: **6/8回**
- 平均score差 vs Matched Ensemble: **-0.2569**
- 勝率 vs Matched Ensemble: **33.3%**
- raw e-value vs Matched Ensemble: **0.9250**
- family-adjusted intersection e-value: **0.4011** / threshold **20.0000**
- Holdout Ensemble進捗: **6/26 trusted draws**
- Holdout平均score差 vs Matched Ensemble: **-0.2569**
- Holdout勝率 vs Matched Ensemble: **33.3%**
- Holdout e-value vs Matched Ensemble: **0.9250**
- Holdout Ensemble凍結: **YES**

### Ensemble Rank Diagnostics

- Rank診断版: **matched-ensemble-rank-diagnostics-v1**
- 定義: **percentileはnull内mid-rank、MC p=(1 + #null score ≥ Challenger score)/(32 + 1)**
- Rank診断用途: **diagnostic only（Production昇格判定には未使用。sequential e-processを維持）**
- 単回Monte-Carlo permutation p最小値: **0.0303** (= 1/33)
- Rank診断 trusted OOS: **6/8回**
- 直近(第698回) percentile / MC p: **46.88% / 0.5758**
- 直近 observed+null rank: **18.0/33位相当** (null below/equal/above = 14/2/16)
- trusted平均 percentile / 単回MC p平均: **54.43% / 0.4899**
- Holdout Rank診断: **6/26 trusted draws**
- Holdout直近(第698回) percentile / MC p / rank: **46.88% / 0.5758 / 18.0/33位相当**
- Holdout平均 percentile / 単回MC p平均: **54.43% / 0.4899**

### Ensemble Score Vector Audit

- Score vector監査版: **matched-ensemble-score-vector-audit-v1**
- Hash: **sha256**
- canonical float: **.17g binary64 round-trip decimal string**
- 用途: **diagnostic only。Promotion e-process / 閾値は変更しない**
- Formal 32-member reference SHA-256事前確定: **YES**
- Formal reference SHA-256: **cc15c9854e7c66bb6b90bd3830d3fef2557e2439752dde8e5755b6ad0dbbe408**
- Holdout 32-member reference SHA-256事前確定: **YES**
- Holdout reference SHA-256: **cc15c9854e7c66bb6b90bd3830d3fef2557e2439752dde8e5755b6ad0dbbe408**
- Formal score vector audit status: **active**
- 直近score vector: **第698回 / SHA-256 c1dd1a40054ea7f23b8d01d7661277c0d1e85bf5119663dc9cbfda7805513738**
- 直近audit record SHA-256: **dc7b9f58bb88589561ea62237622aa51aaf4445bc6354be1841914668c438786**
- 直近rank/p replay一致: **YES**
- Holdout直近score vector SHA-256: **c1dd1a40054ea7f23b8d01d7661277c0d1e85bf5119663dc9cbfda7805513738**
- Holdout直近rank/p replay一致: **YES**

## Fixed Prospective Holdout

- 状態: **active**
- 固定モデル: **global-g00001-c01-2ac3662ad1**
- 進捗: **6/26 trusted draws** / Matched **6/26**
- 現在の事前凍結対象回: **第699回**
- 平均score差 vs Champion / Random / Matched: **-0.2350 / -0.7317 / -0.3200**
- 勝率 vs Champion / Random / Matched: **33.3% / 33.3% / 50.0%**
- e-value vs Champion / Random / Matched: **0.9310 / 0.8022 / 0.8800**
- Matched reference frozen: **YES**
- 用途: **26 trusted draws固定のprospective診断。途中でconfig変更しない**

## Sakura Credential Rotation

- 状態: **pending_external_rotation_verification**
- Verification version: **sakura-credential-rotation-verification-v1**
- Credential generation: **未検証**
- secret値をSTATUS/Gitへ記録: **NO**

## Continuous Runtime

- 最新1回の研究実行時間: **78秒**
- 直近20回平均: **78.6秒**
- 累積実測回数: **5848回**
- 実行方式: **終了後、待ち時間なしで次の研究世代へ**
- Git checkpoint: **10世代ごと、または重要イベント発生時**

## Fixed Future OOS Evidence Claim

- Claim status: **not_confirmed_holdout_incomplete**
- 進捗: **6/26 trusted** / Matched **6/26**
- Protocol lock verified: **True**
- vs Random: mean delta **-0.7317** / win **33.3%** / e **0.8022**
- vs Matched Ensemble(32): mean delta **-0.2569** / win **33.3%** / e **0.9250**
- 26/26完了前は confirmed を出さない。
