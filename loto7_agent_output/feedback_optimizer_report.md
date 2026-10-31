# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **5642**
- incumbent: **signal-g05627-c01-1e9e34f825**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **-0.0483**
- incumbent signal objective: **-0.0461**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g05642-c01-bbc532ca7d: portfolio gain **+0.0693** / signal **-0.0760** / accepted **NO**
- feedback-g05642-c02-52cf92cfc2: portfolio gain **-0.0405** / signal **-0.2809** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
