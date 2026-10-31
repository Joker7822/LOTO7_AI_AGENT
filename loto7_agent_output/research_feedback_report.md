# Research Winner Full-History Replay Feedback

- generation: **5690**
- provisional winner: **evo-g05690-c01-f5aa079e35**
- incumbent research parent: **signal-g05627-c01-1e9e34f825**
- accepted research parent: **signal-g05627-c01-1e9e34f825**
- candidate accepted: **NO**
- replay cache used: **NO**
- 用途: **Research探索の親選択専用。Production昇格証拠には使用しない**

| 指標 | Candidate | Incumbent |
|---|---:|---:|
| feedback objective | 0.0119 | -0.0483 |
| full score Δ vs random | +0.0067 | +0.1365 |
| 120 score Δ vs random | +0.0006 | -0.1274 |
| 60 score Δ vs random | -0.0112 | -0.2209 |
| 30 score Δ vs random | +0.1154 | -0.0729 |

- objective gain: **+0.0601**
- checks: `{"full_max_hits_not_regressed": false, "objective_improves": true, "recent120_score_not_regressed": true}`

> 最新モデルを過去へ再適用した結果はselection leakageを含み得るため、独立精度とは扱いません。未来OOSガバナンスは変更しません。
