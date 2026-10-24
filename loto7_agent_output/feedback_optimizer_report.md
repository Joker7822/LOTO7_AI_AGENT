# Full-History Feedback Optimizer — Signal / Portfolio Separated

- generation: **5199**
- incumbent: **signal-g05198-c01-4cb45d5a7b**
- trials: **2**
- accepted: **なし**
- incumbent portfolio objective: **+0.0728**
- incumbent signal objective: **-0.0398**
- eta探索範囲: **0.1〜6.0**
- overlap_penalty探索範囲: **0.25〜2.0**
- Production昇格証拠: **使用しない**

- feedback-g05199-c01-5bc7cd5aa3: portfolio gain **+0.0096** / signal **-0.0874** / accepted **NO**
- feedback-g05199-c02-5a8f3dce4f: portfolio gain **-0.0888** / signal **-0.2151** / accepted **NO**

> 5口分散で最大一致だけを上げる候補を防ぐため、確率分布そのもののSignalを別ゲートで評価します。
> このoptimizerは過去データへの研究最適化です。独立精度の証明は未来OOSのみです。
