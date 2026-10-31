# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **5706**
- incumbent: **signal-g05705-c01-0b089f3f09**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **+0.1450**
- incumbent signal objective: **-0.0607**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g05706-c01-7ae4671b9a: portfolio gain **-0.0908** / signal **-0.1038** / accepted **NO**
- feedback-g05706-c02-21c463e863: portfolio gain **-0.1155** / signal **-0.0805** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
