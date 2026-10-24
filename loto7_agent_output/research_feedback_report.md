# Research Winner Full-History Replay Feedback

- generation: **5130**
- provisional winner: **evo-g05130-c02-826406b904**
- incumbent research parent: **signal-g05129-c01-6cc09a5015**
- accepted research parent: **signal-g05129-c01-6cc09a5015**
- candidate accepted: **NO**
- replay cache used: **NO**
- 用途: **Research探索の親選択専用。Production昇格証拠には使用しない**

| 指標 | Candidate | Incumbent |
|---|---:|---:|
| feedback objective | 0.0645 | 0.1252 |
| full score Δ vs random | +0.0491 | +0.0883 |
| 120 score Δ vs random | +0.0769 | +0.0668 |
| 60 score Δ vs random | +0.0311 | +0.1896 |
| 30 score Δ vs random | +0.1412 | +0.3298 |

- objective gain: **-0.0607**
- checks: `{"full_max_hits_not_regressed": false, "objective_improves": false, "recent120_score_not_regressed": true}`

> 最新モデルを過去へ再適用した結果はselection leakageを含み得るため、独立精度とは扱いません。未来OOSガバナンスは変更しません。
