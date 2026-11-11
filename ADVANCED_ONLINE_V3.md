# Advanced online v3 — exact fixed-size-set prospective research

**New protocol proposed 2026-11-06 JST.** This is a **separately registered
research-only online learning experiment**, not a modification of the v1 model
registered from round 701 or the v2 freeze already recorded for round 702.

## The problem: calibration is not the same as lottery evidence

Each lottery outcome contains exactly **7 distinct numbers out of 37**. The
fair-lottery null probability for each of the C(37,7) possible sets is equal.
Treating the 37 inclusion indicators as independent Bernoulli variables can
supply a descriptive proper marginal score, but is *not* the exact joint
likelihood of the actual fixed-cardinality draw. This protocol reports both.

## Algorithm

The model is an independently coded, offline Python implementation:

1. Six immutable prior-only experts: uniform, short/long smoothed frequency,
   shrunken momentum, safe AST frequency-plus-pairwise signal, and safe AST
   exponential-decay-plus-gap signal.
2. Three parallel exponential expert-weight tracks at rates **2, 8, 20**.
   A second online meta-learner reweights these tracks. The weights use
   exponential forgetting **0.97** and a fixed **10% prior floor**, so no
   expert is silently eliminated by a single anomalous result.
3. Online calibration ensemble with fixed temperatures **0.70, 1.00, 1.25**.
   Each candidate is projected to 37 probabilities in (0,1), summing to 7.
   The calibration weights are learned only from *previously verified* draws.
4. **40% fair-uniform fallback** under normal conditions. If the last **6**
   genuinely prospective marginal log-score edges average below zero,
   fallback rises to **75% fair uniform**. All settings are preregistered.
5. Every next forecast seals the 37-vector, all six constituent vectors,
   rate weights, meta weights, temperature weights, uniform fallback,
   strictly prior-only CSV fingerprint, timestamp and draw target in a
   SHA-256 chained event *before the JST target calendar date*.
6. Only two-source independently corroborated new outcomes can be scored.
   The frozen exact likelihood, observed seven numbers, and updated
   scores are saved before the next forecast is frozen. No result backfill,
   skipped target, altered source, changed algorithm or forecast edits.
7. A research-only **anytime-valid e-process** is updated from the exact
   whole-set likelihood ratio, not only the marginal Brier/log-score.

### Exact whole-set evidence

Let w_i be the odds implied by a frozen, prior-only inclusion vector, capped
within [0.25, 4], and S the actual set of 7 numbers. Define e_7(w) as the
seventh elementary symmetric polynomial (a dynamic program of 37×7 steps):

    e_7(w) = sum_{|S|=7} product_{i in S} w_i
    Q_w(S) = product_{i in S} w_i / e_7(w)
    U(S) = 1 / C(37,7)
    LR(S) = C(37,7) * Q_w(S)

Thus, when each seven-element subset is equiprobable under the null,
the conditional expectation of LR(S), given all past verified outcomes, is
exactly 1. The program does **not** claim that its original 37 probabilities
are exact inclusion marginals of the induced joint distribution. They define
a mathematically coherent alternative set distribution via odds.

Four preregistered conservative bets **0.025, 0.05, 0.10, 0.20** each update
wealth by \`(1-bet) + bet*LR\`. Their **equal-weight mixture** is a valid
test martingale for the explicitly stated fair-lottery null. By Ville's
inequality, repeatedly checking whether the e-process ever reaches **40**
has false-alarm probability at most **1/40 = 2.5%** *under that null*,
provided each frozen forecast is measurable from previous information.
A predeclared **26 verified future-draw minimum** additionally prevents
premature research-only evidence declarations. It is NOT a Production
promotion decision, evidence of profit, or general certificate of accurate
lottery forecasts.

The test only concerns the single preregistered v3 forecasting algorithm.
Choosing the best of many concurrently tested models would need additional
multiple-testing protection. Neither a normal forecast's marginal Brier
improvement nor a lower e-value is evidence of a guaranteed betting edge.

## Chronological enrollment

* **Round 702 (draw scheduled 2026-11-06)** already has a distinct v2 frozen
  forecast. It is NEVER retroactively repurposed as a v3 prediction.
* On first eligible execution, register the v3 code SHA manifest with
  **first prospective target = round 703**, before round 703 has occurred.
  If the latest verified draw is still 701, register the protocol but
  **do not issue a round-703 forecast yet**.
* After 702 is independently verified, issue the v3 round-703 probability
  vector only if the published next draw schedule can be parsed and the
  current JST date is strictly **before** its scheduled draw date.
* Continue with verified outcomes and immediate next-target freezes.
  The registration and state live only at
  \`research/advanced_online_v3/registration.json\` and
  \`research/advanced_online_v3/state.json\`.
* A missed prefreeze deadline is *not* backfilled. Changing the locked
  code requires a new experiment and new future targets.

## Deployment and scientific controls

The workflow \`.github/workflows/advanced_online_v3.yml\` tests the
future-only simulator and exact likelihood algebra for every relevant PR,
then runs the research workflow on main, once daily at **11:17 JST**,
on a new verified result workflow run, and on deployment of its code.

The automation can write only its two research files. Original
\`continuous_learning_agent_*\`, \`online_learning_v2\`, Production,
Champion, public predictions and source-validation evidence remain
unchanged. There is **no OpenAI API, hosted LLM or inference token**.

    python -m pip install -r requirements.txt pytest
    python -m pytest -q tests/test_advanced_online_v3.py
    python advanced_online_v3.py --repo-root .

The tests use an explicitly **synthetic** 701–703 draw sequence in a
temporary directory; they never insert invented draw outcomes into
\`loto7.csv\` or the real future evidence registry.

## Research references

* V. Vovk & G. Shafer, *Game-Theoretic Foundations for Probability and Finance*
  (2019), DOI 10.1002/9781118547936 — test martingales and capital processes.
* P. Grünwald, A. Henzi & T. Lardy (2024), *Anytime-Valid Tests of
  Conditional Independence Under Model-X*, JASA,
  DOI https://doi.org/10.1080/01621459.2023.2205607
* SciPy reference for the related Fisher noncentral hypergeometric family:
  https://docs.scipy.org/doc/scipy/tutorial/stats/discrete_nchypergeom_fisher.html
* Existing permanent prospective registrations:
  \`CONTINUOUS_LEARNING_AGENT.md\`, \`ONLINE_LEARNING_V2.md\`.

**Important:** the numerical rates, features, penalties, calibration
temperatures and anchors are declared engineering hypotheses. Their values
have not been justified by future draw outcomes.


## 2026-11-11: cross-run numeric stability and a rewritable latest view

A registered future forecast's SHA-256 chained original record under
`research/advanced_online_v3/state.json` must **never** be edited. It is the
scientific evidence showing what was actually frozen before that draw.

However, **the latest displayed research prediction is mutable** when the
currently valid research forecast changes. The operational wrapper
`online_v3_replay_runtime.py` provides two narrowly scoped behaviors:

- It runs the **unchanged, preregistered** `advanced_online_v3.py` model,
  preserving all source-SHA, algorithm-manifest, draw-date, SHA-chain and
  verified-result protections. It tolerates only cross-run binary64 numeric
  variation with **absolute difference no greater than 5e-13** in floating
  point fields, while requiring exact prior-history SHA, top-seven choices,
  drift state, schema, and discrete fields. A larger prediction difference
  fails closed rather than silently rewriting pre-outcome evidence.
- It **overwrites** `research/advanced_online_v3/latest_research_prediction.json`
  if the current display identity (target, frozen event SHA, top seven,
  displayed 37 probabilities) changes before the draw. Every replacement is
  recorded in a new **append-only**
  `research/advanced_online_v3/preview_revisions/revision_XXXXXX.json`,
  linked to its predecessor by SHA-256. Unchanged views are not rewritten.
  Only display-level projections are mutable: earlier frozen vectors and
  measured grades are untouched.

The preview has role
`mutable_research_preview_not_production_not_prospective_evidence`.
It is **not** a ticket purchase, Production prediction, independently
validated improvement, or an alternative registration. Any real alteration
to the algorithm requires a separately preregistered next experiment.

CI also runs the non-mutating original-703 diagnostic via
`python -m scripts.diagnose_v3_frozen_replay` and fails on material replay
drift. Current v3 operations use:

    python -m online_v3_replay_runtime --repo-root .

The original `advanced_online_v3.py` remains unmodified so the registered
source-code fingerprints and historical evidence are preserved.
