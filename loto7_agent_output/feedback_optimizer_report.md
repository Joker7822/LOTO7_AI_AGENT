# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **5176**
- incumbent: **signal-g05175-c01-33535f4f52**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **+0.1128**
- incumbent signal objective: **-0.0403**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g05176-c01-56c7b62970: portfolio gain **-0.0884** / signal **-0.0564** / accepted **NO**
- feedback-g05176-c02-4e29601434: portfolio gain **-0.1747** / signal **-0.3030** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
