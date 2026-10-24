# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **5146**
- incumbent: **signal-g05132-c01-d09ac468ef**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **+0.1635**
- incumbent signal objective: **-0.0506**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g05146-c01-091d87c798: portfolio gain **-0.0606** / signal **-0.0749** / accepted **NO**
- feedback-g05146-c02-9b5a7aafae: portfolio gain **-0.1029** / signal **-0.1658** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
