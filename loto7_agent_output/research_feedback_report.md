# Research Winner Full-History Replay Feedback

- generation: **5521**
- provisional winner: **evo-g05521-c04-e7be4b16fb**
- incumbent research parent: **signal-g05281-c01-55a70e0b94**
- accepted research parent: **signal-g05281-c01-55a70e0b94**
- candidate accepted: **NO**
- replay cache used: **NO**
- 用途: **Research探索の親選択専用。Production昇格証拠には使用しない**

| 指標 | Candidate | Incumbent |
|---|---:|---:|
| feedback objective | 0.0804 | 0.0941 |
| full score Δ vs random | -0.0510 | +0.1367 |
| 120 score Δ vs random | +0.0481 | +0.1012 |
| 60 score Δ vs random | +0.2746 | +0.0825 |
| 30 score Δ vs random | +0.2651 | -0.0569 |

- objective gain: **-0.0136**
- checks: `{"full_max_hits_not_regressed": false, "objective_improves": false, "recent120_score_not_regressed": false}`

> 最新モデルを過去へ再適用した結果はselection leakageを含み得るため、独立精度とは扱いません。未来OOSガバナンスは変更しません。
