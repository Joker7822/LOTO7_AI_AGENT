# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **5132**
- incumbent: **signal-g05129-c01-6cc09a5015**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **+0.1252**
- incumbent signal objective: **-0.0524**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g05132-c01-d309917ed3: portfolio gain **-0.0986** / signal **-0.0723** / accepted **NO**
- feedback-g05132-c02-123efbafb7: portfolio gain **-0.1800** / signal **-0.2786** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
