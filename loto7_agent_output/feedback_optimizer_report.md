# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **5130**
- incumbent: **signal-g05129-c01-6cc09a5015**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **+0.0917**
- incumbent signal objective: **-0.0508**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g05130-c01-87badc3d1d: portfolio gain **-0.0461** / signal **-0.0751** / accepted **NO**
- feedback-g05130-c02-20e0781231: portfolio gain **-0.0565** / signal **-0.3067** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
