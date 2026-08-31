# Matched Ensemble Rank Diagnostics

## Purpose

The 32-member matched-permutation ensemble is the prospective geometry-matched null used by the strict Future-OOS validation gate. Its mean score is already used for the Production promotion comparison.

This diagnostic layer adds a second view of each future draw: **where the frozen Challenger score sits inside the 32 pre-frozen null scores**.

It is descriptive only. It does **not** replace or add to the sequential e-process Promotion gate.

## Per-draw statistics

For a frozen Challenger score `S` and the 32 pre-frozen matched-null scores:

- `null_below`: number of null scores strictly below `S`;
- `null_equal`: number tied with `S`;
- `null_above`: number strictly above `S`;
- `percentile_midrank = 100 * (null_below + 0.5 * null_equal) / 32`;
- `candidate_midrank_from_top = 1 + null_above + 0.5 * null_equal` among the observed Challenger plus 32 null members;
- one-sided Monte-Carlo permutation diagnostic
  `p = (1 + null_above + null_equal) / 33`.

The `+1` correction prevents a zero p-value from a finite Monte-Carlo sample. With 32 null members, the smallest possible single-draw value is `1/33 = 0.030303...`.

## Interpretation

A high percentile means the Challenger scored above most geometry-identical label permutations on that draw. A low one-sided Monte-Carlo p-value means few of the pre-frozen matched permutations scored at least as well as the Challenger.

These are **single-draw diagnostics**, not standalone evidence that LOTO7 is predictable. The mean of single-draw p-values is displayed only as a descriptive summary and is not treated as a combined p-value.

Prospective Production promotion continues to require the existing sequential evidence thresholds against:

1. Production Champion;
2. equal-budget Uniform Random;
3. the 32-member Matched Ensemble mean.

## Audit outputs

Formal Challenger diagnostics are appended to:

- `loto7_agent_output/matched_ensemble_rank_results.csv`

Fixed prospective holdout diagnostics are appended to:

- `loto7_agent_output/future_holdout_matched_ensemble_rank_results.csv`

The OOS and holdout state files store the latest rank, percentile, p-value, null below/equal/above counts, and trusted-draw descriptive averages.

## Pre-freeze integrity

No new randomization is generated during grading. Rank diagnostics use only the 32 ensemble members already frozen before the target result. If the matched ensemble is missing or invalid, rank diagnostics fail closed rather than constructing a replacement after the draw.
