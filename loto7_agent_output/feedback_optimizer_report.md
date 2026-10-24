# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **5239**
- incumbent: **signal-g05198-c01-4cb45d5a7b**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **+0.0005**
- incumbent signal objective: **-0.0426**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g05239-c01-8fbac30339: portfolio gain **+0.0111** / signal **-0.0566** / accepted **NO**
- feedback-g05239-c02-0e4cf17a0d: portfolio gain **-0.1965** / signal **-0.3597** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
