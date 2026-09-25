from pathlib import Path

import future_holdout_evidence as evidence
import loto7_v4_runner as v4
import strict_oos_governance as strict


def locked_state(tmp_path: Path):
    state_path = tmp_path / "future_holdout_state.json"
    state = {
        "version": "future-holdout-v1",
        "status": "active",
        "locked_candidate_version": "candidate-a",
        "locked_config": {
            "name": "candidate-a",
            "eta": 1.0,
            "decay": 0.99,
            "expert_uniform_mix": 0.2,
            "final_uniform_mix": 0.2,
            "overlap_penalty": 0.7,
        },
        "locked_at_jst": "2026-08-31T13:43:47+09:00",
        "start_target_round": 693,
        "horizon_trusted_draws": 26,
        "all_draws": 4,
        "trusted_draws": 4,
        "sum_delta_vs_random": 0.14,
        "wins_vs_random": 2,
        "random_e_value": 0.99,
        "graded_rounds": [693, 694, 695, 696],
        "matched_ensemble_trusted_draws": 4,
        "sum_delta_vs_matched_ensemble": -0.19,
        "wins_vs_matched_ensemble": 2,
        "matched_ensemble_e_value": 0.98,
        "matched_ensemble_graded_rounds": [693, 694, 695, 696],
    }
    assert strict.ensure_holdout_protocol_lock(v4, state, state_path)
    return state


def test_incomplete_holdout_never_confirms(tmp_path: Path):
    state = locked_state(tmp_path)
    report, lock_ok = evidence.build_report(state)
    assert lock_ok is True
    assert report["confirmed"] is False
    assert report["claim_status"] == "not_confirmed_holdout_incomplete"
    assert report["progress"]["trusted_draws"] == 4
    assert report["progress"]["horizon_trusted_draws"] == 26


def test_full_holdout_requires_random_and_matched_to_pass(tmp_path: Path):
    state = locked_state(tmp_path)
    rounds = list(range(693, 719))
    state.update({
        "status": "complete",
        "all_draws": 26,
        "trusted_draws": 26,
        "sum_delta_vs_random": 2.6,
        "wins_vs_random": 16,
        "random_e_value": 25.0,
        "graded_rounds": rounds,
        "matched_ensemble_trusted_draws": 26,
        "sum_delta_vs_matched_ensemble": 2.6,
        "wins_vs_matched_ensemble": 16,
        "matched_ensemble_e_value": 25.0,
        "matched_ensemble_graded_rounds": rounds,
    })
    report, lock_ok = evidence.build_report(state)
    assert lock_ok is True
    assert report["confirmed"] is True
    assert report["claim_status"] == "confirmed_operational_future_oos_edge"

    state["matched_ensemble_e_value"] = 19.99
    report, _ = evidence.build_report(state)
    assert report["confirmed"] is False
    assert report["claim_status"] == "not_confirmed_criteria_not_met"


def test_protocol_drift_invalidates_claim(tmp_path: Path):
    state = locked_state(tmp_path)
    state["locked_config"]["eta"] = 9.9
    report, lock_ok = evidence.build_report(state)
    assert lock_ok is False
    assert report["confirmed"] is False
    assert report["claim_status"] == "invalid_protocol_lock"
