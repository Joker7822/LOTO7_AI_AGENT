# Research Winner Full-History Replay Feedback

- generation: **5123**
- provisional winner: **evo-g05123-c03-f91a57d4bc**
- incumbent research parent: **signal-g04789-c01-29ccf32ff6**
- accepted research parent: **signal-g04789-c01-29ccf32ff6**
- candidate accepted: **NO**
- replay cache used: **NO**
- 用途: **Research探索の親選択専用。Production昇格証拠には使用しない**

| 指標 | Candidate | Incumbent |
|---|---:|---:|
| feedback objective | 0.0238 | 0.0130 |
| full score Δ vs random | +0.0534 | +0.1315 |
| 120 score Δ vs random | +0.0563 | +0.0293 |
| 60 score Δ vs random | -0.0364 | -0.0169 |
| 30 score Δ vs random | -0.0732 | -0.3992 |

- objective gain: **+0.0108**
- checks: `{"full_max_hits_not_regressed": false, "objective_improves": true, "recent120_score_not_regressed": true}`

> 最新モデルを過去へ再適用した結果はselection leakageを含み得るため、独立精度とは扱いません。未来OOSガバナンスは変更しません。
