# Production: Champion-ranked disjoint 35 (from draw 705)

Updated: 2026-11-22 JST. This is a **ticket selection change**, not proof of
predictive skill or authorization to promote a research model.

## Exact rule

- Effective for **new, not-yet-frozen Production targets from draw 705 onward**.
  Draw 702-704 use the existing `production-disjoint35-layout-v1` policy.
  A previously frozen target, including a legacy-layout draw 705 or later,
  is only republished from the immutable canonical ledger.
- Use the **currently approved Production Champion** and the verified
  `loto7.csv` history through the preceding completed draw. Reject missing
  or inconsistent Champion identity; do not substitute the current Research Winner.
- Compute the Champion's final 37-number probability ranking using the existing
  `walk_forward_evolve` + `final_score` pipeline with the Champion's
  `eta`, `decay`, `expert_uniform_mix`, and `final_uniform_mix`.
  Data from the target draw is unavailable and must never be used.
- Sort by **descending final score**, breaking ties by **ascending numeric label**.
  Select exactly ranks **1 through 35**; exclude ranks **36 and 37**.
- Make five non-overlapping tickets by sorting each consecutive rank block
  numerically: **1-7 / 8-14 / 15-21 / 22-28 / 29-35**.
  The five seven-number combinations are disjoint and cover exactly 35 labels.
- Mark each new issued row with
  `production-ai-ranked-disjoint35-layout-v1` in `model_version`.
  Keep legacy frozen v1 rows valid for historical reconciliation and DB sync.
- Store the full 37-number rank, excluded numbers, the model/data identity,
  and the SHA-256 rank-record fingerprint in the Production state.
  Write the exact model ranking to `prediction_ranking.csv`.
  Retain the existing pre-freeze trusted two-source gate and canonical append-only
  issuer checks. Do not edit previously issued predictions.

## Limits / interpretation

- **This does not increase the 1st-prize probability of five distinct tickets**
  under an independent fair 7-of-37 draw:
  `5 / C(37, 7) = 5 / 10,295,472`.
- Ranking-based selection does not imply calibrated marginal probabilities,
  observed expected-value improvement, or a verified predictive advantage.
- No alteration to Champion promotion gates, prospective OOS registries,
  research candidates or previous scores.
- Only merge after CI and reviewer approval. The first post-merge
  not-yet-frozen Friday target will use this ranking rule.

## Verification

```bash
python -m pytest -q tests/test_production_ai_ranked35.py \
  tests/test_production_ticket_geometry35.py \
  tests/test_production_disjoint35_policy.py \
  tests/test_weekly_production_schedule.py
```
