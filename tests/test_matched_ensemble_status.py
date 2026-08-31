import matched_ensemble_status as status


def test_render_matched_ensemble_progress():
    ref_hash = "a" * 64
    holdout_ref_hash = "b" * 64
    vector_hash = "c" * 64
    record_hash = "d" * 64
    registry = {
        "target_round": 693,
        "matched_ensemble_version": "matched-permutation-ensemble-v1",
        "matched_ensemble_size": 32,
        "matched_ensemble_frozen_at_jst": "2026-08-31T20:00:00+09:00",
        "matched_reference_frozen_at_jst": "2026-08-31T15:59:33+09:00",
        "matched_ensemble_reference_sha256_by_candidate": {"candidate": ref_hash},
        "matched_ensemble_score_vector_audit_version": "matched-ensemble-score-vector-audit-v1",
        "champion_version": "champion",
    }
    oos = {
        "matched_ensemble_score_vector_audit_version": "matched-ensemble-score-vector-audit-v1",
        "matched_ensemble_score_vector_hash_algorithm": "sha256",
        "matched_ensemble_score_vector_canonical_float": ".17g",
        "evidence": {
            "k": {
                "candidate_version": "candidate",
                "champion_version": "champion",
                "matched_ensemble_trusted_draws": 4,
                "matched_ensemble_sum_delta": 0.8,
                "matched_ensemble_wins": 3,
                "matched_ensemble_e_value_raw": 1.7,
                "family_adjusted_e_value": 0.85,
                "matched_ensemble_score_vector_audit_status": "active",
                "last_matched_ensemble_score_vector_audit_round": 693,
                "last_matched_ensemble_score_vector_sha256": vector_hash,
                "last_matched_ensemble_audit_record_sha256": record_hash,
                "last_matched_ensemble_score_vector_replay_verified": True,
            }
        },
    }
    formal = {"candidate_version": "candidate", "champion_version": "champion"}
    holdout = {
        "horizon_trusted_draws": 26,
        "matched_ensemble_trusted_draws": 3,
        "sum_delta_vs_matched_ensemble": -0.3,
        "wins_vs_matched_ensemble": 1,
        "matched_ensemble_e_value": 0.9,
    }
    holdout_registry = {
        "matched_ensemble_frozen_at_jst": "2026-08-31T20:00:00+09:00",
        "matched_ensemble_reference_sha256": holdout_ref_hash,
    }
    text = "\n".join(status.render(registry, oos, formal, holdout, holdout_registry))
    assert "Ensemble size: **32**" in text
    assert "Promotionで使用: **YES**" in text
    assert "4/8回" in text
    assert "+0.2000" in text
    assert "75.0%" in text
    assert "3/26" in text
    assert "-0.1000" in text
    assert "33.3%" in text
    assert "旧single Matched" in text
    assert "Ensemble Score Vector Audit" in text
    assert "Score vector監査版: **matched-ensemble-score-vector-audit-v1**" in text
    assert ref_hash in text
    assert holdout_ref_hash in text
    assert vector_hash in text
    assert record_hash in text
    assert "直近rank/p replay一致: **YES**" in text
