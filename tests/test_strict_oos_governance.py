import json
from pathlib import Path

import numpy as np

import loto7_v4_runner as v4
import strict_oos_governance as strict


def test_sequential_family_weights_are_summable_and_thresholds_increase():
    weights = [strict.block_weight(i) for i in range(1, 10000)]
    assert abs(sum(weights) - 0.9999) < 1e-4
    assert strict.required_raw_e_value(1) == 40.0
    assert strict.required_raw_e_value(2) == 120.0
    assert strict.required_raw_e_value(3) == 240.0


def test_random_reference_is_deterministic_and_only_prefrozen(tmp_path: Path):
    path = tmp_path / "shadow_registry.json"
    path.write_text(json.dumps({"target_round": 700}), encoding="utf-8")

    assert strict.ensure_random_reference(v4, path, latest_round=699) is True
    first = json.loads(path.read_text(encoding="utf-8"))
    tickets1 = first["random_reference_tickets"]
    assert len(tickets1) == 5
    assert all(len(t) == 7 and len(set(t)) == 7 for t in tickets1)

    # Re-running cannot rewrite the frozen null reference.
    assert strict.ensure_random_reference(v4, path, latest_round=699) is True
    second = json.loads(path.read_text(encoding="utf-8"))
    assert second["random_reference_tickets"] == tickets1
    assert second["random_reference_frozen_at_jst"] == first["random_reference_frozen_at_jst"]

    # A missing reference must not be manufactured after the target result exists.
    late = tmp_path / "late_registry.json"
    late.write_text(json.dumps({"target_round": 700}), encoding="utf-8")
    assert strict.ensure_random_reference(v4, late, latest_round=700) is False
    assert "random_reference_tickets" not in json.loads(late.read_text(encoding="utf-8"))


def test_strict_promotion_requires_champion_and_random_evidence():
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
        "family_adjusted_e_value": 21.0,
    }
    state = {"evidence": {"candidate::vs::champion": rec}}
    eligible = strict.strict_promotion_candidates(v4, state, "champion")
    assert len(eligible) == 1

    rec["random_sum_delta"] = 0.0
    assert strict.strict_promotion_candidates(v4, state, "champion") == []

    rec["random_sum_delta"] = 0.8
    rec["family_adjusted_e_value"] = 19.99
    assert strict.strict_promotion_candidates(v4, state, "champion") == []


def test_paired_grade_sets_family_adjusted_evidence(tmp_path: Path):
    out = tmp_path / "out"
    out.mkdir()
    result_path = out / "shadow_oos_results.csv"
    candidate_version = "candidate"
    champion_version = "champion"
    registry = {
        "target_round": 700,
        "formal_block_index": 1,
        "champion_version": champion_version,
        "champion_tickets": [[1, 2, 3, 4, 5, 6, 7]] * 5,
        "random_reference_tickets": [[8, 9, 10, 11, 12, 13, 14]] * 5,
        "random_reference_frozen_at_jst": "2026-08-31T10:00:00+09:00",
        "base_data_sha": "sha",
        "frozen_at_jst": "2026-08-31T10:00:00+09:00",
        "candidates": [{
            "version": candidate_version,
            "config": {
                "name": "candidate",
                "eta": 1.0,
                "decay": 0.99,
                "expert_uniform_mix": 0.2,
                "final_uniform_mix": 0.2,
                "overlap_penalty": 0.7,
            },
            "tickets": [[1, 2, 3, 4, 5, 6, 8]] * 5,
        }],
    }
    state = {"graded_rounds": [], "evidence": {}}
    actual = set(range(1, 8))

    graded = strict._patched_grade_registry(
        v4, v4.grade_registry, registry, 700, "2026-10-23", actual,
        "verified_two_result_sources", True, state, result_path,
    )
    assert graded is True
    rec = state["evidence"][v4.e_key(candidate_version, champion_version)]
    assert rec["random_trusted_draws"] == 1
    assert rec["formal_block_index"] == 1
    assert rec["family_weight"] == 0.5
    assert rec["required_raw_e_value"] == 40.0
    assert rec["e_value"] == rec["family_adjusted_e_value"]
    assert rec["e_value"] <= min(rec["champion_e_value_raw"], rec["random_e_value_raw"])
    assert (out / "paired_oos_results.csv").exists()


def test_e_process_update_is_neutral_at_zero_delta():
    comps = {str(l): 1.0 for l in v4.E_LAMBDAS}
    updated = strict.update_e_components(comps, 0.0, v4.E_LAMBDAS)
    assert updated == comps
    assert strict.e_value_from_components(updated, v4.E_LAMBDAS) == 1.0
