# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **5619**
- incumbent: **signal-g05618-c01-7d2976e19d**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **+0.1524**
- incumbent signal objective: **-0.0715**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g05619-c01-6132f6168f: portfolio gain **-0.0967** / signal **-0.0774** / accepted **NO**
- feedback-g05619-c02-7257516102: portfolio gain **+0.0270** / signal **-0.0658** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
