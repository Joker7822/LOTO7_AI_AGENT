# Research Winner Full-History Replay Feedback

- generation: **5108**
- provisional winner: **evo-g05108-c01-7f8d68d18d**
- incumbent research parent: **signal-g04789-c01-29ccf32ff6**
- accepted research parent: **signal-g04789-c01-29ccf32ff6**
- candidate accepted: **NO**
- replay cache used: **NO**
- 用途: **Research探索の親選択専用。Production昇格証拠には使用しない**

| 指標 | Candidate | Incumbent |
|---|---:|---:|
| feedback objective | 0.1328 | 0.0130 |
| full score Δ vs random | +0.0629 | +0.1315 |
| 120 score Δ vs random | +0.1113 | +0.0293 |
| 60 score Δ vs random | +0.2013 | -0.0169 |
| 30 score Δ vs random | +0.3162 | -0.3992 |

- objective gain: **+0.1198**
- checks: `{"full_max_hits_not_regressed": false, "objective_improves": true, "recent120_score_not_regressed": true}`

> 最新モデルを過去へ再適用した結果はselection leakageを含み得るため、独立精度とは扱いません。未来OOSガバナンスは変更しません。
