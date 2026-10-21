# Literature Review & Experiment Design Agents

This subsystem is **deterministic scholarly-metadata triage and experiment proposal generation**. It is not a model-based full-text analysis system, peer review, external-code execution, or permission to modify any forecast.

The existing hourly agent uses a fixed list of safe topics to query Crossref/OpenAlex. The new reviewer checks the SHA256-chained hourly audit log and requires each displayed DOI, title and year to match the originally logged discovery. Missing, forged or mutated bibliographic evidence raises an error instead of silently assigning research credibility.

## Paper reviewer

It produces research_literature_reviews.json, containing a reproducible topic taxonomy and bounded triage priority for each supported DOI. Only the six categories below are recognized: calibration, online evaluation, anytime-valid evidence, distribution shift, selection bias and ensemble methods.

Importantly, a title and DOI alone **cannot** establish that the article is sound, peer reviewed, reproducible or suitable for a fair lottery. The result explicitly labels all papers metadata_triage_only, full_text_examined=false, peer_review_verified=false and lottery_applicability_verified=false. Score represents **reading priority, not expected prediction accuracy**. All outside metadata remains untrusted input.

## Experiment designer

It produces research_experiment_proposals.json. The planner selects only fixed, human-authored experiment-design templates, indexed by the metadata review category. Each draft includes:

- A falsifiable hypothesis and preregistered primary metric
- A strictly fair independent 7-of-37 benchmark
- Prequential chronological scoring, complete optimizer-budget and candidate-selection correction, identical compute budgets
- Conditions for stopping if a frozen prediction, source trust, model/data SHA or existing research budget is inconsistent
- A requirement for **new, non-overlapping truly future outcomes**, separate pre-registration, methodological review, and explicit human approval

The proposed plans cannot run anything, cannot grant trials or reset the guard, cannot register OOS, cannot change Champion/Production or the existing fifth-expert/v2/adaptive OOS books. A WAIT_FOR_NEW_DATA guard is respected and reported.

## Workflows, scope and data

Existing .github/workflows/always_on_accuracy_research.yml now runs the paper reviewer and experiment designer **after** the original hourly audit. Existing research agent SHA-chain remains immutable; the workflow stages only its three existing owned files and three new report files:

- loto7_agent_output/research_literature_reviews.json
- loto7_agent_output/research_experiment_proposals.json
- loto7_agent_output/research_literature_review_report.md

Existing experimental registrations, the actual draw CSV, any OOS ledger and Production are untouched.

## Testing

    python -m compileall -q .
    python -m pytest -q
    python -m pytest -q tests/test_always_on_accuracy_agent.py tests/test_research_literature_pipeline.py
    python research_literature_pipeline.py --repo-root .

Tests cover real-world transition from VALIDATION_ONLY to WAIT_FOR_NEW_DATA without reopening search, all three allowed guard modes, unsafe search-mode mismatches, forged titles/DOIs, tampering with SHA-chained evidence, no-source results, prompt-injection-like metadata, proposal invariants, protected-file immutability and output determinism.

Note: this improves *research governance and evaluation workflow*, not verified future lottery accuracy. A random 7-of-37 draw does not become more predictable because more papers have been searched.
