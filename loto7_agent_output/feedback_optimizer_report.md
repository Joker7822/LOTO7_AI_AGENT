# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **4398**
- incumbent: **signal-g02253-c01-b6030e66c9**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **-0.1144**
- incumbent signal objective: **-0.0421**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g04398-c01-aaf8c2783b: portfolio gain **-0.0718** / signal **-0.0583** / accepted **NO**
- feedback-g04398-c02-d61a42b602: portfolio gain **+0.2677** / signal **-0.2365** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
