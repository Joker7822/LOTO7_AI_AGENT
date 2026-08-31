# Matched-Permutation Future-OOS Null

## Purpose

This protocol separates **number-selection signal** from **5-ticket portfolio geometry** in prospective LOTO7 evaluation.

The strict Future-OOS protocol compares the Formal Challenger with:

1. the frozen Production Champion;
2. a pre-frozen equal-budget 5-ticket Uniform Random portfolio; and
3. a pre-frozen **32-member matched label-permutation ensemble**.

The original single matched permutation remains frozen as member 0 for audit continuity, but Production promotion uses the **mean portfolio score across all 32 matched members**.

## Construction

For each future target round, before the result is known:

1. freeze the Formal Challenger's five tickets;
2. preserve the original deterministic matched permutation (`matched-permutation-null-v1`) as ensemble member 0;
3. deterministically generate 31 additional unique permutations of labels `1..37` from a separately predeclared target-round seed;
4. apply each common permutation to every number in every challenger ticket;
5. verify that all 32 transformed portfolios preserve the original portfolio geometry;
6. freeze all 32 portfolios and their permutations before the target result exists.

A common bijection preserves exactly:

- the number of tickets;
- seven numbers per ticket;
- every pairwise ticket overlap;
- total union/coverage size;
- all higher-order overlap structure.

It changes only **which number labels occupy those structural positions**.

Therefore, under an exchangeable 7-of-37 null, the original portfolio and each permuted portfolio have the same expected score. Averaging 32 pre-frozen matched portfolios reduces the chance that one unusually easy or difficult permutation dominates the comparator while continuing to target number identity/selection rather than portfolio geometry.

## Ensemble aggregation

For each trusted future draw:

- score the frozen Challenger once;
- score each of the 32 matched portfolios;
- compute `matched_ensemble_score = mean(member_1_score, ..., member_32_score)`;
- use `challenger_score - matched_ensemble_score` as the matched-null score delta for that draw.

The per-draw matched-ensemble delta remains bounded by the same portfolio-score range as the existing paired comparisons, so it is passed through the same bounded sequential e-process normalization.

The original single matched score continues to be recorded as audit/telemetry data. It is no longer the Production matched-null promotion gate once the 32-member ensemble is frozen.

## Promotion gate

Production promotion requires the strict conditions against **all three promotion references**:

- Champion;
- equal-budget Uniform Random;
- 32-member matched permutation ensemble mean.

For each comparator:

- at least 8 trusted future draws;
- mean score delta >= +0.05;
- win rate >= 55%.

The sequential e-value intersection is the minimum raw e-value across the Champion, Uniform Random, and matched-ensemble comparisons, multiplied by the Formal Challenger block's family weight. The adjusted threshold remains 20.

For block 1 (`family_weight = 0.5`), each raw comparison must therefore reach at least 40 before the adjusted intersection can reach 20.

## Migration from the single matched comparator

For a target round that already has the original matched comparator frozen but whose draw result is still unknown, the ensemble may be expanded prospectively:

- the already-frozen single comparator must remain exactly ensemble member 0;
- only the additional 31 members are added;
- the ensemble receives its own freeze timestamp;
- the original matched freeze timestamp and tickets are never rewritten.

For target rounds whose results are already present, missing ensemble members cannot be created retroactively.

## Fail-closed rule

A matched ensemble cannot be created or repaired after its target draw already exists in `loto7.csv`. If all 32 members were not frozen in time, that draw is not eligible for matched-ensemble promotion evidence.

## Fixed prospective holdout

The 26-trusted-draw fixed holdout receives the same 32-member matched permutation ensemble. Its ensemble score delta, win rate, and e-value are diagnostic and are not used to change the locked holdout configuration.

## Interpretation

Passing this gate does **not** prove that lottery draws are predictable. It establishes that the frozen model performed better, in the specified future sample, than the Production Champion, a uniform equal-budget reference, and the mean of 32 predeclared geometry-matched label permutations.
