# Research Winner Full-History Replay Feedback

- generation: **5175**
- provisional winner: **evo-g05175-c02-2603b3d480**
- incumbent research parent: **signal-g05173-c02-2ea7248cef**
- accepted research parent: **signal-g05173-c02-2ea7248cef**
- candidate accepted: **NO**
- replay cache used: **NO**
- 用途: **Research探索の親選択専用。Production昇格証拠には使用しない**

| 指標 | Candidate | Incumbent |
|---|---:|---:|
| feedback objective | 0.1141 | 0.2134 |
| full score Δ vs random | +0.1425 | +0.1441 |
| 120 score Δ vs random | +0.0949 | +0.2588 |
| 60 score Δ vs random | +0.0756 | +0.2776 |
| 30 score Δ vs random | +0.1585 | +0.1692 |

- objective gain: **-0.0994**
- checks: `{"full_max_hits_not_regressed": false, "objective_improves": false, "recent120_score_not_regressed": false}`

> 最新モデルを過去へ再適用した結果はselection leakageを含み得るため、独立精度とは扱いません。未来OOSガバナンスは変更しません。
