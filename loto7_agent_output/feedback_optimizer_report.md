# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **5166**
- incumbent: **signal-g05155-c01-b7bf1ffa1e**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **+0.0111**
- incumbent signal objective: **-0.0490**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g05166-c01-d1fc490cd6: portfolio gain **+0.0942** / signal **-0.0635** / accepted **NO**
- feedback-g05166-c02-a1ffc1b72d: portfolio gain **-0.0932** / signal **-0.2327** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
