# Research Winner Full-History Replay Feedback

- generation: **5789**
- provisional winner: **evo-g05789-c04-0ae1ce41ad**
- incumbent research parent: **signal-g05751-c01-b251534c9e**
- accepted research parent: **signal-g05751-c01-b251534c9e**
- candidate accepted: **NO**
- replay cache used: **NO**
- 用途: **Research探索の親選択専用。Production昇格証拠には使用しない**

| 指標 | Candidate | Incumbent |
|---|---:|---:|
| feedback objective | 0.0302 | 0.0564 |
| full score Δ vs random | +0.1244 | +0.0762 |
| 120 score Δ vs random | +0.0138 | +0.0636 |
| 60 score Δ vs random | -0.0147 | +0.0383 |
| 30 score Δ vs random | -0.1522 | -0.0019 |

- objective gain: **-0.0262**
- checks: `{"full_max_hits_not_regressed": true, "objective_improves": false, "recent120_score_not_regressed": false}`

> 最新モデルを過去へ再適用した結果はselection leakageを含み得るため、独立精度とは扱いません。未来OOSガバナンスは変更しません。
