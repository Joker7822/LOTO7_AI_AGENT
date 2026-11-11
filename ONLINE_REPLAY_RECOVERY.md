# LOTO7 online v2/v3 integrity and preview policy
## Operations incident and repair — 2026-11-12 JST

### Observed incident
- 2026-11-11 16:48 JST, online learning v2 (GitHub Actions run
  [42982240442](https://github.com/Joker7822/LOTO7_AI_AGENT/actions/runs/42982240442))
  failed with `online frozen prediction or prefix was tampered`.
- 2026-11-11 18:30 JST, advanced online v3 (run
  [42995703801](https://github.com/Joker7822/LOTO7_AI_AGENT/actions/runs/42995703801))
  failed with `frozen probabilities or history have changed`.
- On a controlled later retry with the pinned date-702 result prefix, v3
  replay differences were *zero*. This excludes a reproducible corruption
  in that specific later run, but **does not establish the historical
  root cause** of the initial failure. NumPy/BLAS versions and reduction
  order were not frozen originally.

### Operational repair
- The pre-registered scripts `online_learning_boost_v2.py` and
  `advanced_online_v3.py` are byte-for-byte unchanged.
- v2 operations use `python -m online_v2_replay_runtime` and v3 uses
  `python -m online_v3_replay_runtime`, preserving their existing
  registration and immutable SHA-256 event chain.
- Previously registered freeze/grade events are independently recalculated.
  **Only** a change in float fields within absolute 5e-13 is permitted;
  all recorded integers, top-seven choices, exact prior-history SHA,
  drift state, field schema, schedules, event hashes and grades remain
  strictly checked. The actual recorded numeric values are retained
  verbatim for verification. Larger differences STOP the operation.
- Any newly issued future forecast is computed freshly by the registered
  algorithm from the verified historical prefix. Earlier forecasts and
  results cannot be rewritten, retrospectively backfilled or silently
  regraded.
- The online scientific jobs alone install versions from
  `requirements-online-research.lock`: CPython 3.12.16; NumPy 2.5.4;
  pandas 2.3.3; associated pure-Python packages at fixed versions.
  OpenBLAS, OMP, MKL and Numexpr threads are set to 1 before importing
  NumPy. Other research and Production workflows retain their own
  requirements. These pins increase reproducibility but do not
  cryptographically pin wheels, OS images, or BLAS builds.
- `python -m scripts.audit_online_replay_environment` emits precise
  runtime versions and verifies all registered online research chains
  **without writing to them**. Controlled synthetic tests include
  deliberate tampering, history/SHA changes, material prediction changes,
  microscopic floating point perturbations and forbidden backfills.

### Versioned mutable display vs scientific evidence
The website-facing current v3 research preview is
`research/advanced_online_v3/latest_research_prediction.json`.
It can be replaced **only by a new audited revision**. Each revision is
archived in `research/advanced_online_v3/preview_revisions/` and linked
by SHA-256 to the previous one. Reading the current preview does not
confer Production approval, purchase authorization or research skill.
The preview's `identity.view_status` becomes
`expired_on_or_after_draw_day` on the scheduled draw's JST calendar
date (unless a genuinely fresh future target has already been frozen).
An expired preview is **not** a current purchasing recommendation. The
original frozen prediction remains available for future scoring.

### Prospective validity and scientific limit
- v2's first valid target was 702. The grade for 702 and future freeze
  for 703 are part of the separately authenticated v2 record.
- v3's original first valid target was 703; it has **zero** prospective
  verified grades as of this repair. It is still research-only.
- A passing CI run verifies *engineering integrity*, not an empirical
  forecasting advantage, higher winning probability or permission for
  Production promotion.
