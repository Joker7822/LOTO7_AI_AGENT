# Research Winner Full-History Replay Feedback

- generation: **5280**
- provisional winner: **evo-g05280-c04-218e35b40c**
- incumbent research parent: **signal-g05276-c01-af711eb9cb**
- accepted research parent: **signal-g05276-c01-af711eb9cb**
- candidate accepted: **NO**
- replay cache used: **NO**
- 用途: **Research探索の親選択専用。Production昇格証拠には使用しない**

| 指標 | Candidate | Incumbent |
|---|---:|---:|
| feedback objective | 0.0855 | 0.0915 |
| full score Δ vs random | +0.0551 | +0.1671 |
| 120 score Δ vs random | +0.1575 | +0.1032 |
| 60 score Δ vs random | +0.0224 | -0.0247 |
| 30 score Δ vs random | +0.0655 | +0.0182 |

- objective gain: **-0.0060**
- checks: `{"full_max_hits_not_regressed": false, "objective_improves": false, "recent120_score_not_regressed": true}`

> 最新モデルを過去へ再適用した結果はselection leakageを含み得るため、独立精度とは扱いません。未来OOSガバナンスは変更しません。
