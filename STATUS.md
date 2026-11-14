# LOTO7 AI Agent Status

- 更新日時 (JST): **2026-11-14T13:45:35+09:00**
- 最新取得回: **第703回 / 2026-11-13**
- 最新Production対象: **第704回（未発行）**
- 未照合予測: **0口**
- モデル: **baseline-5fdb8dc2ad+production-disjoint35-layout-v1**
- データSHA256: `ca6c245500134f8d843d0604cf5fe777d8a7c3338fdf287bc71c415beece2960`
- ソース検証: **verified_two_result_sources**
- 取得状態: **ok**

> Productionの凍結は金曜13:00〜15:00 JSTのProduction publisher系統のみが行います。通常checkpointは既存の凍結台帳を照合・表示するだけです。

## Continuous Research v4

- 研究世代: **6491**
- Production Champion: **baseline-5fdb8dc2ad**
- 最新Research Winner: **signal-g05814-c01-a0b6c7d9c2**
- 候補プール: **16モデル**
- 累積研究評価数: **45436**
- 過去データの研究スコアから本番昇格: **無効（禁止）**
- 現在ソース検証: **verified_two_result_sources**
- 本番昇格に利用可能なソース: **YES**

## Research Signal / Portfolio Separation

- Research Parent: **signal-g05814-c01-a0b6c7d9c2**
- 全期間 Top7 edge vs uniform: **+0.0206**
- 全期間 actual-mass edge vs uniform: **+0.001282**
- 全期間 log edge vs uniform: **-0.017989**
- 全期間 Brier edge vs uniform: **-0.001323**
- 直近120回 log edge vs uniform: **-0.017654**
- Portfolio feedback objective: **+0.2527**
- Signal objective: **-0.0464**
- Research採用: **Portfolio改善だけでは不可。Signal非劣化ゲートも必須**

## Historical Replay Accuracy

- 評価回数: **603回** (101〜703)
- Top7平均本数字一致: **1.3648** / random **1.3243**
- Top7近似両側p: **0.292882** / 判定 **not_confirmed**
- 5口平均最大一致: **2.2454** / random **2.4245**
- 5口平均score差 vs random: **-0.1954**
- 3個以上一致券あり: **36.7%** / random **42.9%**
- 4個以上一致券あり: **7.1%** / random **6.8%**
- 何らかの等級当選があった回: **16.58%**
- 用途: **過去回の精度確認専用。v4 Champion昇格の未来OOS証拠には使用しない**

## Historical Reconciliation

- 独立再照合: **603回 / 3015口**
- 当選口数: **127口** (4.212%)
- 参考購入額: **904,500円**
- 公表当選額ベース参考払戻: **175,900円**
- 参考回収率: **19.45%**
- 予測側実績とloto7.csvの不一致: **0件**

## Nested Champion / Research / Random

- Nested評価回数: **120回** (584〜703)
- 平均score Champion / Research / Random: **2.5289 / 2.6223 / 2.7696**
- Research差 vs Champion: **+0.0933** (95% CI -0.0834〜+0.2751)
- Research差 vs Random: **-0.1474** (95% CI -0.3636〜+0.0872)
- Research勝率 vs Champion / Random: **43.3% / 35.0%**
- 選択方法: **各対象回より前の成績のみで事前定義モデルから選択**

## Formal Challenger

- Formal Challenger: **evo-g04766-c01-a63936bd65**
- block id: **e48bc9ec5d6c52c5**
- strict block index: **2**
- block開始対象回: **第702回**
- trusted Future OOS: **2/8回**
- family weight: **0.16666667**
- 必要raw e-value: **120.00**
- 現在の凍結対象回: **第704回**
- Promotion候補数: **1**
- ポリシー: **同一Challengerを8 trusted drawsまで固定し、Champion・事前凍結Random・32-member geometry-matched permutation ensembleの全てに勝つことを要求**

## Strict Future OOS Governance

- ガバナンス版: **strict-oos-governance-v1**
- Matched null版: **matched-permutation-null-v1**
- 凍結済みshadow対象回: **第704回**
- Promotion対象shadow候補数: **1**
- 最終OOS採点回: **703**
- 累積Champion昇格数: **0**
- Uniform Random凍結: **YES** / Matched凍結: **YES**
- strict昇格条件: **8 paired trusted draws / adjusted e-value ≥ 20 / 平均score差 ≥ +0.05 / 勝率 ≥ 55% をChampion・Random・Matched Ensemble(32)の全てで満たす**
- Formal OOS候補: **evo-g04766-c01-a63936bd65**
- Champion比較 trusted: **2回** / Random比較 trusted: **2回** / Matched比較 trusted: **2回**
- 平均score差 vs Champion / Random / Matched: **+0.5200 / -0.0800 / -2.8750**
- 勝率 vs Champion / Random / Matched: **50.0% / 0.0% / 0.0%**
- raw e-value vs Champion: **1.0473**
- raw e-value vs Random: **0.9927**
- raw e-value vs Matched: **0.7619**
- family-adjusted intersection e-value: **0.1467** / threshold **20.0000**
- 現block必要raw e-value: **120.00**
- Random reference valid: **YES**
- Matched reference valid: **YES**

## Matched Permutation Ensemble

- Ensemble版: **matched-permutation-ensemble-v1**
- Ensemble size: **32**
- Promotionで使用: **YES**
- 第704回事前凍結: **YES**
- Ensemble凍結日時(JST): **2026-11-13T21:49:44+09:00**
- member 0（旧single comparator）凍結日時(JST): **2026-11-13T21:49:44+09:00**
- Null構造: **32個の共通数字ラベル置換。各memberは5口のticket overlap / union coverage / portfolio geometryを元Challengerと同一に保持**
- 集約方法: **32 memberのportfolio score平均を1回のMatched Ensemble基準scoreとして使用**
- 旧single Matched: **監査・telemetry用として保持。Production昇格のMatchedゲートはEnsemble平均を使用**
- Ensemble trusted OOS: **2/8回**
- 平均score差 vs Matched Ensemble: **-1.3738**
- 勝率 vs Matched Ensemble: **0.0%**
- raw e-value vs Matched Ensemble: **0.8802**
- family-adjusted intersection e-value: **0.1467** / threshold **20.0000**
- Holdout Ensemble進捗: **10/26 trusted draws**
- Holdout平均score差 vs Matched Ensemble: **-0.2137**
- Holdout勝率 vs Matched Ensemble: **30.0%**
- Holdout e-value vs Matched Ensemble: **0.8989**
- Holdout Ensemble凍結: **YES**

### Ensemble Rank Diagnostics

- Rank診断版: **matched-ensemble-rank-diagnostics-v1**
- 定義: **percentileはnull内mid-rank、MC p=(1 + #null score ≥ Challenger score)/(32 + 1)**
- Rank診断用途: **diagnostic only（Production昇格判定には未使用。sequential e-processを維持）**
- 単回Monte-Carlo permutation p最小値: **0.0303** (= 1/33)
- Rank診断 trusted OOS: **2/8回**
- 直近(第703回) percentile / MC p: **6.25% / 0.9697**
- 直近 observed+null rank: **31.0/33位相当** (null below/equal/above = 1/2/29)
- trusted平均 percentile / 単回MC p平均: **3.12% / 0.9848**
- Holdout Rank診断: **10/26 trusted draws**
- Holdout直近(第703回) percentile / MC p / rank: **12.50% / 0.9091 / 29.0/33位相当**
- Holdout平均 percentile / 単回MC p平均: **48.59% / 0.5545**

### Ensemble Score Vector Audit

- Score vector監査版: **matched-ensemble-score-vector-audit-v1**
- Hash: **sha256**
- canonical float: **.17g binary64 round-trip decimal string**
- 用途: **diagnostic only。Promotion e-process / 閾値は変更しない**
- Formal 32-member reference SHA-256事前確定: **YES**
- Formal reference SHA-256: **812ef1a70fc11ed9edf3223a7659d6a49f81029ba63aa9c6a27d049ca9c37bc5**
- Holdout 32-member reference SHA-256事前確定: **YES**
- Holdout reference SHA-256: **9ffb99824195db90c6811d3d4d99dd0be5fb64ec1e2500dd050a3cf8fb7fc60f**
- Formal score vector audit status: **active**
- 直近score vector: **第703回 / SHA-256 2587145a65ca7170b76f79acbb132251c270c028e2b1544e336a6fecefd56232**
- 直近audit record SHA-256: **65d728802835c191f1b32eee62083e15d0ded6165aa61b2056453e70e119a6ae**
- 直近rank/p replay一致: **YES**
- Holdout直近score vector SHA-256: **15700d55a84b0ee5aac99b2f3a2e649f09b883679d68a4c9f74b6ec694bd4117**
- Holdout直近rank/p replay一致: **YES**

## Fixed Prospective Holdout

- 状態: **active**
- 固定モデル: **global-g00001-c01-2ac3662ad1**
- 進捗: **10/26 trusted draws** / Matched **10/26**
- 現在の事前凍結対象回: **第704回**
- 平均score差 vs Champion / Random / Matched: **-0.1140 / -0.3470 / -0.3840**
- 勝率 vs Champion / Random / Matched: **50.0% / 40.0% / 40.0%**
- e-value vs Champion / Random / Matched: **0.9219 / 0.8285 / 0.7998**
- Matched reference frozen: **YES**
- 用途: **26 trusted draws固定のprospective診断。途中でconfig変更しない**

## Sakura Credential Rotation

- 状態: **pending_external_rotation_verification**
- Verification version: **sakura-credential-rotation-verification-v1**
- Credential generation: **未検証**
- secret値をSTATUS/Gitへ記録: **NO**

## Continuous Runtime

- 最新1回の研究実行時間: **1375秒**
- 直近20回平均: **1426.5秒**
- 累積実測回数: **8095回**
- 実行方式: **終了後、待ち時間なしで次の研究世代へ**
- Git checkpoint: **10世代ごと、または重要イベント発生時**

## Fixed Future OOS Evidence Claim

- Claim status: **not_confirmed_holdout_incomplete**
- 進捗: **10/26 trusted** / Matched **10/26**
- Protocol lock verified: **True**
- Confirmation policy preregistered before first outcome: **False**
- vs Random: mean delta **-0.3470** / win **40.0%** / e **0.8285**
- vs Matched Ensemble(32): mean delta **-0.2137** / win **30.0%** / e **0.8989**
- 26/26完了前は confirmed を出さない。
