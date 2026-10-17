# Joint Set v2 — Continuous Rank Bonus Outer Time Split

- evaluation draws: **60**
- train / holdout: **40 / 20**
- predeclared weights: **[0.0, 0.02, 0.04, 0.08, 0.12]**
- selected rank weight from train only: **0.0000**
- holdout result used for weight selection: **NO**
- Production promotion eligible: **NO**

## Holdout (last 20 draws, frozen weight)
- selected score: **3.0730**
- unrestricted score: **3.0730**
- random score: **2.7772**
- delta vs unrestricted: **+0.0000** (95% CI +0.0000〜+0.0000)
- delta vs random: **+0.2958** (95% CI -0.1572〜+0.7443)
- round win rate vs unrestricted: **0.00%**
- mean continuous rank score: **0.5217**

## Holdout paired number-identity permutation
- permutations: **4096**
- observed score: **3.0730**
- permuted mean: **2.8157**
- identity edge: **+0.2573**
- upper-tail p: **0.126678**
- null p95/p99: **3.2016 / 3.3726**

> rank weight is chosen once from the first 40 evaluation draws and frozen for the final 20.
> This is a historical outer split, not pristine independent Future OOS evidence; the research concept was developed after prior analysis of this dataset family.
