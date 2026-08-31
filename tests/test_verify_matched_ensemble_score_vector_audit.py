import matched_ensemble_score_vector_audit as audit
import verify_matched_ensemble_score_vector_audit as verify


def make_row():
    scores = [float(i) / 10.0 for i in range(32)]
    vector_json = audit.score_vector_json(scores)
    vector_sha = audit._sha256_text(vector_json)
    subject_score = audit.canonical_score(2.0)
    reference_sha = "a" * 64
    frozen_at = "2026-09-01T06:00:00+09:00"
    replay = audit._replay_metrics(float(subject_score), scores)
    record_sha = audit._audit_record_sha256(
        round_no=700,
        subject_version="candidate",
        subject_score=subject_score,
        vector_sha=vector_sha,
        reference_sha=reference_sha,
        frozen_at=frozen_at,
    )
    return {
        "round": "700",
        "candidate_version": "candidate",
        "candidate_score_canonical": subject_score,
        "ensemble_size": "32",
        "null_score_vector_json": vector_json,
        "null_score_vector_sha256": vector_sha,
        "matched_ensemble_reference_sha256": reference_sha,
        "audit_record_sha256": record_sha,
        "ensemble_mean_score_recomputed": audit.canonical_score(replay["mean_score"]),
        "percentile_midrank_recomputed": f"{replay['percentile_midrank']:.12f}",
        "permutation_p_upper_recomputed": f"{replay['permutation_p_upper']:.12f}",
        "matched_ensemble_frozen_at_jst": frozen_at,
        "audit_version": audit.VERSION,
    }


def test_verify_row_accepts_valid_replay_and_rejects_tampering():
    row = make_row()
    result = verify.verify_row(row, "formal")
    assert result["ok"] is True
    assert result["errors"] == []

    tampered = dict(row)
    tampered["null_score_vector_json"] = tampered["null_score_vector_json"].replace("0.5", "0.6", 1)
    bad = verify.verify_row(tampered, "formal")
    assert bad["ok"] is False
    assert "score_vector_sha256_mismatch" in bad["errors"]
