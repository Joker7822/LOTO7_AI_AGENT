# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **4252**
- incumbent: **signal-g02253-c01-b6030e66c9**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **-0.1144**
- incumbent signal objective: **-0.0421**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g04252-c01-4f84030445: portfolio gain **-0.0031** / signal **-0.0876** / accepted **NO**
- feedback-g04252-c02-4e36463bac: portfolio gain **+0.0879** / signal **-0.3186** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
