# Research Winner Full-History Replay Feedback

- generation: **5094**
- provisional winner: **evo-g05094-c04-acd2e1847b**
- incumbent research parent: **signal-g04789-c01-29ccf32ff6**
- accepted research parent: **signal-g04789-c01-29ccf32ff6**
- candidate accepted: **NO**
- replay cache used: **NO**
- 用途: **Research探索の親選択専用。Production昇格証拠には使用しない**

| 指標 | Candidate | Incumbent |
|---|---:|---:|
| feedback objective | 0.0912 | 0.0130 |
| full score Δ vs random | +0.0360 | +0.1315 |
| 120 score Δ vs random | +0.1309 | +0.0293 |
| 60 score Δ vs random | +0.1138 | -0.0169 |
| 30 score Δ vs random | +0.1005 | -0.3992 |

- objective gain: **+0.0783**
- checks: `{"full_max_hits_not_regressed": false, "objective_improves": true, "recent120_score_not_regressed": true}`

> 最新モデルを過去へ再適用した結果はselection leakageを含み得るため、独立精度とは扱いません。未来OOSガバナンスは変更しません。
