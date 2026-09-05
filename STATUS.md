# LOTO7 AI Agent Status

- 更新日時 (JST): **2026-09-06T04:34:45+09:00**
- 最新取得回: **第693回 / 2026-09-04**
- 最新Production対象: **第694回（未発行）**
- 未照合予測: **0口**
- モデル: **baseline-5fdb8dc2ad**
- データSHA256: `0fdce483829f37c88226c3d0ebeb0321bec34ed144afd986af5f81a8fb7347d0`
- ソース検証: **verified_two_result_sources**
- 取得状態: **ok**

> Productionの凍結は金曜15:00 JST publisherのみが行います。通常checkpointは既存の凍結台帳を照合・表示するだけです。

## Continuous Research v4

- 研究世代: **3200**
- Production Champion: **baseline-5fdb8dc2ad**
- 最新Research Winner: **signal-g02253-c01-b6030e66c9**
- 候補プール: **17モデル**
- 累積研究評価数: **22399**
- 過去データの研究スコアから本番昇格: **無効（禁止）**
- 現在ソース検証: **verified_two_result_sources**
- 本番昇格に利用可能なソース: **YES**

## Research Signal / Portfolio Separation

- Research Parent: **signal-g02253-c01-b6030e66c9**
- 全期間 Top7 edge vs uniform: **+0.0180**
- 全期間 actual-mass edge vs uniform: **+0.001330**
- 全期間 log edge vs uniform: **-0.016637**
- 全期間 Brier edge vs uniform: **-0.001193**
- 直近120回 log edge vs uniform: **-0.014363**
- Portfolio feedback objective: **-0.1157**
- Signal objective: **-0.0420**
- Research採用: **Portfolio改善だけでは不可。Signal非劣化ゲートも必須**

## Historical Replay Accuracy

- 評価回数: **593回** (101〜693)
- Top7平均本数字一致: **1.3727** / random **1.3243**
- Top7近似両側p: **0.213184** / 判定 **not_confirmed**
- 5口平均最大一致: **2.2513** / random **2.4258**
- 5口平均score差 vs random: **-0.1896**
- 3個以上一致券あり: **36.8%** / random **42.9%**
- 4個以上一致券あり: **7.3%** / random **6.8%**
- 何らかの等級当選があった回: **16.36%**
- 用途: **過去回の精度確認専用。v4 Champion昇格の未来OOS証拠には使用しない**

## Historical Reconciliation

- 独立再照合: **593回 / 2965口**
- 当選口数: **123口** (4.148%)
- 参考購入額: **889,500円**
- 公表当選額ベース参考払戻: **172,000円**
- 参考回収率: **19.34%**
- 予測側実績とloto7.csvの不一致: **0件**

## Nested Champion / Research / Random

- Nested評価回数: **120回** (574〜693)
- 平均score Champion / Research / Random: **2.5479 / 2.6813 / 2.7614**
- Research差 vs Champion: **+0.1334** (95% CI -0.0532〜+0.3225)
- Research差 vs Random: **-0.0801** (95% CI -0.3045〜+0.1481)
- Research勝率 vs Champion / Random: **44.2% / 35.8%**
- 選択方法: **各対象回より前の成績のみで事前定義モデルから選択**

## Formal Challenger

- Formal Challenger: **global-g00001-c01-2ac3662ad1**
- block id: **36d2ec03cdf5da70**
- strict block index: **1**
- block開始対象回: **第692回**
- trusted Future OOS: **1/8回**
- family weight: **0.50000000**
- 必要raw e-value: **40.00**
- 現在の凍結対象回: **第694回**
- Promotion候補数: **1**
- ポリシー: **同一Challengerを8 trusted drawsまで固定し、Champion・事前凍結Random・32-member geometry-matched permutation ensembleの全てに勝つことを要求**

## Strict Future OOS Governance

- ガバナンス版: **strict-oos-governance-v1**
- Matched null版: **matched-permutation-null-v1**
- 凍結済みshadow対象回: **第694回**
- Promotion対象shadow候補数: **1**
- 最終OOS採点回: **693**
- 累積Champion昇格数: **0**
- Uniform Random凍結: **YES** / Matched凍結: **YES**
- strict昇格条件: **8 paired trusted draws / adjusted e-value ≥ 20 / 平均score差 ≥ +0.05 / 勝率 ≥ 55% をChampion・Random・Matched Ensemble(32)の全てで満たす**
- Formal OOS候補: **global-g00001-c01-2ac3662ad1**
- Champion比較 trusted: **1回** / Random比較 trusted: **1回** / Matched比較 trusted: **1回**
- 平均score差 vs Champion / Random / Matched: **-0.0200 / +0.0200 / +2.4900**
- 勝率 vs Champion / Random / Matched: **0.0% / 100.0% / 100.0%**
- raw e-value vs Champion: **0.9991**
- raw e-value vs Random: **1.0009**
- raw e-value vs Matched: **1.1132**
- family-adjusted intersection e-value: **0.4995** / threshold **20.0000**
- 現block必要raw e-value: **40.00**
- Random reference valid: **YES**
- Matched reference valid: **YES**

## Matched Permutation Ensemble

- Ensemble版: **matched-permutation-ensemble-v1**
- Ensemble size: **32**
- Promotionで使用: **YES**
- 第694回事前凍結: **YES**
- Ensemble凍結日時(JST): **2026-09-04T21:33:21+09:00**
- member 0（旧single comparator）凍結日時(JST): **2026-09-04T21:33:21+09:00**
- Null構造: **32個の共通数字ラベル置換。各memberは5口のticket overlap / union coverage / portfolio geometryを元Challengerと同一に保持**
- 集約方法: **32 memberのportfolio score平均を1回のMatched Ensemble基準scoreとして使用**
- 旧single Matched: **監査・telemetry用として保持。Production昇格のMatchedゲートはEnsemble平均を使用**
- Ensemble trusted OOS: **1/8回**
- 平均score差 vs Matched Ensemble: **+0.9547**
- 勝率 vs Matched Ensemble: **100.0%**
- raw e-value vs Matched Ensemble: **1.0434**
- family-adjusted intersection e-value: **0.4995** / threshold **20.0000**
- Holdout Ensemble進捗: **1/26 trusted draws**
- Holdout平均score差 vs Matched Ensemble: **+0.9547**
- Holdout勝率 vs Matched Ensemble: **100.0%**
- Holdout e-value vs Matched Ensemble: **1.0434**
- Holdout Ensemble凍結: **YES**

### Ensemble Rank Diagnostics

- Rank診断版: **matched-ensemble-rank-diagnostics-v1**
- 定義: **percentileはnull内mid-rank、MC p=(1 + #null score ≥ Challenger score)/(32 + 1)**
- Rank診断用途: **diagnostic only（Production昇格判定には未使用。sequential e-processを維持）**
- 単回Monte-Carlo permutation p最小値: **0.0303** (= 1/33)
- Rank診断 trusted OOS: **1/8回**
- 直近(第693回) percentile / MC p: **81.25% / 0.2121**
- 直近 observed+null rank: **7.0/33位相当** (null below/equal/above = 26/0/6)
- trusted平均 percentile / 単回MC p平均: **81.25% / 0.2121**
- Holdout Rank診断: **1/26 trusted draws**
- Holdout直近(第693回) percentile / MC p / rank: **81.25% / 0.2121 / 7.0/33位相当**
- Holdout平均 percentile / 単回MC p平均: **81.25% / 0.2121**

### Ensemble Score Vector Audit

- Score vector監査版: **matched-ensemble-score-vector-audit-v1**
- Hash: **sha256**
- canonical float: **.17g binary64 round-trip decimal string**
- 用途: **diagnostic only。Promotion e-process / 閾値は変更しない**
- Formal 32-member reference SHA-256事前確定: **YES**
- Formal reference SHA-256: **e5d9ef9815a855334d297c3fd7f1ffb916eb8c62fd6619f2df7d15b22d9582ee**
- Holdout 32-member reference SHA-256事前確定: **YES**
- Holdout reference SHA-256: **e5d9ef9815a855334d297c3fd7f1ffb916eb8c62fd6619f2df7d15b22d9582ee**
- Formal score vector audit status: **active**
- 直近score vector: **第693回 / SHA-256 a88fc7643e87dbd413dab0dd459a267ffbb181a635cdfe1d8603dc3fa6e03ee7**
- 直近audit record SHA-256: **23d152eea54bb502b62cf07aeec76a4356823dfec9c106db14021abb8b65fe8a**
- 直近rank/p replay一致: **YES**
- Holdout直近score vector SHA-256: **a88fc7643e87dbd413dab0dd459a267ffbb181a635cdfe1d8603dc3fa6e03ee7**
- Holdout直近rank/p replay一致: **YES**

## Fixed Prospective Holdout

- 状態: **active**
- 固定モデル: **global-g00001-c01-2ac3662ad1**
- 進捗: **1/26 trusted draws** / Matched **1/26**
- 現在の事前凍結対象回: **第694回**
- 平均score差 vs Champion / Random / Matched: **-0.0200 / +0.0200 / +2.4900**
- 勝率 vs Champion / Random / Matched: **0.0% / 100.0% / 100.0%**
- e-value vs Champion / Random / Matched: **0.9991 / 1.0009 / 1.1132**
- Matched reference frozen: **YES**
- 用途: **26 trusted draws固定のprospective診断。途中でconfig変更しない**

## Continuous Runtime

- 最新1回の研究実行時間: **1529秒**
- 直近20回平均: **1516.5秒**
- 累積実測回数: **4198回**
- 実行方式: **終了後、待ち時間なしで次の研究世代へ**
- Git checkpoint: **10世代ごと、または重要イベント発生時**
