# LOTO7 AI Agent Status

- 更新日時 (JST): **2026-10-31T07:55:41+09:00**
- 最新取得回: **第701回 / 2026-10-30**
- 最新Production対象: **第702回（未発行）**
- 未照合予測: **0口**
- モデル: **baseline-5fdb8dc2ad**
- データSHA256: `fa6ee78c6350e9b979597107a8650dae16399f91fba0d1c22149d4717e3116d6`
- ソース検証: **verified_two_result_sources**
- 取得状態: **ok**

> Productionの凍結は金曜13:00〜15:00 JSTのProduction publisher系統のみが行います。通常checkpointは既存の凍結台帳を照合・表示するだけです。

## Continuous Research v4

- 研究世代: **5588**
- Production Champion: **baseline-5fdb8dc2ad**
- 最新Research Winner: **signal-g05281-c01-55a70e0b94**
- 候補プール: **16モデル**
- 累積研究評価数: **39115**
- 過去データの研究スコアから本番昇格: **無効（禁止）**
- 現在ソース検証: **verified_two_result_sources**
- 本番昇格に利用可能なソース: **YES**

## Research Signal / Portfolio Separation

- Signal分離評価: **初回再評価待ち**

## Historical Replay Accuracy

- 評価回数: **601回** (101〜701)
- Top7平均本数字一致: **1.3694** / random **1.3243**
- Top7近似両側p: **0.242894** / 判定 **not_confirmed**
- 5口平均最大一致: **2.2496** / random **2.4246**
- 5口平均score差 vs random: **-0.1905**
- 3個以上一致券あり: **36.8%** / random **42.9%**
- 4個以上一致券あり: **7.2%** / random **6.8%**
- 何らかの等級当選があった回: **16.64%**
- 用途: **過去回の精度確認専用。v4 Champion昇格の未来OOS証拠には使用しない**

## Historical Reconciliation

- 独立再照合: **601回 / 3005口**
- 当選口数: **127口** (4.226%)
- 参考購入額: **901,500円**
- 公表当選額ベース参考払戻: **175,900円**
- 参考回収率: **19.51%**
- 予測側実績とloto7.csvの不一致: **0件**

## Nested Champion / Research / Random

- Nested評価回数: **120回** (582〜701)
- 平均score Champion / Research / Random: **2.5500 / 2.6311 / 2.7693**
- Research差 vs Champion: **+0.0811** (95% CI -0.0993〜+0.2603)
- Research差 vs Random: **-0.1382** (95% CI -0.3635〜+0.0893)
- Research勝率 vs Champion / Random: **41.7% / 35.0%**
- 選択方法: **各対象回より前の成績のみで事前定義モデルから選択**

## Formal Challenger

- Formal Challenger: **evo-g04766-c01-a63936bd65**
- block id: **e48bc9ec5d6c52c5**
- strict block index: **2**
- block開始対象回: **第702回**
- trusted Future OOS: **0/8回**
- family weight: **0.16666667**
- 必要raw e-value: **120.00**
- 現在の凍結対象回: **第702回**
- Promotion候補数: **1**
- ポリシー: **同一Challengerを8 trusted drawsまで固定し、Champion・事前凍結Random・32-member geometry-matched permutation ensembleの全てに勝つことを要求**

## Strict Future OOS Governance

- ガバナンス版: **strict-oos-governance-v1**
- Matched null版: **matched-permutation-null-v1**
- 凍結済みshadow対象回: **第702回**
- Promotion対象shadow候補数: **1**
- 最終OOS採点回: **701**
- 累積Champion昇格数: **0**
- Uniform Random凍結: **YES** / Matched凍結: **YES**
- strict昇格条件: **8 paired trusted draws / adjusted e-value ≥ 20 / 平均score差 ≥ +0.05 / 勝率 ≥ 55% をChampion・Random・Matched Ensemble(32)の全てで満たす**
- Formal OOS証拠: **まだ蓄積なし**

## Matched Permutation Ensemble

- Ensemble版: **matched-permutation-ensemble-v1**
- Ensemble size: **32**
- Promotionで使用: **YES**
- 第702回事前凍結: **YES**
- Ensemble凍結日時(JST): **2026-10-31T00:28:28+09:00**
- member 0（旧single comparator）凍結日時(JST): **2026-10-31T00:28:28+09:00**
- Null構造: **32個の共通数字ラベル置換。各memberは5口のticket overlap / union coverage / portfolio geometryを元Challengerと同一に保持**
- 集約方法: **32 memberのportfolio score平均を1回のMatched Ensemble基準scoreとして使用**
- 旧single Matched: **監査・telemetry用として保持。Production昇格のMatchedゲートはEnsemble平均を使用**
- Ensemble trusted OOS: **0/8回**
- 平均score差 vs Matched Ensemble: **+0.0000**
- 勝率 vs Matched Ensemble: **0.0%**
- raw e-value vs Matched Ensemble: **1.0000**
- family-adjusted intersection e-value: **0.0000** / threshold **20.0000**
- Holdout Ensemble進捗: **8/26 trusted draws**
- Holdout平均score差 vs Matched Ensemble: **-0.1248**
- Holdout勝率 vs Matched Ensemble: **37.5%**
- Holdout e-value vs Matched Ensemble: **0.9459**
- Holdout Ensemble凍結: **YES**

### Ensemble Rank Diagnostics

- Rank診断版: **matched-ensemble-rank-diagnostics-v1**
- 定義: **percentileはnull内mid-rank、MC p=(1 + #null score ≥ Challenger score)/(32 + 1)**
- Rank診断用途: **diagnostic only（Production昇格判定には未使用。sequential e-processを維持）**
- 単回Monte-Carlo permutation p最小値: **0.0303** (= 1/33)
- Rank診断 trusted OOS: **0/8回**
- 直近 percentile / MC p / rank: **未採点**
- Holdout Rank診断: **8/26 trusted draws**
- Holdout直近(第701回) percentile / MC p / rank: **45.31% / 0.6061 / 18.5/33位相当**
- Holdout平均 percentile / 単回MC p平均: **56.45% / 0.4773**

### Ensemble Score Vector Audit

- Score vector監査版: **matched-ensemble-score-vector-audit-v1**
- Hash: **sha256**
- canonical float: **.17g binary64 round-trip decimal string**
- 用途: **diagnostic only。Promotion e-process / 閾値は変更しない**
- Formal 32-member reference SHA-256事前確定: **YES**
- Formal reference SHA-256: **12366a10449d454c594d1558c4b1542eee2496c4415230b4a77e51384f030e68**
- Holdout 32-member reference SHA-256事前確定: **YES**
- Holdout reference SHA-256: **81b94ba6e700b374ee9a6e8d79d27100591c258be0df6a908cbdc5eafa9d5a27**
- Formal score vector audit status: **active**
- 直近score vector / audit record: **未採点**
- Holdout直近score vector SHA-256: **36f8ee04c7eabe7537133cdcb7e9cb975b4eafa8171a3adccbfd940bd4062611**
- Holdout直近rank/p replay一致: **YES**

## Fixed Prospective Holdout

- 状態: **active**
- 固定モデル: **global-g00001-c01-2ac3662ad1**
- 進捗: **8/26 trusted draws** / Matched **8/26**
- 現在の事前凍結対象回: **第702回**
- 平均score差 vs Champion / Random / Matched: **-0.4025 / -0.5437 / -0.1075**
- 勝率 vs Champion / Random / Matched: **37.5% / 37.5% / 50.0%**
- e-value vs Champion / Random / Matched: **0.8454 / 0.7998 / 0.9121**
- Matched reference frozen: **YES**
- 用途: **26 trusted draws固定のprospective診断。途中でconfig変更しない**

## Sakura Credential Rotation

- 状態: **pending_external_rotation_verification**
- Verification version: **sakura-credential-rotation-verification-v1**
- Credential generation: **未検証**
- secret値をSTATUS/Gitへ記録: **NO**

## Continuous Runtime

- 最新1回の研究実行時間: **98秒**
- 直近20回平均: **98.2秒**
- 累積実測回数: **7044回**
- 実行方式: **終了後、待ち時間なしで次の研究世代へ**
- Git checkpoint: **10世代ごと、または重要イベント発生時**

## Fixed Future OOS Evidence Claim

- Claim status: **not_confirmed_holdout_incomplete**
- 進捗: **8/26 trusted** / Matched **8/26**
- Protocol lock verified: **True**
- vs Random: mean delta **-0.5437** / win **37.5%** / e **0.7998**
- vs Matched Ensemble(32): mean delta **-0.1248** / win **37.5%** / e **0.9459**
- 26/26完了前は confirmed を出さない。
