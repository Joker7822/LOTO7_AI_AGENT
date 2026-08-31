# Matched Ensemble Score Vector Audit

## Purpose

This audit layer makes each prospective matched-ensemble rank result independently reproducible from persisted artifacts.

It does **not** change the Production promotion gate. Champion, Uniform Random, and the 32-member Matched Ensemble remain the inferential comparators. The score-vector audit is diagnostic and integrity-focused only.

## Pre-result commitment

Before a target result is available, the system hashes the exact ordered 32-member matched ensemble already frozen for that target.

For the Formal Challenger the hash is stored in:

- `shadow_registry.json -> matched_ensemble_reference_sha256_by_candidate`

For the fixed holdout it is stored in:

- `future_holdout_registry.json -> matched_ensemble_reference_sha256`

The hash covers member order, ticket order, and the sorted number labels within every ticket. This binds later score vectors to the exact pre-frozen portfolio ensemble.

## Score vector after grading

After a target result is verified, the system scores all 32 pre-frozen matched portfolios and persists the ordered vector.

The canonical vector representation is a compact JSON array of **binary64 round-trip decimal strings** using Python format `.17g`. No randomization occurs at grading time.

Formal output:

- `loto7_agent_output/matched_ensemble_score_vector_audit.csv`

Holdout output:

- `loto7_agent_output/future_holdout_matched_ensemble_score_vector_audit.csv`

Each row contains:

- the observed Challenger/Holdout score;
- all 32 ordered null scores;
- SHA-256 of the canonical score-vector JSON;
- SHA-256 of the pre-frozen 32-member reference;
- a second audit-record SHA-256 binding round, subject version, subject score, reference hash, vector hash, and freeze timestamp;
- recomputed ensemble mean score;
- recomputed percentile mid-rank;
- recomputed one-sided Monte-Carlo permutation p-value;
- a replay-verification flag.

## Hash definitions

### Score vector hash

`SHA256(canonical_score_vector_json_utf8)`

where the vector JSON is order-preserving and whitespace-free.

### Reference hash

`SHA256(canonical_ordered_32_portfolios_json_utf8)`

### Audit record hash

The record hash is SHA-256 of canonical sorted-key JSON containing:

- audit version;
- round;
- subject version;
- canonical observed score;
- ensemble size;
- matched-ensemble freeze timestamp;
- pre-frozen reference SHA-256;
- realized score-vector SHA-256.

This prevents a valid score vector from being silently rebound to another target round or candidate.

## Independent verification

Run:

```bash
python verify_matched_ensemble_score_vector_audit.py
```

The verifier independently checks every persisted audit row and exits non-zero if it finds:

- score-vector SHA mismatch;
- audit-record SHA mismatch;
- ensemble-size mismatch;
- mean-score replay mismatch;
- percentile replay mismatch;
- permutation-p replay mismatch;
- audit-version mismatch.

The verifier requires no new random draws and operates only on persisted audit CSV data.

## Governance

The audit layer is explicitly `diagnostic_only`.

A hash or replay failure is surfaced as an audit-integrity failure, but the statistical Production promotion thresholds themselves are unchanged. The sequential e-process remains the inferential Future-OOS gate.
