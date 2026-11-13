# Research Winner Full-History Replay Feedback

- generation: **6411**
- provisional winner: **evo-g06411-c01-7a9d5b4426**
- incumbent research parent: **signal-g05814-c01-a0b6c7d9c2**
- accepted research parent: **signal-g05814-c01-a0b6c7d9c2**
- candidate accepted: **NO**
- replay cache used: **NO**
- 用途: **Research探索の親選択専用。Production昇格証拠には使用しない**

| 指標 | Candidate | Incumbent |
|---|---:|---:|
| feedback objective | 0.0166 | 0.2527 |
| full score Δ vs random | +0.0952 | +0.1632 |
| 120 score Δ vs random | +0.0400 | +0.3429 |
| 60 score Δ vs random | -0.1036 | +0.2177 |
| 30 score Δ vs random | -0.0997 | +0.3206 |

- objective gain: **-0.2361**
- checks: `{"full_max_hits_not_regressed": false, "objective_improves": false, "recent120_score_not_regressed": false}`

> 最新モデルを過去へ再適用した結果はselection leakageを含み得るため、独立精度とは扱いません。未来OOSガバナンスは変更しません。
