# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **1104**
- incumbent: **feedback-g00625-c01-1bd218e77b**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **+0.3093**
- incumbent signal objective: **-0.0604**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g01104-c01-52a5d3ecb9: portfolio gain **-0.1733** / signal **-0.0580** / accepted **NO**
- feedback-g01104-c02-bac6d7204b: portfolio gain **-0.3624** / signal **-0.1595** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
