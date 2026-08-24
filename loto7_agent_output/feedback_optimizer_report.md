# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **2248**
- incumbent: **signal-g02247-c01-b35c6f70ab**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **+0.1484**
- incumbent signal objective: **-0.0460**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g02248-c01-f002dadf39: portfolio gain **+0.1407** / signal **-0.0605** / accepted **NO**
- feedback-g02248-c02-4ed44d01de: portfolio gain **-0.1764** / signal **-0.1601** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
