import numpy as np

import loto7_v2_runner as v2
import matched_budget_null_calibration as matched


DUMMY_WINDOWS = {"full": {}, "120": {}, "60": {}, "30": {}}
DUMMY_ERAS = [{"signal_objective": -0.1}] * 4


def test_run_world_stops_on_plateau(monkeypatch):
    monkeypatch.setattr(matched, "synthetic_history", lambda n_rows, seed: np.zeros((n_rows, 37)))
    monkeypatch.setattr(
        matched.robust,
        "replay_signal_with_eras",
        lambda x, cfg, min_train, keep_q=False: (DUMMY_WINDOWS, DUMMY_ERAS, []),
    )
    monkeypatch.setattr(matched.so, "weighted_signal_objective", lambda windows, cfg: -0.05)
    monkeypatch.setattr(
        matched,
        "_best_candidate",
        lambda x, parent, parent_windows, parent_eras, data_key, generation, min_train, count: (
            None, None, None, count
        ),
    )

    result = matched.run_world(
        n_rows=20,
        min_train=5,
        world_index=0,
        trial_budget=20,
        max_stale_generations=3,
        candidates_per_generation=2,
    )
    assert result["stop_reason"] == "signal_parent_plateau"
    assert result["candidate_trials"] == 6
    assert result["generations_run"] == 3


def test_run_world_can_consume_exact_trial_budget(monkeypatch):
    monkeypatch.setattr(matched, "synthetic_history", lambda n_rows, seed: np.zeros((n_rows, 37)))
    monkeypatch.setattr(
        matched.robust,
        "replay_signal_with_eras",
        lambda x, cfg, min_train, keep_q=False: (DUMMY_WINDOWS, DUMMY_ERAS, []),
    )
    monkeypatch.setattr(matched.so, "weighted_signal_objective", lambda windows, cfg: -0.04)
    monkeypatch.setattr(
        matched,
        "_best_candidate",
        lambda x, parent, parent_windows, parent_eras, data_key, generation, min_train, count: (
            v2.DEFAULT_CHAMPION, DUMMY_WINDOWS, DUMMY_ERAS, count
        ),
    )

    result = matched.run_world(
        n_rows=20,
        min_train=5,
        world_index=1,
        trial_budget=5,
        max_stale_generations=300,
        candidates_per_generation=2,
    )
    assert result["stop_reason"] == "trial_budget_exhausted"
    assert result["candidate_trials"] == 5
    assert result["generations_run"] == 3
    assert result["accepted_generations"] == 3


def test_summary_uses_finite_sample_upper_tail_correction():
    state = {
        "target_worlds": 4,
        "trial_budget": 708,
        "max_stale_generations": 300,
        "worlds": [
            {"best_signal_objective": -0.06},
            {"best_signal_objective": -0.05},
            {"best_signal_objective": -0.04},
            {"best_signal_objective": -0.03},
        ],
    }
    summary = matched.summarize(state, observed=-0.045)
    # Two of four null worlds are >= observed; corrected empirical p=(1+2)/(4+1).
    assert summary["empirical_tail_p_vs_matched_null_search"] == 0.6
    assert summary["matched_signal_trial_budget"] == 708
    assert summary["calibration_complete"] is True
