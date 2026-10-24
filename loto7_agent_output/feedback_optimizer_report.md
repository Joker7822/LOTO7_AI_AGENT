# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **5145**
- incumbent: **signal-g05132-c01-d09ac468ef**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **+0.1635**
- incumbent signal objective: **-0.0506**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g05145-c01-b2ed79c57c: portfolio gain **-0.0708** / signal **-0.0639** / accepted **NO**
- feedback-g05145-c02-8877eee709: portfolio gain **-0.1332** / signal **-0.1347** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
