# Joint Set v2 — Continuous Rank Bonus Outer Time Split

- evaluation draws: **60**
- train / holdout: **40 / 20**
- predeclared weights: **[0.0, 0.02, 0.04, 0.08, 0.12]**
- selected rank weight from train only: **0.0000**
- holdout result used for weight selection: **NO**
- Production promotion eligible: **NO**

## Holdout (last 20 draws, frozen weight)
- selected score: **2.9150**
- unrestricted score: **2.9150**
- random score: **2.7772**
- delta vs unrestricted: **+0.0000** (95% CI +0.0000〜+0.0000)
- delta vs random: **+0.1378** (95% CI -0.2662〜+0.5503)
- round win rate vs unrestricted: **0.00%**
- mean continuous rank score: **0.5470**

## Holdout paired number-identity permutation
- permutations: **4096**
- observed score: **2.9150**
- permuted mean: **2.8249**
- identity edge: **+0.0901**
- upper-tail p: **0.332682**
- null p95/p99: **3.2194 / 3.3790**

> rank weight is chosen once from the first 40 evaluation draws and frozen for the final 20.
> This is a historical outer split, not pristine independent Future OOS evidence; the research concept was developed after prior analysis of this dataset family.
