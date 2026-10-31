# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **5672**
- incumbent: **signal-g05627-c01-1e9e34f825**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **-0.0483**
- incumbent signal objective: **-0.0461**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g05672-c01-087dbf56d0: portfolio gain **+0.2163** / signal **-0.0586** / accepted **NO**
- feedback-g05672-c02-35971e3f2e: portfolio gain **-0.0129** / signal **-0.3153** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
