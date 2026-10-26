# Online Research → Operational Quality Audit

This component turns the existing **online literature discovery / application
readiness queue** into actionable **scientific operations checks**, without
running any unreviewed model method and without claiming better lottery
prediction accuracy.

**Important distinction:** previous Crossref/OpenAlex collection captured
DOI/title/year bibliographic metadata and some short abstracts only. It did
NOT establish peer review, reproducibility or applicability to fair,
independent lottery draws. The new audit uses its *research topics*, **not**
unverified paper algorithms, as its source of operations practice.

## Current practical value

- Compare the current, **independently verified** lottery CSV and its exact
  SHA-256 with the source-validation report, the existing research-cycle
  guard, literature application readiness, proposals and scientific summary.
  Flag any stale snapshot. A stale scientific review can never silently be
  labelled current.
- Turn five discovery topics into fixed human-authored **operational
  controls**: prequential test-before-train, calibration proper scores,
  selection-bias precautions, protected prospective e-evidence, shift/source
  freshness, and like-for-like ensemble comparisons.
- Display progress in *existing, unchanged* fixed 26-draw holdout and
  Joint Set v2 future OOS, and in the independent 35-number disjoint research
  stream. **0/26 is not proof of an improvement**.
- Independently recompute the exact geometry null from source: five
  nonoverlapping tickets (35 distinct numbers) against the one shared Top1
  option (34 distinct numbers). Under a fair 7-of-37 draw, the expected
  composite scores are approximately **2.952151** and **2.941706**,
  respectively. This advantage is ticket geometry, not prediction of which
  numbers will be drawn. Five distinct tickets always have the same
  first-prize probability.
- Highlight any failure to verify papers, authorization, already-frozen
  predictions, or a 26-draw horizon. **No new optimizer budget, automatic
  Champion promotion or Production ticket change**.

## Operational command

```bash
python -m pip install -r requirements.txt pytest
python -m pytest -q tests/test_online_research_operational_audit.py
python online_research_operational_audit.py --repo-root .
```

Output, in ignored/generated `research_output/` only:

- `online_research_operational_audit.json` — machine-readable blockers,
  source and science SHA matches, existing future-OOS progress and safe next
  step.
- `online_research_operational_audit.md` — human-readable operations
  checklist suitable for GitHub Actions job summaries.

Read-only workflow:
`.github/workflows/online_research_operational_audit.yml`.

It runs on manual dispatch, PRs affecting this feature, and as a daily
best-effort schedule at 12:45 JST; uploads a 30-day downloadable Actions
artifact. It uses read-only permissions, refuses stale/unverified sources,
and never stages or pushes any repository file.

## Meaning of a stale online finding

For example, validated latest lottery result **#700** and an online
application-readiness file based on **#699** must produce
`online_research_readiness_stale`. The current advanced statistics summary
is also historically pinned to an earlier SHA and is similarly marked
stale. These are **separate** from the verified actual result source.

The appropriate action is to refresh the scientific diagnostics using the
**existing authorized pipeline with its existing SHA and trial-budget
guards**. Do not fabricate a retrospective OOS, rewrite a registered
analysis, reset the history-search trial budget, or ignore `WAIT_FOR_NEW_DATA`
merely because a paper's title sounds promising.

## Governance

`online_research_operational_audit.py` imports existing source-validation
and immutable frozen-portfolio guard code. It refuses any paper/proposal
record that grants unreviewed execution or Production rights. It never reads
future results to generate forecast tickets, and never touches the canonical
Production publisher, Sakura database sync, model Champion, or preregistered
Future-OOS ledgers.

The operational report is **not** evidence of improved prediction skill or
expected financial returns. Truly new model experiments still require
verified full-text methodology and licensing, explicit review, a fresh
prospectively registered protocol, and genuinely future results.
