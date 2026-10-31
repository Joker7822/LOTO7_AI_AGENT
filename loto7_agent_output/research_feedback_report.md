# Research Winner Full-History Replay Feedback

- generation: **5623**
- provisional winner: **evo-g05623-c03-a1b977c9c4**
- incumbent research parent: **signal-g05622-c02-44c2d7a3af**
- accepted research parent: **signal-g05622-c02-44c2d7a3af**
- candidate accepted: **NO**
- replay cache used: **NO**
- 用途: **Research探索の親選択専用。Production昇格証拠には使用しない**

| 指標 | Candidate | Incumbent |
|---|---:|---:|
| feedback objective | 0.0328 | 0.1152 |
| full score Δ vs random | +0.0310 | +0.1329 |
| 120 score Δ vs random | -0.0079 | +0.0948 |
| 60 score Δ vs random | -0.0060 | +0.1175 |
| 30 score Δ vs random | +0.2594 | +0.1197 |

- objective gain: **-0.0824**
- checks: `{"full_max_hits_not_regressed": false, "objective_improves": false, "recent120_score_not_regressed": false}`

> 最新モデルを過去へ再適用した結果はselection leakageを含み得るため、独立精度とは扱いません。未来OOSガバナンスは変更しません。
