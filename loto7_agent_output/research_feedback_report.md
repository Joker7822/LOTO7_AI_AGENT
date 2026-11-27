# Research Winner Full-History Replay Feedback

- generation: **7009**
- provisional winner: **evo-g07009-c04-7e68b0c059**
- incumbent research parent: **signal-g06845-c01-6183c9b064**
- accepted research parent: **signal-g06845-c01-6183c9b064**
- candidate accepted: **NO**
- replay cache used: **NO**
- 用途: **Research探索の親選択専用。Production昇格証拠には使用しない**

| 指標 | Candidate | Incumbent |
|---|---:|---:|
| feedback objective | -0.0165 | 0.2363 |
| full score Δ vs random | +0.0341 | +0.2117 |
| 120 score Δ vs random | +0.0229 | +0.1909 |
| 60 score Δ vs random | -0.1135 | +0.3039 |
| 30 score Δ vs random | -0.1373 | +0.3457 |

- objective gain: **-0.2528**
- checks: `{"full_max_hits_not_regressed": false, "objective_improves": false, "recent120_score_not_regressed": false}`

> 最新モデルを過去へ再適用した結果はselection leakageを含み得るため、独立精度とは扱いません。未来OOSガバナンスは変更しません。
