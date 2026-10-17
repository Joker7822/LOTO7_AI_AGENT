# Joint Set Research v2

更新: 2026-10-17 JST

## 目的

Joint Set v2 は、LOTO7 の次回7数字を Research-only で検証する構造モデルです。Production Champion、Formal Challenger、既存の Future OOS holdout は変更しません。

v1 の `q`（37数字で合計1の相対分布）とは分離し、v2 は各数字について

`p_i = P(number i is included in the next 7-number set)`

を表す inclusion probability を使用します。常に次を満たすよう射影します。

- `0 <= p_i <= 1`
- `sum_i p_i = 7`

## Signal evaluation

各対象回 t では t より前の履歴だけを使用します。Signal は37数字すべてについて marginal Bernoulli proper score を計算します。

- Bernoulli log score edge vs uniform `p=7/37`
- Bernoulli Brier score edge vs uniform `p=7/37`
- Top7 hits
- 実際に出た7数字の平均 inclusion probability

Dynamic Uniform Gate は過去の prequential proper-score evidence が弱い、または負の場合にモデル成分を縮小します。負の log/Brier evidence が続く場合は、ほぼ uniform へ退避します。

## Structural model

v2 は小さな事前定義 config family のみを使用します。

- recency-weighted marginal inclusion estimates
- overdue / momentum の弱い構造補正
- low-rank pair interaction
- stable / shift / volatile の prior-only regime filter
- dynamic uniform gate

config 選択も対象回より前の prequential signal rows だけで行います。

## Five-ticket portfolio

最終5口は固定 overlap penalty ではなく、モデルから生成した次回抽せん scenario に対する expected utility を最大化します。

utility は max hits を基本に、3個以上、4個以上、5個以上、6個以上、7個一致へ段階的な重みを加えます。係数はコード上で事前固定し、対象回の結果を見て変更しません。

## Matched-budget null calibration

`joint_set_v2_null_calibration.py` は完全ランダムな7/37世界を生成し、実データと同じ以下の研究予算を再実行します。

- predeclared config family
- config selection rule
- Dynamic Uniform Gate
- regime / pair model
- scenario count
- candidate count
- expected-utility portfolio optimizer

標準 target は64 worldsです。null calibration は Research の探索バイアス診断であり、Production 昇格証拠には使用しません。

Random 5-ticket baseline は数字ラベル対称性により、7個の実数字のラベルに依存しない同一のMonte Carlo null分布を使用します。

## Outputs

- `loto7_agent_output/joint_set_v2_true_nested_summary.json`
- `loto7_agent_output/joint_set_v2_true_nested.csv`
- `loto7_agent_output/joint_set_v2_true_nested_report.md`
- `loto7_agent_output/joint_set_v2_current_research.json`
- `loto7_agent_output/joint_set_v2_candidate_tickets.csv`
- `loto7_agent_output/joint_set_v2_null_calibration_state.json`
- `loto7_agent_output/joint_set_v2_null_calibration_summary.json`
- `loto7_agent_output/joint_set_v2_null_calibration_report.md`

## Governance

Joint Set v2 の historical replay や synthetic null が良好でも、それだけで Production へ昇格しません。将来採用する場合は、事前凍結した候補として Future OOS governance に登録し、未知の将来抽せん結果による証拠を別途蓄積する必要があります。
