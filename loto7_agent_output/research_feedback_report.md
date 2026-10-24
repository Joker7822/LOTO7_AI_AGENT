# Research Winner Full-History Replay Feedback

- generation: **5264**
- provisional winner: **evo-g05264-c02-477ed0db15**
- incumbent research parent: **signal-g05198-c01-4cb45d5a7b**
- accepted research parent: **evo-g05264-c02-477ed0db15**
- candidate accepted: **YES**
- replay cache used: **NO**
- 用途: **Research探索の親選択専用。Production昇格証拠には使用しない**

| 指標 | Candidate | Incumbent |
|---|---:|---:|
| feedback objective | 0.0998 | 0.0005 |
| full score Δ vs random | +0.0476 | +0.0234 |
| 120 score Δ vs random | +0.1528 | -0.0433 |
| 60 score Δ vs random | +0.1256 | +0.0344 |
| 30 score Δ vs random | +0.0455 | +0.0058 |

- objective gain: **+0.0993**
- checks: `{"full_max_hits_not_regressed": true, "objective_improves": true, "recent120_score_not_regressed": true}`

> 最新モデルを過去へ再適用した結果はselection leakageを含み得るため、独立精度とは扱いません。未来OOSガバナンスは変更しません。
