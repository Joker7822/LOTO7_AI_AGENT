# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **4026**
- incumbent: **signal-g02253-c01-b6030e66c9**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **-0.1219**
- incumbent signal objective: **-0.0419**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g04026-c01-297bd6420a: portfolio gain **+0.0205** / signal **-0.0593** / accepted **NO**
- feedback-g04026-c02-342c0a6144: portfolio gain **+0.1355** / signal **-0.1054** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
