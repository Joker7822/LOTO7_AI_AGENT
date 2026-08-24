# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **2251**
- incumbent: **signal-g02247-c01-b35c6f70ab**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **+0.1127**
- incumbent signal objective: **-0.0440**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g02251-c01-fba2abbd4a: portfolio gain **+0.0170** / signal **-0.0588** / accepted **NO**
- feedback-g02251-c02-0ff20cceeb: portfolio gain **-0.2596** / signal **-0.4216** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
