# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **5759**
- incumbent: **signal-g05751-c01-b251534c9e**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **+0.0564**
- incumbent signal objective: **-0.0467**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g05759-c01-a27ed776ab: portfolio gain **+0.0769** / signal **-0.0589** / accepted **NO**
- feedback-g05759-c02-4a1cdb8221: portfolio gain **-0.0131** / signal **-0.1065** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
