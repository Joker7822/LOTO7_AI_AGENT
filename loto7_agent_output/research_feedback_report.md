# Research Winner Full-History Replay Feedback

- generation: **5713**
- provisional winner: **evo-g05713-c04-f38aef7a85**
- incumbent research parent: **signal-g05705-c01-0b089f3f09**
- accepted research parent: **signal-g05705-c01-0b089f3f09**
- candidate accepted: **NO**
- replay cache used: **NO**
- 用途: **Research探索の親選択専用。Production昇格証拠には使用しない**

| 指標 | Candidate | Incumbent |
|---|---:|---:|
| feedback objective | 0.0983 | 0.0865 |
| full score Δ vs random | +0.0758 | +0.1860 |
| 120 score Δ vs random | +0.1721 | +0.0174 |
| 60 score Δ vs random | +0.0776 | +0.0251 |
| 30 score Δ vs random | -0.0402 | +0.1031 |

- objective gain: **+0.0118**
- checks: `{"full_max_hits_not_regressed": false, "objective_improves": true, "recent120_score_not_regressed": true}`

> 最新モデルを過去へ再適用した結果はselection leakageを含み得るため、独立精度とは扱いません。未来OOSガバナンスは変更しません。
