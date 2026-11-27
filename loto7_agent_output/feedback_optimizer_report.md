# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **6864**
- incumbent: **signal-g06845-c01-6183c9b064**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **+0.2363**
- incumbent signal objective: **-0.0459**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g06864-c01-0c28feae14: portfolio gain **-0.1662** / signal **-0.0610** / accepted **NO**
- feedback-g06864-c02-0af9e3bcd4: portfolio gain **-0.2752** / signal **-0.2967** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
