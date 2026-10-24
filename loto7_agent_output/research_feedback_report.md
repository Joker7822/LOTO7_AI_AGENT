# Research Winner Full-History Replay Feedback

- generation: **5166**
- provisional winner: **evo-g05166-c03-6dd6c39e24**
- incumbent research parent: **signal-g05155-c01-b7bf1ffa1e**
- accepted research parent: **signal-g05155-c01-b7bf1ffa1e**
- candidate accepted: **NO**
- replay cache used: **NO**
- 用途: **Research探索の親選択専用。Production昇格証拠には使用しない**

| 指標 | Candidate | Incumbent |
|---|---:|---:|
| feedback objective | 0.0185 | 0.0111 |
| full score Δ vs random | +0.0254 | +0.0778 |
| 120 score Δ vs random | +0.0344 | +0.0239 |
| 60 score Δ vs random | +0.0096 | -0.1107 |
| 30 score Δ vs random | -0.0428 | -0.0232 |

- objective gain: **+0.0074**
- checks: `{"full_max_hits_not_regressed": false, "objective_improves": true, "recent120_score_not_regressed": true}`

> 最新モデルを過去へ再適用した結果はselection leakageを含み得るため、独立精度とは扱いません。未来OOSガバナンスは変更しません。
