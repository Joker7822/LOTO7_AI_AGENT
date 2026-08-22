# Research Winner Full-History Replay Feedback

- generation: **800**
- provisional winner: **evo-g00800-c03-b26235b243**
- incumbent research parent: **feedback-g00625-c01-1bd218e77b**
- accepted research parent: **feedback-g00625-c01-1bd218e77b**
- candidate accepted: **NO**
- replay cache used: **NO**
- 用途: **Research探索の親選択専用。Production昇格証拠には使用しない**

| 指標 | Candidate | Incumbent |
|---|---:|---:|
| feedback objective | 0.0470 | 0.3093 |
| full score Δ vs random | +0.0737 | +0.2533 |
| 120 score Δ vs random | +0.0323 | +0.3407 |
| 60 score Δ vs random | +0.0572 | +0.3917 |
| 30 score Δ vs random | -0.0150 | +0.2303 |

- objective gain: **-0.2622**
- checks: `{"full_max_hits_not_regressed": false, "objective_improves": false, "recent120_score_not_regressed": false}`

> 最新モデルを過去へ再適用した結果はselection leakageを含み得るため、独立精度とは扱いません。未来OOSガバナンスは変更しません。
