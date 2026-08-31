import csv
import json
from pathlib import Path

import loto7_v4_runner as v4
import matched_ensemble_rank_diagnostics as rank
import matched_ensemble_score_vector_audit as audit
import matched_permutation_ensemble as ensemble


def sample_tickets():
    return [
        [1, 2, 3, 4, 5, 6, 7],
        [1, 2, 8, 9, 10, 11, 12],
        [1, 3, 8, 13, 14, 15, 16],
        [2, 4, 9, 13, 17, 18, 19],
        [5, 6, 10, 14, 17, 20, 21],
    ]


def test_score_vector_canonicalization_roundtrips_and_hashes_order():
    scores = [0.1, 1.0 / 3.0, 2.75, 8.8]
    canonical = audit.canonical_score_vector(scores)
    assert [float(x) for x in canonical] == [float(x) for x in scores]
    text = audit.score_vector_json(scores)
    assert text == json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    h1 = audit.score_vector_sha256(scores)
    h2 = audit.score_vector_sha256(scores)
    assert h1 == h2
    assert len(h1) == 64
    assert audit.score_vector_sha256(list(reversed(scores))) != h1


def test_reference_hash_binds_member_order_and_tickets():
    tickets = sample_tickets()
    members = ensemble._ensemble_for_tickets(tickets, ensemble.permutations_for_round(700))
    h1 = audit.reference_sha256(members)
    assert h1 == audit.reference_sha256(members)
    assert len(h1) == 64
    swapped = list(members)
    swapped[0], swapped[1] = swapped[1], swapped[0]
    assert audit.reference_sha256(swapped) != h1


def test_bootstrap_precommits_formal_and_holdout_reference_hashes(tmp_path: Path):
    out = tmp_path / "out"
    out.mkdir()
    tickets = sample_tickets()
    members = ensemble._ensemble_for_tickets(tickets, ensemble.permutations_for_round(700))
    shadow = tmp_path / "shadow_registry.json"
    shadow.write_text(json.dumps({
        "target_round": 700,
        "matched_ensemble_frozen_at_jst": "2026-09-01T06:00:00+09:00",
        "matched_ensemble_by_candidate": {"candidate": members},
        "candidates": [{"version": "candidate", "tickets": tickets}],
    }), encoding="utf-8")
    (out / "future_holdout_registry.json").write_text(json.dumps({
        "target_round": 700,
        "holdout_tickets": tickets,
        "matched_ensemble_tickets": members,
        "matched_ensemble_frozen_at_jst": "2026-09-01T06:00:00+09:00",
    }), encoding="utf-8")
    (out / "future_holdout_state.json").write_text(json.dumps({
        "locked_candidate_version": "candidate",
    }), encoding="utf-8")
    (out / "oos_candidate_state.json").write_text("{}", encoding="utf-8")
    csv_path = tmp_path / "loto7.csv"
    csv_path.write_text(
        "回別,抽せん日,本数字1,本数字2,本数字3,本数字4,本数字5,本数字6,本数字7\n"
        "692,2026-08-28,1,2,3,4,5,6,7\n",
        encoding="utf-8",
    )

    result = audit.bootstrap_before_main(v4, [
        "--csv", str(csv_path),
        "--out-dir", str(out),
        "--shadow-registry", str(shadow),
    ])
    assert result["registry_reference_hash_ready"] is True
    assert result["holdout_reference_hash_ready"] is True
    assert result["promotion_role"] == "diagnostic_only"

    registry = json.loads(shadow.read_text(encoding="utf-8"))
    expected = audit.reference_sha256(members)
    assert registry["matched_ensemble_reference_sha256_by_candidate"]["candidate"] == expected
    holdout_registry = json.loads((out / "future_holdout_registry.json").read_text(encoding="utf-8"))
    assert holdout_registry["matched_ensemble_reference_sha256"] == expected


def test_formal_score_vector_audit_replays_rank_and_writes_hashes(tmp_path: Path):
    out = tmp_path / "out"
    out.mkdir()
    result_path = out / "shadow_oos_results.csv"
    tickets = sample_tickets()
    members = ensemble._ensemble_for_tickets(tickets, ensemble.permutations_for_round(700))
    ref_hash = audit.reference_sha256(members)
    registry = {
        "target_round": 700,
        "champion_version": "champion",
        "matched_ensemble_frozen_at_jst": "2026-09-01T06:00:00+09:00",
        "matched_ensemble_by_candidate": {"candidate": members},
        "matched_ensemble_reference_sha256_by_candidate": {"candidate": ref_hash},
        "candidates": [{"version": "candidate", "tickets": tickets}],
    }
    key = v4.e_key("candidate", "champion")
    state = {"evidence": {key: {"candidate_version": "candidate", "champion_version": "champion"}}}
    actual = set(range(1, 8))

    rank._grade_rank(
        v4, registry, 700, "2026-10-23", actual,
        "verified_two_result_sources", True, state, result_path,
    )
    audit._grade_audit(
        v4, registry, 700, "2026-10-23", actual,
        "verified_two_result_sources", True, state, result_path,
    )

    rec = state["evidence"][key]
    assert rec["matched_ensemble_score_vector_audit_status"] == "active"
    assert rec["last_matched_ensemble_score_vector_replay_verified"] is True
    assert rec["matched_ensemble_score_vector_audit_trusted_draws"] == 1
    assert len(rec["last_matched_ensemble_score_vector_sha256"]) == 64
    assert len(rec["last_matched_ensemble_audit_record_sha256"]) == 64
    assert rec["last_matched_ensemble_reference_sha256"] == ref_hash

    path = out / "matched_ensemble_score_vector_audit.csv"
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    assert len(rows) == 1
    row = rows[0]
    vector = json.loads(row["null_score_vector_json"])
    assert len(vector) == 32
    assert audit._sha256_text(row["null_score_vector_json"]) == row["null_score_vector_sha256"]
    assert row["matched_ensemble_reference_sha256"] == ref_hash
    assert row["replay_verified"] == "true"


def test_audit_rejects_reference_hash_mismatch(tmp_path: Path):
    out = tmp_path / "out"
    out.mkdir()
    result_path = out / "shadow_oos_results.csv"
    tickets = sample_tickets()
    members = ensemble._ensemble_for_tickets(tickets, ensemble.permutations_for_round(700))
    registry = {
        "target_round": 700,
        "champion_version": "champion",
        "matched_ensemble_frozen_at_jst": "2026-09-01T06:00:00+09:00",
        "matched_ensemble_by_candidate": {"candidate": members},
        "matched_ensemble_reference_sha256_by_candidate": {"candidate": "0" * 64},
        "candidates": [{"version": "candidate", "tickets": tickets}],
    }
    key = v4.e_key("candidate", "champion")
    state = {"evidence": {key: {"candidate_version": "candidate", "champion_version": "champion"}}}

    audit._grade_audit(
        v4, registry, 700, "2026-10-23", set(range(1, 8)),
        "verified_two_result_sources", True, state, result_path,
    )
    assert state["evidence"][key]["matched_ensemble_score_vector_audit_status"] == "invalid_reference_hash_mismatch"
    assert not (out / "matched_ensemble_score_vector_audit.csv").exists()


def test_holdout_score_vector_audit_writes_replayable_vector(tmp_path: Path):
    out = tmp_path / "out"
    out.mkdir()
    tickets = sample_tickets()
    members = ensemble._ensemble_for_tickets(tickets, ensemble.permutations_for_round(700))
    ref_hash = audit.reference_sha256(members)
    registry = {
        "target_round": 700,
        "holdout_tickets": tickets,
        "matched_ensemble_tickets": members,
        "matched_ensemble_frozen_at_jst": "2026-09-01T06:00:00+09:00",
        "matched_ensemble_reference_sha256": ref_hash,
    }
    state = {"locked_candidate_version": "candidate"}
    (out / "future_holdout_registry.json").write_text(json.dumps(registry), encoding="utf-8")
    (out / "future_holdout_state.json").write_text(json.dumps(state), encoding="utf-8")
    actual = set(range(1, 8))

    rank._grade_holdout_rank(
        v4, out, 700, "2026-10-23", actual,
        "verified_two_result_sources", True,
    )
    audit._grade_holdout_audit(
        v4, out, 700, "2026-10-23", actual,
        "verified_two_result_sources", True,
    )
    updated = json.loads((out / "future_holdout_state.json").read_text(encoding="utf-8"))
    assert updated["matched_ensemble_score_vector_audit_status"] == "active"
    assert updated["last_matched_ensemble_score_vector_replay_verified"] is True
    assert updated["matched_ensemble_score_vector_audit_trusted_draws"] == 1
    rows = list(csv.DictReader((out / "future_holdout_matched_ensemble_score_vector_audit.csv").open(encoding="utf-8")))
    assert len(json.loads(rows[0]["null_score_vector_json"])) == 32
    assert rows[0]["replay_verified"] == "true"
