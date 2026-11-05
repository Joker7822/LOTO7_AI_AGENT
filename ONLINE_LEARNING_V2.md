# Online Learning v2 — new genuine prospective shadow (2026-11-05 JST)

## Why this is a separate model

The existing Continuous Learning Agent v1 is permanently SHA-locked and
began prospectively at **round 701**. Its first real verified grade is
already recorded, and its **702** probability vector is frozen. Changing
that implementation would break the original scientific registration.

V2 starts a **separate**, independently preregistered sequence, first
eligible target **702** (scheduled **2026-11-06**), only if its registration
and frozen prediction are actually written **before 2026-11-06 JST**. It
must not backdate this first forecast if the deadline has already passed.

## What is enhanced

* Four fixed, prior-only experts: fair uniform, short Bayesian frequency,
  long Bayesian frequency, and shrunken momentum. Their original source
  is reused read-only.
* Three independent multiplicative-weight updates with learning rates
  **2.0, 8.0, 20.0**, exponential forgetting **0.97**.
* A second, online multiplicative-weight learner mixes the three tracks
  using an independently updated **8.0** meta-rate and **0.97** forgetting.
* A **10% prior-weight floor** prevents either layer from eliminating
  any expert or rate track.
* **30% fair-uniform inclusion-probability anchor** by default. When at
  least **four new prospectively scored** draws exist and their mean
  proper-score edge is negative, automatically use **60% uniform** for
  the next forecast. This drift guard relies only on *past* graded draws.
* All vectors are 37 finite probabilities strictly within (0,1) whose
  sum is 7; the seven ranked numbers are research telemetry only.
* Before each draw, the exact 37 probabilities, all expert vectors,
  track weights, meta weights, raw scores, and history fingerprint are
  saved in a SHA-256 hash-chained append-only event sequence.
* Once the **same target** result is independently verified, the
  previously frozen vector is scored; only then are weights updated,
  and the next target is frozen. Missing, late, untrusted, nonconsecutive,
  changed-source, or altered-code evidence refuses to backfill.

This is independent of OpenAI API, other hosted models, and external AI
inference. The only routine network requirement is obtaining verified
lottery results via the existing source-validation workflow.

## Source and evidence safety

The dedicated workflow is
[.github/workflows/online_learning_boost_v2.yml](.github/workflows/online_learning_boost_v2.yml).
It executes the synthetic lifecycle tests at every relevant PR/push, then
runs the real isolated research writer on main, daily at 10:20 JST and
after the independently corroborated result workflow.

The writer changes only:
\`research/online_learning_v2/state.json\`

It does not change \`continuous_learning_agent.py\`, its v1 evidence,
\`predictive_expert_agent.py\`, the original OOS protocols, Champion, public
ticket selection, Production, or data-source files.

The research output reports descriptive future-only proper log score,
Brier score, and prospective Top7 counts. A fair independent lottery has
the marginal 7/37 probability; **no proven advantage, causal learnability,
fixed-horizon p-values, e-value adoption, or Production authorization**
is claimed by this new adaptive learner. Repeated online monitoring is not
license to reinterpret descriptive scores as controlled statistical tests.

## Execution

    python -m pip install -r requirements.txt pytest
    python -m pytest -q tests/test_online_learning_boost_v2.py
    python online_learning_boost_v2.py --repo-root .

The initial run requires a trusted actual round 701, an attestable CSV,
a published official 702 schedule and a JST date **strictly before**
2026-11-06. If these conditions are not met, the script must fail closed
or explicitly report that it is waiting.

## Primary references

* The existing v1 permanent registration:
  [CONTINUOUS_LEARNING_AGENT.md](CONTINUOUS_LEARNING_AGENT.md).
* Cesa-Bianchi and Lugosi (2006), *Prediction, Learning, and Games*,
  Cambridge University Press, DOI 10.1017/CBO9780511546921.
* Python JSON/cryptographic evidence:
  https://docs.python.org/3/library/hashlib.html

The multi-rate combination, damping parameters and drift threshold here
are **new engineering hypotheses**, not empirical proof that lottery
sequences are predictable. They are SHA-locked before any qualifying
future grade to make that distinction auditable.
