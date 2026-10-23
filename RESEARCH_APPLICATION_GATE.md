# Autonomous research: online discovery → validation → application readiness

The Research Application Gate connects the existing hourly evidence-gathering and
scientific-method sandbox to an actionable, **human-reviewed** research backlog.

## Stages

1. **Online search:** bounded Crossref/OpenAlex queries. All DOI/title/year
   metadata remain untrusted until checked against the SHA256-chained activity journal.
2. **Research review:** classify title-only metadata into fixed calibration,
   online learning, anytime evidence, drift, selection bias and ensemble topics.
   No full-text review, peer-review verification or validated lottery relevance is claimed.
3. **Scientific validation:** independently corroborate DOI/title/year where
   both providers are available, and inspect the existing 512-world fair
   7-of-37 Monte Carlo smoke test.
4. **Exact mathematical control:** verify that the fixed biased probability
   vector loses expected Bernoulli proper log/Brier score against the fair
   uniform 7/37 baseline. The expected log-score difference is negative
   averaged Bernoulli KL divergence; the expected Brier difference is negative
   average squared marginal probability error. The expected frozen e-factor
   is exactly 1 under independent uniform draws. The finite simulation is
   tested against those values as a sanity check, NOT real-world evidence.
5. **Application readiness:** match every approved-by-nobody experimental
   draft to independent bibliographic verifications. Output only a work queue
   for verification or human full-text/methodological review.
6. **Monitoring:** project safe statuses and counts into the existing atomic
   dashboard snapshot, with stale/unsafe evidence hidden. New public screen:
   研究成果の実用化ゲート.

## Permissions

Allowed: search, inspect bibliography, reproduce fixed fair-world methodology
sanity checks, produce a deterministic audit/readiness report and human backlog.

Forbidden: automatically running new real model experiments, resetting budget,
modifying prospective pre-frozen vectors or prediction ledgers, changing draw
history, promoting Champion or publishing Production. WAIT_FOR_NEW_DATA and
unverified lottery results remain protected.

The only two new research artifacts are:

- loto7_agent_output/research_application_readiness.json
- loto7_agent_output/research_application_readiness_report.md

The separate dashboard workflow alone updates docs/data/dashboard_snapshot.json.
Future predictive skill is still unproven. Full papers, code/license, explicit
human approval and separately preregistered genuinely future evaluation would
be necessary for an experimental method to become a new model candidate.

## Validate

    python -m pytest -q tests/test_research_application_gate.py
    python -m pytest -q tests/test_dashboard_status_snapshot.py
    node --test docs/tests/research-application.test.mjs
    python research_application_gate.py --repo-root .

Fail closed on forged references, modified research plans, unavailable
verifications, incorrect synthetic controls, or unauthorized execution rights.
