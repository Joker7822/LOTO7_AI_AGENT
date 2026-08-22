# Research Winner Full-History Replay Feedback

- generation: **313**
- provisional winner: **evo-g00313-c04-e39c4958da**
- incumbent research parent: **feedback-g00312-c01-105d4e9dce**
- accepted research parent: **feedback-g00312-c01-105d4e9dce**
- candidate accepted: **NO**
- replay cache used: **NO**
- 用途: **Research探索の親選択専用。Production昇格証拠には使用しない**

| 指標 | Candidate | Incumbent |
|---|---:|---:|
| feedback objective | 0.0282 | 0.1194 |
| full score Δ vs random | +0.0518 | +0.1423 |
| 120 score Δ vs random | +0.0318 | +0.0905 |
| 60 score Δ vs random | +0.0632 | +0.1747 |
| 30 score Δ vs random | -0.1370 | +0.0297 |

- objective gain: **-0.0912**
- checks: `{"full_max_hits_not_regressed": false, "objective_improves": false, "recent120_score_not_regressed": false}`

> 最新モデルを過去へ再適用した結果はselection leakageを含み得るため、独立精度とは扱いません。未来OOSガバナンスは変更しません。
