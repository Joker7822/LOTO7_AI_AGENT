# Research Winner Full-History Replay Feedback

- generation: **5294**
- provisional winner: **evo-g05294-c04-df5984b032**
- incumbent research parent: **signal-g05281-c01-55a70e0b94**
- accepted research parent: **signal-g05281-c01-55a70e0b94**
- candidate accepted: **NO**
- replay cache used: **NO**
- 用途: **Research探索の親選択専用。Production昇格証拠には使用しない**

| 指標 | Candidate | Incumbent |
|---|---:|---:|
| feedback objective | 0.0002 | 0.1142 |
| full score Δ vs random | +0.0426 | +0.1402 |
| 120 score Δ vs random | +0.0236 | +0.1172 |
| 60 score Δ vs random | -0.0679 | +0.1106 |
| 30 score Δ vs random | -0.0942 | +0.0202 |

- objective gain: **-0.1141**
- checks: `{"full_max_hits_not_regressed": false, "objective_improves": false, "recent120_score_not_regressed": false}`

> 最新モデルを過去へ再適用した結果はselection leakageを含み得るため、独立精度とは扱いません。未来OOSガバナンスは変更しません。
