# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **5128**
- incumbent: **signal-g05127-c01-f8591bf40d**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **+0.1874**
- incumbent signal objective: **-0.0624**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g05128-c01-33ccc3501a: portfolio gain **-0.1297** / signal **-0.1013** / accepted **NO**
- feedback-g05128-c02-112f1f09c9: portfolio gain **-0.1236** / signal **-0.1350** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
