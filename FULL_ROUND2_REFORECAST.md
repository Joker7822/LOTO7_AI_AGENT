# Full Historical Reforecast — from Round 2

A **research-only, chronological replay** of every confirmed LOTO7 draw from
round 2 to the latest row in `loto7.csv`. It reconstructs forecasts today;
it does NOT establish that such forecasts existed before those historical
drawings, and must not be treated as independently frozen prospective evidence.

## Required cold start

- Round 2 uses only actual round 1 as prior.
- Rounds 2..20 have fewer than 20 previous draws; the existing
  `expert_probabilities()` requires 20 or more. Therefore these 19 rounds
  use exact uniform probability `1/37`, with seeded, unbiased tie breaking.
- Round 21 onward runs the frozen `baseline-5fdb8dc2ad` configuration:
  historical `int8` legacy expert, with weight updates **only after** observing
  each result. This reforecast initializes online learning at round 21, whereas
  older reports using round-101 min-train are NOT the same protocol.

## Prespecified signal models and ticket arms

The five signal comparisons are uniform, `legacy`, `pair_int64`,
`drop_ewma`, `prior_uniform_gate` (return to uniform if the previous
30 *legacy* Bernoulli log-score edges were nonpositive on average).

Seven 5-ticket arms, all created from previous draws only:

- `uniform_random`, `legacy_random`: average of 8 independent seeded
  5-ticket samples per target round. The first sample's actual five tickets
  are in the record, but scores average across the full sample.
- `uniform_optimized`, `legacy_optimized`,
  `pair_int64_optimized`, `drop_ewma_optimized`,
  `prior_uniform_gate_optimized`: one five-ticket portfolio each, selected
  with the shared, research-only scenario-based greedy optimizer.

For model vs uniform comparisons, ticket generation uses the same seeds.
Each round stores: prior count, date, actual 7 numbers, top-7 signal ranking,
complete five-ticket optimized forecasts, seed-based example random forecasts,
per-arm max and average hits, any 3+/4+ results, composite portfolio score,
proper Bernoulli log/Brier signals and the **pre-outcome** forecast SHA-256.

Summaries are provided over all rounds, cold-start 2-20, adaptive 21 onward,
21-100, 101 onward, last 120 and last 60.

## Execution

```bash
python -m pytest -q tests/test_full_round2_reforecast.py
python full_round2_reforecast.py \
  --csv loto7.csv \
  --out research_output/full_round2_reforecast.json \
  --scenarios 96 --candidates 32 --random-reps 8 \
  --seed 20261025
```

For GitHub, pull requests affecting replay code automatically trigger the
read-only `Historical Reforecast From Round 2` workflow, which uploads the
full JSON artifact. No repository worktree changes are made by the diagnostic,
outside an untracked `research_output/` path. This workflow cannot push.

## Interpretability and governance

1. **No future-target leakage in the calculation:** for target t, each
   distribution and all five tickets are generated from historical rows < t.
   Target values are read only after a pre-outcome forecast digest is computed.
2. **No independent skill claim:** this is still an in-sample-era historical
   reconstruction because algorithm choices were developed with historical
   hindsight. Even 699 backtested predictions are not 699 prospectively
   preregistered predictions. Confidence based on reusing this development
   history would be overstated.
3. **No Production substitution:** prior fixed predictions, Champion,
   current 26-draw future holdout and live OOS evidence are unchanged.
4. **No promise of a lottery edge:** for conditionally fair 7-of-37 draws,
   each combination has probability 1/10,295,472; changing historical model
   complexity does not make a future lottery ticket more likely to win first
   prize.
5. **Comparability:** previous 600-round v2/v3 reports start at 101 and
   use different training burn-in and portfolio construction. Do not interpret
   differences as an exact repair of historical issued predictions.
