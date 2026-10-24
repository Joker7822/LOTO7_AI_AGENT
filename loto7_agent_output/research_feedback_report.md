# Research Winner Full-History Replay Feedback

- generation: **5119**
- provisional winner: **evo-g05119-c02-12861fab98**
- incumbent research parent: **signal-g04789-c01-29ccf32ff6**
- accepted research parent: **signal-g04789-c01-29ccf32ff6**
- candidate accepted: **NO**
- replay cache used: **NO**
- 用途: **Research探索の親選択専用。Production昇格証拠には使用しない**

| 指標 | Candidate | Incumbent |
|---|---:|---:|
| feedback objective | 0.0829 | 0.0130 |
| full score Δ vs random | +0.0827 | +0.1315 |
| 120 score Δ vs random | +0.0873 | +0.0293 |
| 60 score Δ vs random | +0.0596 | -0.0169 |
| 30 score Δ vs random | +0.1152 | -0.3992 |

- objective gain: **+0.0700**
- checks: `{"full_max_hits_not_regressed": false, "objective_improves": true, "recent120_score_not_regressed": true}`

> 最新モデルを過去へ再適用した結果はselection leakageを含み得るため、独立精度とは扱いません。未来OOSガバナンスは変更しません。
