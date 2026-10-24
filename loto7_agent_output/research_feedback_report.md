# Research Winner Full-History Replay Feedback

- generation: **5278**
- provisional winner: **evo-g05278-c03-92be8be934**
- incumbent research parent: **signal-g05276-c01-af711eb9cb**
- accepted research parent: **signal-g05276-c01-af711eb9cb**
- candidate accepted: **NO**
- replay cache used: **NO**
- 用途: **Research探索の親選択専用。Production昇格証拠には使用しない**

| 指標 | Candidate | Incumbent |
|---|---:|---:|
| feedback objective | 0.1047 | 0.0915 |
| full score Δ vs random | +0.1474 | +0.1671 |
| 120 score Δ vs random | +0.1189 | +0.1032 |
| 60 score Δ vs random | +0.0651 | -0.0247 |
| 30 score Δ vs random | -0.0152 | +0.0182 |

- objective gain: **+0.0132**
- checks: `{"full_max_hits_not_regressed": false, "objective_improves": true, "recent120_score_not_regressed": true}`

> 最新モデルを過去へ再適用した結果はselection leakageを含み得るため、独立精度とは扱いません。未来OOSガバナンスは変更しません。
