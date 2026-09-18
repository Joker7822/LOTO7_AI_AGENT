# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **3661**
- incumbent: **signal-g02253-c01-b6030e66c9**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **-0.1142**
- incumbent signal objective: **-0.0417**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g03661-c01-1b67491747: portfolio gain **+0.2059** / signal **-0.0669** / accepted **NO**
- feedback-g03661-c02-5b738287a6: portfolio gain **+0.0733** / signal **-0.2071** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
