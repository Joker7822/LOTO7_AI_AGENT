# Matched-Budget Null-Search Calibration

- completed null worlds: **15/64**
- matched candidate-trial budget/world: **602**
- matched plateau limit: **300 generations**
- Signal gate matched: **YES**
- four-era gate matched: **YES**
- observed real Signal objective: **-0.03447**
- null median best: **-0.05368**
- null 95th percentile best: **-0.03165**
- null 99th percentile best: **-0.02742**
- empirical upper-tail p: **0.1875**
- calibration complete: **NO**

> 実データ側で消費したSignal trial数と同じ候補budgetを各Null worldへ与え、現在のSignal/era採用ルールとplateau停止を同じように適用します。
> 過去に使った旧optimizerの細部を完全再演するものではなく、現在のResearch選択ポリシーを同一探索量で較正する検定です。Production昇格証拠には使用しません。
