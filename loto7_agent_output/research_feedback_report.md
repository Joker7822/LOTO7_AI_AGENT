# Research Winner Full-History Replay Feedback

- generation: **5236**
- provisional winner: **evo-g05236-c03-737f25e40d**
- incumbent research parent: **signal-g05198-c01-4cb45d5a7b**
- accepted research parent: **signal-g05198-c01-4cb45d5a7b**
- candidate accepted: **NO**
- replay cache used: **NO**
- 用途: **Research探索の親選択専用。Production昇格証拠には使用しない**

| 指標 | Candidate | Incumbent |
|---|---:|---:|
| feedback objective | 0.0304 | 0.0005 |
| full score Δ vs random | -0.0069 | +0.0234 |
| 120 score Δ vs random | +0.0041 | -0.0433 |
| 60 score Δ vs random | +0.0903 | +0.0344 |
| 30 score Δ vs random | +0.1335 | +0.0058 |

- objective gain: **+0.0299**
- checks: `{"full_max_hits_not_regressed": false, "objective_improves": true, "recent120_score_not_regressed": true}`

> 最新モデルを過去へ再適用した結果はselection leakageを含み得るため、独立精度とは扱いません。未来OOSガバナンスは変更しません。
