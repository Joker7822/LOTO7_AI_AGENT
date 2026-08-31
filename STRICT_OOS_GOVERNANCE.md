# Strict Future-OOS Governance

適用開始: **2026-08-31**

この層は、既存の v4 Research 探索や Historical replay の順位付けを変更せず、Production Champion 昇格に使う **未来 OOS 証拠だけを厳格化**します。

## 1. Pre-frozen equal-budget Random reference

各 target round について、Champion / Formal Challenger と同じ **5口**の Uniform Random portfolio を抽せん前に固定します。

- seed policy: `12000000 + target_round * 1009`
- 5口 x 7数字
- target result が CSV に入った後で Random reference が欠けていた場合、後付け生成しません
- 欠損した round は strict promotion evidence として fail closed します

保存先:

- `loto7_agent_output/shadow_registry.json`
  - `random_reference_tickets`
  - `random_reference_frozen_at_jst`
- `loto7_agent_output/paired_oos_results.csv`

## 2. Paired Future-OOS gate

Formal Challenger は、同じ未知の target result に対して以下の両方と paired 比較されます。

1. 現 Production Champion
2. 事前凍結した equal-budget Random reference

各比較で score delta を `MAX_PORTFOLIO_SCORE=8.8` で [-1, 1] に正規化し、既存 v4 と同じ lambda mixture e-process を更新します。

昇格には最低でも以下をすべて要求します。

- trusted Future OOS: 8回以上
- Champion に対する平均 score delta: +0.05以上
- Random に対する平均 score delta: +0.05以上
- Champion に対する勝率: 55%以上
- Random に対する勝率: 55%以上
- multiplicity-adjusted intersection e-value: 20以上

Random reference が欠ける場合は昇格不可です。

## 3. Sequential block multiplicity control

Formal Challenger を8回ブロックごとに何度も入れ替えると、各ブロックで同じ e-value 20 を使うだけではシステム全体の誤検出率を5%と解釈できません。

そこで block `i = 1, 2, ...` に

`w_i = 1 / (i(i+1))`

の e-capital weight を割り当てます。

`sum_i w_i = 1`

なので、family alpha 0.05 を逐次ブロック全体に配分できます。

既存 v4 の promotion threshold 20 は維持し、state に保存する `e_value` を

`family_adjusted_e = w_i * min(E_champion, E_random)`

と定義します。

したがって必要な raw e-value は:

- block 1: **40**
- block 2: **120**
- block 3: **240**
- block i: **20 * i * (i+1)**

となります。

## 4. Fixed prospective holdout

Promotion block とは独立に、開始時点の Formal Challenger config を固定し、**26 trusted future draws** を追跡します。

固定するもの:

- model config / version
- holdout horizon = 26 trusted draws
- 評価ロジック

各回で許可するもの:

- その回より前までに公開済みの LOTO7 履歴を使った expert-weight 更新
- 固定済み config に従う次回予測生成

禁止するもの:

- holdout 成績を見て model config を変更すること
- target result を見て ticket / Random reference を作り直すこと

保存先:

- `loto7_agent_output/future_holdout_state.json`
- `loto7_agent_output/future_holdout_registry.json`
- `loto7_agent_output/future_holdout_results.csv`

この holdout は診断専用で、現時点では Production promotion の条件には直接加算しません。

## 5. Backward compatibility

既存の以下は維持します。

- Historical replay / reconciliation / nested replay は診断専用
- 過去 Research score だけでは Production 昇格不可
- result source が `verified_two_result_sources` でない回は trusted promotion evidence に加算しない
- Weekly Production publication と Research execution は分離

実装は `research_v4_no_production.py` から `strict_oos_governance.py` を install する形にしており、`loto7_v4_runner.py` の retrospective Research ranking は変更しません。
