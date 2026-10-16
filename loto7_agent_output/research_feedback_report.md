# Research Winner Full-History Replay Feedback

- generation: **4908**
- provisional winner: **evo-g04908-c03-4646519f55**
- incumbent research parent: **signal-g04789-c01-29ccf32ff6**
- accepted research parent: **signal-g04789-c01-29ccf32ff6**
- candidate accepted: **NO**
- replay cache used: **NO**
- 用途: **Research探索の親選択専用。Production昇格証拠には使用しない**

| 指標 | Candidate | Incumbent |
|---|---:|---:|
| feedback objective | 0.0604 | 0.0225 |
| full score Δ vs random | +0.1138 | +0.1330 |
| 120 score Δ vs random | -0.0168 | +0.0389 |
| 60 score Δ vs random | +0.0987 | +0.0014 |
| 30 score Δ vs random | +0.0663 | -0.3797 |

- objective gain: **+0.0379**
- checks: `{"full_max_hits_not_regressed": false, "objective_improves": true, "recent120_score_not_regressed": false}`

> 最新モデルを過去へ再適用した結果はselection leakageを含み得るため、独立精度とは扱いません。未来OOSガバナンスは変更しません。
