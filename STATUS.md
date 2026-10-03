# LOTO7 AI Agent Status

- 更新日時 (JST): **2026-10-03T23:58:41+09:00**
- 最新取得回: **第697回 / 2026-10-02**
- 最新Production対象: **第698回（未発行）**
- 未照合予測: **0口**
- モデル: **baseline-5fdb8dc2ad**
- データSHA256: `3bc3486fec4198fc19036eb8f8482303ca90aef5cc6bf093a78011dc8dcbee5f`
- ソース検証: **verified_two_result_sources**
- 取得状態: **ok**

> Productionの凍結は金曜13:00〜15:00 JSTのProduction publisher系統のみが行います。通常checkpointは既存の凍結台帳を照合・表示するだけです。

## Continuous Research v4

- 研究世代: **4404**
- Production Champion: **baseline-5fdb8dc2ad**
- 最新Research Winner: **signal-g02253-c01-b6030e66c9**
- 候補プール: **17モデル**
- 累積研究評価数: **30827**
- 過去データの研究スコアから本番昇格: **無効（禁止）**
- 現在ソース検証: **verified_two_result_sources**
- 本番昇格に利用可能なソース: **YES**

## Research Signal / Portfolio Separation

- Research Parent: **signal-g02253-c01-b6030e66c9**
- 全期間 Top7 edge vs uniform: **+0.0191**
- 全期間 actual-mass edge vs uniform: **+0.001338**
- 全期間 log edge vs uniform: **-0.016665**
- 全期間 Brier edge vs uniform: **-0.001202**
- 直近120回 log edge vs uniform: **-0.014926**
- Portfolio feedback objective: **-0.1144**
- Signal objective: **-0.0421**
- Research採用: **Portfolio改善だけでは不可。Signal非劣化ゲートも必須**

## Historical Replay Accuracy

- 評価回数: **597回** (101〜697)
- Top7平均本数字一致: **1.3719** / random **1.3243**
- Top7近似両側p: **0.219515** / 判定 **not_confirmed**
- 5口平均最大一致: **2.2513** / random **2.4247**
- 5口平均score差 vs random: **-0.1880**
- 3個以上一致券あり: **36.9%** / random **42.9%**
- 4個以上一致券あり: **7.2%** / random **6.8%**
- 何らかの等級当選があった回: **16.58%**
- 用途: **過去回の精度確認専用。v4 Champion昇格の未来OOS証拠には使用しない**

## Historical Reconciliation

- 独立再照合: **597回 / 2985口**
- 当選口数: **126口** (4.221%)
- 参考購入額: **895,500円**
- 公表当選額ベース参考払戻: **174,900円**
- 参考回収率: **19.53%**
- 予測側実績とloto7.csvの不一致: **0件**

## Nested Champion / Research / Random

- Nested評価回数: **120回** (578〜697)
- 平均score Champion / Research / Random: **2.5393 / 2.6545 / 2.7667**
- Research差 vs Champion: **+0.1153** (95% CI -0.0673〜+0.3003)
- Research差 vs Random: **-0.1122** (95% CI -0.3306〜+0.1141)
- Research勝率 vs Champion / Random: **42.5% / 35.0%**
- 選択方法: **各対象回より前の成績のみで事前定義モデルから選択**

## Formal Challenger

- Formal Challenger: **global-g00001-c01-2ac3662ad1**
- block id: **36d2ec03cdf5da70**
- strict block index: **1**
- block開始対象回: **第692回**
- trusted Future OOS: **5/8回**
- family weight: **0.50000000**
- 必要raw e-value: **40.00**
- 現在の凍結対象回: **第698回**
- Promotion候補数: **1**
- ポリシー: **同一Challengerを8 trusted drawsまで固定し、Champion・事前凍結Random・32-member geometry-matched permutation ensembleの全てに勝つことを要求**

## Strict Future OOS Governance

- ガバナンス版: **strict-oos-governance-v1**
- Matched null版: **matched-permutation-null-v1**
- 凍結済みshadow対象回: **第698回**
- Promotion対象shadow候補数: **1**
- 最終OOS採点回: **697**
- 累積Champion昇格数: **0**
- Uniform Random凍結: **YES** / Matched凍結: **YES**
- strict昇格条件: **8 paired trusted draws / adjusted e-value ≥ 20 / 平均score差 ≥ +0.05 / 勝率 ≥ 55% をChampion・Random・Matched Ensemble(32)の全てで満たす**
- Formal OOS候補: **global-g00001-c01-2ac3662ad1**
- Champion比較 trusted: **5回** / Random比較 trusted: **5回** / Matched比較 trusted: **5回**
- 平均score差 vs Champion / Random / Matched: **-0.0080 / -0.6080 / +0.2560**
- 勝率 vs Champion / Random / Matched: **40.0% / 40.0% / 60.0%**
- raw e-value vs Champion: **0.9926**
- raw e-value vs Random: **0.8508**
- raw e-value vs Matched: **1.0308**
- family-adjusted intersection e-value: **0.4254** / threshold **20.0000**
- 現block必要raw e-value: **40.00**
- Random reference valid: **YES**
- Matched reference valid: **YES**

## Matched Permutation Ensemble

- Ensemble版: **matched-permutation-ensemble-v1**
- Ensemble size: **32**
- Promotionで使用: **YES**
- 第698回事前凍結: **YES**
- Ensemble凍結日時(JST): **2026-10-03T00:58:19+09:00**
- member 0（旧single comparator）凍結日時(JST): **2026-10-03T00:58:19+09:00**
- Null構造: **32個の共通数字ラベル置換。各memberは5口のticket overlap / union coverage / portfolio geometryを元Challengerと同一に保持**
- 集約方法: **32 memberのportfolio score平均を1回のMatched Ensemble基準scoreとして使用**
- 旧single Matched: **監査・telemetry用として保持。Production昇格のMatchedゲートはEnsemble平均を使用**
- Ensemble trusted OOS: **5/8回**
- 平均score差 vs Matched Ensemble: **-0.1186**
- 勝率 vs Matched Ensemble: **40.0%**
- raw e-value vs Matched Ensemble: **0.9660**
- family-adjusted intersection e-value: **0.4254** / threshold **20.0000**
- Holdout Ensemble進捗: **5/26 trusted draws**
- Holdout平均score差 vs Matched Ensemble: **-0.1186**
- Holdout勝率 vs Matched Ensemble: **40.0%**
- Holdout e-value vs Matched Ensemble: **0.9660**
- Holdout Ensemble凍結: **YES**

### Ensemble Rank Diagnostics

- Rank診断版: **matched-ensemble-rank-diagnostics-v1**
- 定義: **percentileはnull内mid-rank、MC p=(1 + #null score ≥ Challenger score)/(32 + 1)**
- Rank診断用途: **diagnostic only（Production昇格判定には未使用。sequential e-processを維持）**
- 単回Monte-Carlo permutation p最小値: **0.0303** (= 1/33)
- Rank診断 trusted OOS: **5/8回**
- 直近(第697回) percentile / MC p: **48.44% / 0.5758**
- 直近 observed+null rank: **17.5/33位相当** (null below/equal/above = 14/3/15)
- trusted平均 percentile / 単回MC p平均: **55.94% / 0.4727**
- Holdout Rank診断: **5/26 trusted draws**
- Holdout直近(第697回) percentile / MC p / rank: **48.44% / 0.5758 / 17.5/33位相当**
- Holdout平均 percentile / 単回MC p平均: **55.94% / 0.4727**

### Ensemble Score Vector Audit

- Score vector監査版: **matched-ensemble-score-vector-audit-v1**
- Hash: **sha256**
- canonical float: **.17g binary64 round-trip decimal string**
- 用途: **diagnostic only。Promotion e-process / 閾値は変更しない**
- Formal 32-member reference SHA-256事前確定: **YES**
- Formal reference SHA-256: **da6de53f9d8209e33839e0a350631e5e90ce22f233fef7287967fa18f49adea3**
- Holdout 32-member reference SHA-256事前確定: **YES**
- Holdout reference SHA-256: **da6de53f9d8209e33839e0a350631e5e90ce22f233fef7287967fa18f49adea3**
- Formal score vector audit status: **active**
- 直近score vector: **第697回 / SHA-256 55241584e0e8307a4463b0bedaeece3e33bebb986507c6bc15be8952f8a222bd**
- 直近audit record SHA-256: **d4b186a148e662bc8acaab27f7f52327b14494652bd284da6ae6b493db46c7c6**
- 直近rank/p replay一致: **YES**
- Holdout直近score vector SHA-256: **55241584e0e8307a4463b0bedaeece3e33bebb986507c6bc15be8952f8a222bd**
- Holdout直近rank/p replay一致: **YES**

## Fixed Prospective Holdout

- 状態: **active**
- 固定モデル: **global-g00001-c01-2ac3662ad1**
- 進捗: **5/26 trusted draws** / Matched **5/26**
- 現在の事前凍結対象回: **第698回**
- 平均score差 vs Champion / Random / Matched: **-0.0080 / -0.6080 / +0.2560**
- 勝率 vs Champion / Random / Matched: **40.0% / 40.0% / 60.0%**
- e-value vs Champion / Random / Matched: **0.9926 / 0.8508 / 1.0308**
- Matched reference frozen: **YES**
- 用途: **26 trusted draws固定のprospective診断。途中でconfig変更しない**

## Sakura Credential Rotation

- 状態: **pending_external_rotation_verification**
- Verification version: **sakura-credential-rotation-verification-v1**
- Credential generation: **未検証**
- secret値をSTATUS/Gitへ記録: **NO**

## Continuous Runtime

- 最新1回の研究実行時間: **1481秒**
- 直近20回平均: **1301.9秒**
- 累積実測回数: **5642回**
- 実行方式: **終了後、待ち時間なしで次の研究世代へ**
- Git checkpoint: **10世代ごと、または重要イベント発生時**

## Fixed Future OOS Evidence Claim

- Claim status: **not_confirmed_holdout_incomplete**
- 進捗: **5/26 trusted** / Matched **5/26**
- Protocol lock verified: **True**
- vs Random: mean delta **-0.6080** / win **40.0%** / e **0.8508**
- vs Matched Ensemble(32): mean delta **-0.1186** / win **40.0%** / e **0.9660**
- 26/26完了前は confirmed を出さない。
