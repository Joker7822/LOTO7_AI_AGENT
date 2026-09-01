# Regularized Signal Meta-Model

## Purpose

This research family tests whether the historical draw stream contains number-ranking signal that the current Hedge mixture does not capture.

It is deliberately separated from ticket portfolio optimization.

## Model

`signal_meta_model.py` builds one feature vector for each of the 37 numbers immediately before each target draw.

Features are derived only from the prefix available at that time:

- log relative scores from every existing expert (`hot`, EWMA, overdue, cold, momentum, pair context)
- whether the number appeared in the immediately preceding draw
- current gap divided by historical mean gap
- 12-draw minus 48-draw frequency momentum

Features are standardized across the 37 numbers at each target time.

A linear score is mapped to a 37-way softmax. The target distribution assigns `1/7` mass to each of the seven actual numbers. After each result is observed, one L2-regularized online cross-entropy update is performed.

The prediction for draw `t` is therefore computed before draw `t` is used for learning.

## Predeclared family

The v1 family contains exactly three fixed configurations:

- `meta-conservative`
- `meta-balanced`
- `meta-adaptive`

They differ only in learning rate, L2 strength, forgetting, and final uniform shrinkage. The family is intentionally small to limit historical search degrees of freedom.

## Nested historical evaluation

`signal_meta_replay.py` runs all three configurations in true walk-forward order and evaluates the last 120 predictions with a nested selector.

For target row `i`, the selector may inspect only scored rows `< i`. The target row itself cannot affect which model is selected for that row.

Primary metrics are signal metrics only:

- Top-7 hits
- actual-number probability mass
- mean log probability of the seven actual numbers
- Brier score

The reference models are:

- Uniform `1/37`
- current baseline Hedge Champion

Paired differences against the Hedge Champion use an 8-draw moving-block bootstrap to reduce sensitivity to short-range dependence.

## Governance

This is retrospective Research evidence only.

Even if the meta-model beats Uniform and the current Hedge Champion historically:

1. it is **not** automatically registered as a Formal Challenger;
2. historical results do not enter Production promotion evidence;
3. positive historical findings require matched null/search calibration;
4. a new candidate must then be frozen prospectively under Future-OOS governance before any Production claim.

`overlap_penalty`, five-ticket portfolio score, and matched-permutation portfolio gates are intentionally absent from this signal-only research stage.
