# Research Winner Full-History Replay Feedback

- generation: **310**
- provisional winner: **evo-g00310-c02-f765657a9f**
- incumbent research parent: **feedback-g00308-c01-662d478c2c**
- accepted research parent: **feedback-g00308-c01-662d478c2c**
- candidate accepted: **NO**
- replay cache used: **NO**
- 用途: **Research探索の親選択専用。Production昇格証拠には使用しない**

| 指標 | Candidate | Incumbent |
|---|---:|---:|
| feedback objective | -0.1001 | 0.1023 |
| full score Δ vs random | +0.0343 | +0.1565 |
| 120 score Δ vs random | -0.0775 | +0.0661 |
| 60 score Δ vs random | -0.2317 | +0.1760 |
| 30 score Δ vs random | -0.3863 | -0.1080 |

- objective gain: **-0.2024**
- checks: `{"full_max_hits_not_regressed": false, "objective_improves": false, "recent120_score_not_regressed": false}`

> 最新モデルを過去へ再適用した結果はselection leakageを含み得るため、独立精度とは扱いません。未来OOSガバナンスは変更しません。
