# Sakura credential rotation and prospective-evidence audit

Updated: 2026-10-31 JST. This is an operational audit and runbook, **not** evidence that a secret was rotated or that a model predicts lotteries.

## Immediate security state

- Public incident: [GitHub issue #45](https://github.com/Joker7822/LOTO7_AI_AGENT/issues/45), opened 2026-09-06.
- Canonical status: `loto7_agent_output/sakura_credential_rotation_status.json`.
- At the time of this change, the canonical status is `pending_external_rotation_verification`. Completion **has not been independently verified**.
- The repository must not include or print any former/new MySQL password or HMAC secret.
- All non-dry-run `prediction_db_sync.py` commands now require both:
  1. `rotation_attested_and_live_verified` status with successful HMAC, generation-match and DB-transaction checks;
  2. a nonempty `sakura/credential_generation.txt` pin matching both the status and the generation used for the request.
- Dry-run payload validation is unaffected. `verify_sakura_rotation.py` performs its dedicated empty live transaction without relying on a prior status.

## Required actions outside this repository (owner / Sakura administrator)

1. Rotate the Sakura MySQL password **on Sakura**, not in GitHub.
2. Rotate the HMAC secret **on Sakura** and change the endpoint to accept the new secret.
3. Configure a new, non-secret `credential_generation` identifier on the Sakura endpoint.
4. Update GitHub Actions secrets `SAKURA_PREDICTION_API_URL` (HTTPS endpoint) and `SAKURA_PREDICTION_HMAC_SECRET` (new secret). Do not place either value in workflow YAML, issues, logs or Markdown.
5. Run **Verify Sakura Credential Rotation** manually. Provide the new generation identifier and truthful timestamp evidence for both rotations after 2026-09-06T08:56:30Z.
6. Verify the workflow wrote the status `rotation_attested_and_live_verified` and the matching public generation pin. Its live check requires a signed API request, a matching generation and a DB transaction.
7. Ensure old credentials are disabled or revoked using trusted administrative access. The verifier does **not** itself demonstrate that the former credentials are rejected; it records an attestation. Close issue #45 only after the required external steps are confirmed.
8. Rerun the regular Sakura sync workflow; never bypass the verification gate to force network transmission.

If the external steps have not been executed, **do not mark the incident resolved**. This repository change alone cannot rotate credentials on Sakura.

## Regression / safeguards

```bash
python -m pytest -q tests/test_prediction_db_sync.py tests/test_verify_sakura_rotation.py tests/test_weekly_production_schedule.py
python prediction_db_sync.py --dry-run --output /tmp/sakura_payload.json
```

Both weekly publisher workflows source the endpoint from the GitHub secret instead of embedding a URL. The sync preflight rejects missing status, pending verification, missing pin and generation mismatch. The verification workflow is intentionally separate from the network sync gate.

## Fixed 26-draw Future OOS: inference boundary

- The existing 26-trusted-draw holdout is retained without resetting candidates, scored outcomes, SHA lock or geometry.
- As of 2026-10-31, `confirmation_policy_registered_at_trusted_draws` is **4** in the archived state: the final confirmation rule was recorded after four trusted outcomes.
- A SHA-locked rule **after** observations is integrity evidence from that point forward, not evidence it was preregistered before the first outcome.
- `future_holdout_evidence.py` now reports this timing as an explicit field. Even if all metrics pass at 26 draws, it cannot emit `confirmed_operational_future_oos_edge` for an incomplete or late-registered confirmation policy.
- This is a **conservative reporting rule**, not an attempt to erase or re-grade the previous results. The original holdout remains a diagnostic study.
- A new, separately preregistered confirmation study would require its own protocol registered before its first outcome. It must not reuse the completed samples from the previous holdout as genuinely new evidence.

## Environment reproducibility

CI records Python package versions from its run in an artifact. This does not replace fully pinned dependencies, wheels and hashes. Before changing NumPy/Pandas versions, establish a separate compatibility baseline: compare deterministic old-replay outputs, output hashes, and all prospective-ledger safety tests. Never update an existing prospective ledger to match a newly installed dependency.
