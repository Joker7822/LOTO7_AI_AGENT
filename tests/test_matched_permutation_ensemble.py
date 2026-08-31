import json
from pathlib import Path

import loto7_v4_runner as v4
import matched_permutation_ensemble as ensemble
import matched_permutation_oos as single


def sample_tickets():
    return [
        [1, 2, 3, 4, 5, 6, 7],
        [1, 2, 8, 9, 10, 11, 12],
        [1, 3, 8, 13, 14, 15, 16],
        [2, 4, 9, 13, 17, 18, 19],
        [5, 6, 10, 14, 17, 20, 21],
    ]


def test_ensemble_is_deterministic_unique_and_preserves_legacy_member_zero():
    tickets = sample_tickets()
    permutations1 = ensemble.permutations_for_round(693)
    permutations2 = ensemble.permutations_for_round(693)
    assert permutations1 == permutations2
    assert len(permutations1) == ensemble.ENSEMBLE_SIZE == 32
    assert len({tuple(p) for p in permutations1}) == 32
    assert permutations1[0] == single.permutation_for_round(693)

    members = ensemble._ensemble_for_tickets(tickets, permutations1)
    assert len(members) == 32
    assert members[0] == single.permute_tickets(tickets, 693)
    assert len({tuple(tuple(t) for t in m) for m in members}) == 32
    assert all(single.geometry_preserved(tickets, member) for member in members)


def test_ensemble_extends_existing_single_reference_and_fail_closes(tmp_path: Path):
    path = tmp_path / "shadow_registry.json"
    tickets = sample_tickets()
    registry = {
        "target_round": 700,
        "candidates": [{"version": "candidate", "tickets": tickets}],
        "matched_reference_by_candidate": {
            "candidate": single.permute_tickets(tickets, 700),
        },
        "matched_reference_frozen_at_jst": "2026-08-31T15:00:00+09:00",
        "matched_reference_permutation": single.permutation_for_round(700),
    }
    path.write_text(json.dumps(registry), encoding="utf-8")

    assert ensemble.ensure_matched_ensemble_reference(v4, path, latest_round=699) is True
    frozen = json.loads(path.read_text(encoding="utf-8"))
    refs = frozen["matched_ensemble_by_candidate"]["candidate"]
    assert len(refs) == 32
    assert refs[0] == registry["matched_reference_by_candidate"]["candidate"]
    assert frozen["matched_ensemble_size"] == 32
    frozen_at = frozen["matched_ensemble_frozen_at_jst"]

    assert ensemble.ensure_matched_ensemble_reference(v4, path, latest_round=699) is True
    again = json.loads(path.read_text(encoding="utf-8"))
    assert again["matched_ensemble_frozen_at_jst"] == frozen_at
    assert again["matched_ensemble_by_candidate"] == frozen["matched_ensemble_by_candidate"]

    late = tmp_path / "late.json"
    late.write_text(json.dumps(registry), encoding="utf-8")
    assert ensemble.ensure_matched_ensemble_reference(v4, late, latest_round=700) is False
    assert "matched_ensemble_by_candidate" not in json.loads(late.read_text(encoding="utf-8"))


def test_ensemble_score_is_mean_of_member_scores():
    tickets = sample_tickets()
    members = ensemble._ensemble_for_tickets(tickets, ensemble.permutations_for_round(693))
    actual = set(range(1, 8))
    result = ensemble._score_ensemble(v4, members, actual)
    manual = [v4.score_tickets(member, actual)["score"] for member in members]
    assert abs(result["mean_score"] - sum(manual) / len(manual)) < 1e-12
    assert result["score_std"] >= 0.0


def test_promotion_uses_ensemble_not_legacy_single_gate():
    rec = {
        "candidate_version": "candidate",
        "champion_version": "champion",
        "trusted_draws": 8,
        "random_trusted_draws": 8,
        "sum_delta": 0.8,
        "random_sum_delta": 0.8,
        "wins": 5,
        "random_wins": 5,
        "strict_random_valid": True,
        "matched_trusted_draws": 8,
        "matched_sum_delta": -10.0,
        "matched_wins": 0,
        "strict_matched_valid": True,
        "matched_ensemble_trusted_draws": 8,
        "matched_ensemble_sum_delta": 0.8,
        "matched_ensemble_wins": 5,
        "strict_matched_ensemble_valid": True,
        "family_adjusted_e_value": 21.0,
    }
    state = {"evidence": {v4.e_key("candidate", "champion"): rec}}
    eligible = ensemble.promotion_candidates(v4, state, "champion")
    assert len(eligible) == 1

    rec["matched_ensemble_sum_delta"] = 0.0
    assert ensemble.promotion_candidates(v4, state, "champion") == []


def test_ensemble_grade_replaces_single_matched_in_e_intersection(tmp_path: Path):
    out = tmp_path / "out"
    out.mkdir()
    result_path = out / "shadow_oos_results.csv"
    tickets = sample_tickets()
    members = ensemble._ensemble_for_tickets(tickets, ensemble.permutations_for_round(700))
    registry = {
        "target_round": 700,
        "formal_block_index": 1,
        "family_weight": 0.5,
        "champion_version": "champion",
        "matched_ensemble_frozen_at_jst": "2026-08-31T19:00:00+09:00",
        "matched_ensemble_by_candidate": {"candidate": members},
        "candidates": [{"version": "candidate", "tickets": tickets}],
    }
    rec = {
        "candidate_version": "candidate",
        "champion_version": "champion",
        "champion_e_value_raw": 10.0,
        "random_e_value_raw": 8.0,
        "matched_e_value_raw": 0.01,
        "family_weight": 0.5,
        "required_raw_e_value": 40.0,
    }
    state = {"evidence": {v4.e_key("candidate", "champion"): rec}}

    def already_graded(*_args, **_kwargs):
        return True

    assert ensemble._grade_registry(
        v4, already_graded, registry, 700, "2026-10-23", set(range(1, 8)),
        "verified_two_result_sources", True, state, result_path,
    ) is True
    updated = state["evidence"][v4.e_key("candidate", "champion")]
    assert updated["strict_matched_ensemble_valid"] is True
    assert updated["matched_ensemble_trusted_draws"] == 1
    assert updated["e_value_semantics"] == "family_adjusted_min_champion_random_matched_ensemble32"
    assert abs(updated["family_adjusted_e_value"] - 0.5 * min(
        updated["champion_e_value_raw"],
        updated["random_e_value_raw"],
        updated["matched_ensemble_e_value_raw"],
    )) < 1e-12
    assert updated["family_adjusted_e_value"] > 0.5 * updated["matched_e_value_raw"]
    assert (out / "matched_ensemble_oos_results.csv").exists()
