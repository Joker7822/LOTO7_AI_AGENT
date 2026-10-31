# Research Winner Full-History Replay Feedback

- generation: **5692**
- provisional winner: **evo-g05692-c02-7c587f68f7**
- incumbent research parent: **signal-g05690-c01-7b9859bf53**
- accepted research parent: **signal-g05690-c01-7b9859bf53**
- candidate accepted: **NO**
- replay cache used: **NO**
- 用途: **Research探索の親選択専用。Production昇格証拠には使用しない**

| 指標 | Candidate | Incumbent |
|---|---:|---:|
| feedback objective | -0.0255 | -0.0772 |
| full score Δ vs random | +0.0282 | +0.0641 |
| 120 score Δ vs random | -0.0538 | -0.1184 |
| 60 score Δ vs random | -0.0800 | -0.1714 |
| 30 score Δ vs random | -0.0056 | -0.2393 |

- objective gain: **+0.0517**
- checks: `{"full_max_hits_not_regressed": false, "objective_improves": true, "recent120_score_not_regressed": true}`

> 最新モデルを過去へ再適用した結果はselection leakageを含み得るため、独立精度とは扱いません。未来OOSガバナンスは変更しません。
