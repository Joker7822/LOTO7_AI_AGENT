import json
from pathlib import Path

import loto7_v4_runner as v4
import matched_permutation_oos as matched


def test_common_permutation_preserves_portfolio_geometry():
    tickets = [
        [1, 2, 3, 4, 5, 6, 7],
        [1, 2, 8, 9, 10, 11, 12],
        [1, 3, 8, 13, 14, 15, 16],
        [2, 4, 9, 13, 17, 18, 19],
        [5, 6, 10, 14, 17, 20, 21],
    ]
    ref1 = matched.permute_tickets(tickets, 693)
    ref2 = matched.permute_tickets(tickets, 693)
    assert ref1 == ref2
    assert ref1 != tickets
    assert matched.geometry_preserved(tickets, ref1)
    assert matched.geometry_signature(tickets) == matched.geometry_signature(ref1)


def test_matched_reference_is_prefrozen_and_fail_closed(tmp_path: Path):
    path = tmp_path / "shadow_registry.json"
    registry = {
        "target_round": 700,
        "candidates": [{"version": "candidate", "tickets": [[1, 2, 3, 4, 5, 6, 7]] * 5}],
    }
    path.write_text(json.dumps(registry), encoding="utf-8")

    assert matched.ensure_matched_reference(v4, path, latest_round=699) is True
    first = json.loads(path.read_text(encoding="utf-8"))
    ref = first["matched_reference_by_candidate"]["candidate"]
    assert matched.geometry_preserved(registry["candidates"][0]["tickets"], ref)
    frozen = first["matched_reference_frozen_at_jst"]

    assert matched.ensure_matched_reference(v4, path, latest_round=699) is True
    second = json.loads(path.read_text(encoding="utf-8"))
    assert second["matched_reference_by_candidate"]["candidate"] == ref
    assert second["matched_reference_frozen_at_jst"] == frozen

    late = tmp_path / "late.json"
    late.write_text(json.dumps(registry), encoding="utf-8")
    assert matched.ensure_matched_reference(v4, late, latest_round=700) is False
    assert "matched_reference_by_candidate" not in json.loads(late.read_text(encoding="utf-8"))


def test_matched_gate_is_required_after_champion_random_gate():
    rec = {
        "candidate_version": "candidate",
        "champion_version": "champion",
        "matched_trusted_draws": 8,
        "matched_sum_delta": 0.8,
        "matched_wins": 5,
        "strict_matched_valid": True,
    }

    def base(_state, _champion):
        return [(2.0, rec)]

    eligible = matched._promotion_candidates(v4, base, {"evidence": {}}, "champion")
    assert len(eligible) == 1

    rec["matched_sum_delta"] = 0.0
    assert matched._promotion_candidates(v4, base, {"evidence": {}}, "champion") == []

    rec["matched_sum_delta"] = 0.8
    rec["strict_matched_valid"] = False
    assert matched._promotion_candidates(v4, base, {"evidence": {}}, "champion") == []


def test_matched_grade_enters_three_way_intersection(tmp_path: Path):
    out = tmp_path / "out"
    out.mkdir()
    result_path = out / "shadow_oos_results.csv"
    candidate_tickets = [[1, 2, 3, 4, 5, 6, 8]] * 5
    matched_tickets = matched.permute_tickets(candidate_tickets, 700)
    registry = {
        "target_round": 700,
        "formal_block_index": 1,
        "family_weight": 0.5,
        "champion_version": "champion",
        "matched_reference_frozen_at_jst": "2026-08-31T15:00:00+09:00",
        "matched_reference_by_candidate": {"candidate": matched_tickets},
        "candidates": [{"version": "candidate", "tickets": candidate_tickets}],
    }
    rec = {
        "candidate_version": "candidate",
        "champion_version": "champion",
        "champion_e_value_raw": 10.0,
        "random_e_value_raw": 8.0,
        "family_weight": 0.5,
        "required_raw_e_value": 40.0,
    }
    state = {"evidence": {v4.e_key("candidate", "champion"): rec}}

    def already_strict(*_args, **_kwargs):
        return True

    assert matched._grade_registry(
        v4, already_strict, registry, 700, "2026-10-23", set(range(1, 8)),
        "verified_two_result_sources", True, state, result_path,
    ) is True
    updated = state["evidence"][v4.e_key("candidate", "champion")]
    assert updated["strict_matched_valid"] is True
    assert updated["matched_trusted_draws"] == 1
    assert updated["e_value_semantics"] == "family_adjusted_min_champion_random_matched_permutation"
    assert updated["family_adjusted_e_value"] <= 0.5 * min(
        updated["champion_e_value_raw"], updated["random_e_value_raw"], updated["matched_e_value_raw"]
    ) + 1e-12
    assert (out / "matched_oos_results.csv").exists()
