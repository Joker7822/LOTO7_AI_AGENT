# Matched-Permutation Future-OOS Null

## Purpose

This protocol separates **number-selection signal** from **5-ticket portfolio geometry** in prospective LOTO7 evaluation.

The existing strict Future-OOS protocol compares the Formal Challenger with:

1. the frozen Production Champion, and
2. a pre-frozen equal-budget 5-ticket Uniform Random portfolio.

This protocol adds a third comparator: a **matched label-permutation null**.

## Construction

For each future target round, before the result is known:

1. freeze the Formal Challenger's five tickets;
2. generate one deterministic predeclared permutation of the labels `1..37` using
   `23000000 + target_round * 1013`;
3. apply the same permutation to every number in every challenger ticket;
4. freeze the resulting five-ticket matched portfolio.

A common bijection preserves exactly:

- the number of tickets;
- seven numbers per ticket;
- every pairwise ticket overlap;
- total union/coverage size;
- all higher-order overlap structure.

It changes only **which number labels occupy those structural positions**.

Therefore, under an exchangeable 7-of-37 null, the original and permuted portfolios have the same expected score. A persistent advantage over the matched comparator is evidence about number identity/selection rather than portfolio geometry alone.

## Promotion gate

Production promotion now requires the existing strict conditions against **all three** references:

- Champion;
- equal-budget Uniform Random;
- matched permutation null.

For each comparator:

- at least 8 trusted future draws;
- mean score delta >= +0.05;
- win rate >= 55%.

The sequential e-value intersection is the minimum raw e-value across the three comparisons, multiplied by the Formal Challenger block's family weight. The existing adjusted threshold remains 20.

For block 1 (`family_weight = 0.5`), each raw comparison must therefore reach at least 40 before the adjusted intersection can reach 20.

## Fail-closed rule

A matched reference cannot be created after its target draw already exists in `loto7.csv`. If the reference was not frozen in time, that draw is not eligible for matched-null promotion evidence.

## Fixed prospective holdout

The 26-trusted-draw fixed holdout also receives a pre-frozen matched permutation comparator. Its matched score delta, win rate, and e-value are diagnostic and are not used to change the locked holdout configuration.

## Interpretation

Passing this gate does **not** prove that lottery draws are predictable. It establishes that the frozen model performed better, in the specified future sample, than three predeclared comparators including one with identical portfolio geometry.
