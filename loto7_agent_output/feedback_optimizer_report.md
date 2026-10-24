# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **5192**
- incumbent: **signal-g05175-c01-33535f4f52**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **+0.1252**
- incumbent signal objective: **-0.0430**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g05192-c01-c42ec0cc8c: portfolio gain **-0.2279** / signal **-0.0883** / accepted **NO**
- feedback-g05192-c02-5f7a8c99f4: portfolio gain **-0.0310** / signal **-0.1888** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
