# Research: Legacy Top1 shared across exactly two of five tickets

Version: **`legacy-top1-two-tickets-34-v1`**.

This is a new *research-only* ticket configuration, not a replacement for the
previously frozen 35-number disjoint candidate or Production Champion. The
existing `research/disjoint_future_oos/freeze_0701.json`, registered 26-draw
protocol, other Future OOS, and old prediction ledgers are **not modified**.

## Algorithm

1. The Top1 anchor is the number with greatest probability from the existing
   `baseline-5fdb8dc2ad` legacy score **calculated solely from earlier draws**.
   It is a ranking, **not calibrated confidence** and not a demonstrated
   above-chance prediction.
2. Place that number into tickets **1 and 2 exactly once each**.
3. Shuffle the other 36 numbers with the per-round preselected RNG seed.
   Tickets 1 and 2 receive six unique others each; tickets 3–5 receive seven
   unique others each. The remaining three numbers are unused.
4. Total: **5 tickets × 7 numbers, 34 distinct numbers**, exactly one
   duplicate across tickets; no other interticket overlap.

In rounds 2–20, `expert_probabilities` cannot train with fewer than 20
prior draws, so choose a seeded uniform tie-breaking anchor. From round 21,
update the existing legacy ensemble only *after* each target outcome.

## Comparators

- `legacy_top1_overlap34`: the requested strategy.
- `uniform_anchor_overlap34`: **same 34-number geometry** but its shared
  number is drawn from uniform seeded ranking. This controls for geometry and
  tests whether the historic AI Top1 actually adds any information.
- `uniform_disjoint35`: previous, independent 35-number/zero-overlap
  construction, generated with the same target RNG seed as the new arm.

The historical report includes per-round Top1, control anchor, exact tickets,
pre-outcome forecast SHA-256, actual seven numbers, maximum/mean matches,
at-least-3/4 indicators and the previously defined composite score.
Aggregates cover draws 2+, 21+, 101+, last 120 and last 60, plus descriptive
paired-bootstrap 95% ranges. The intervals are **not** independent,
selection-adjusted future tests and may not be used for model promotion.

## Exact fair-lottery geometry calculation

With common-number inclusion `s=0..1`, independent unique groups of sizes
`6, 6, 7, 7, 7` and three unused numbers, enumerate each valid number-hit
count vector `k_i`:

```text
sum(k_i) + s + omitted = 7
ways = C(1,s) * C(3,omitted) * product C(group_i,k_i)
```

Sum over all `C(37,7) = 10,295,472` possible fair drawn sets. This exact
null is independent of which Top1 is selected. Results:

| Geometry | Any 3+ main hits | Composite score |
| --- | ---: | ---: |
| 34 distinct; Top1 shared in two tickets | 50.40983% | 2.941706 |
| 35 distinct; zero overlap | 50.96274% | 2.952151 |

Under a fair draw, the new arm gives up roughly **0.553 percentage points**
on P(any >=3) and 0.01045 composite-score units relative to 35 distinct
numbers. Both guarantee five *different* tickets and have exactly the
same first-prize probability, `5/C(37,7)`. The historical model could only
compensate for the coverage trade-off if its Top1 inclusion probability
was genuinely predictive—which has **not been established**.

## Run research-only backtest

```bash
python -m pytest -q tests/test_top1_overlap34_research.py
python top1_overlap34_research.py \
  --csv loto7.csv \
  --out research_output/top1_overlap34_research.json \
  --seed 20261025
```

GitHub Actions runs the tests and reforecasts all presently verified rounds
starting at #2, then uploads JSON for auditing. Code, generated artifact and
historical period selection use model-development data; no resulting score
creates independent pre-registration. A **separate prospective registration
and pre-result freeze** would be required to test this Top1 arm in new draws.

No Production model, historical issued predictions, draw data or existing
prospective freeze/grade files are changed.
