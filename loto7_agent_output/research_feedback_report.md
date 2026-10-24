# Research Winner Full-History Replay Feedback

- generation: **5112**
- provisional winner: **evo-g05112-c02-7caf7d2cee**
- incumbent research parent: **signal-g04789-c01-29ccf32ff6**
- accepted research parent: **signal-g04789-c01-29ccf32ff6**
- candidate accepted: **NO**
- replay cache used: **NO**
- 用途: **Research探索の親選択専用。Production昇格証拠には使用しない**

| 指標 | Candidate | Incumbent |
|---|---:|---:|
| feedback objective | -0.0307 | 0.0130 |
| full score Δ vs random | +0.0588 | +0.1315 |
| 120 score Δ vs random | -0.1003 | +0.0293 |
| 60 score Δ vs random | -0.0519 | -0.0169 |
| 30 score Δ vs random | -0.0582 | -0.3992 |

- objective gain: **-0.0437**
- checks: `{"full_max_hits_not_regressed": false, "objective_improves": false, "recent120_score_not_regressed": false}`

> 最新モデルを過去へ再適用した結果はselection leakageを含み得るため、独立精度とは扱いません。未来OOSガバナンスは変更しません。
