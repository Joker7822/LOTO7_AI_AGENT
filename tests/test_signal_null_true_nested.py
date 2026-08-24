from __future__ import annotations

import numpy as np

import loto7_v2_runner as v2
import null_search_calibration as nsc
import precision_random_baseline as prb
import separated_optimizer as so
import true_nested_evolution as tne


def cfg(name: str = "x", overlap: float = 0.65) -> v2.ModelConfig:
    return v2.ModelConfig(
        name=name,
        eta=1.2,
        decay=0.994,
        expert_uniform_mix=0.12,
        final_uniform_mix=0.20,
        overlap_penalty=overlap,
    )


def signal_window(log_edge: float, brier_edge: float = 0.001, top_delta: float = 0.05):
    return {
        "top7_hits": so.UNIFORM_TOP7_HITS + top_delta,
        "actual_mass": so.UNIFORM_ACTUAL_MASS + 0.001,
        "mean_log_prob_actual": so.UNIFORM_LOG_PROB + log_edge,
        "brier": 0.02,
        "uniform_brier": 0.02 + brier_edge,
        "top7_hits_delta_vs_uniform": top_delta,
        "actual_mass_delta_vs_uniform": 0.001,
        "log_edge_vs_uniform": log_edge,
        "brier_edge_vs_uniform": brier_edge,
    }


def test_signal_signature_ignores_portfolio_overlap():
    assert so.signal_signature(cfg("a", 0.4)) == so.signal_signature(cfg("b", 2.0))


def test_signal_candidates_keep_overlap_fixed():
    parent = cfg(overlap=1.4)
    children = so.signal_candidates(parent, "data", 12, count=2)
    assert children
    assert all(c.overlap_penalty == parent.overlap_penalty for c in children)


def test_signal_accept_is_signal_only_and_accepts_clear_improvement():
    incumbent = {name: signal_window(-0.02) for name in so.SIGNAL_WEIGHTS}
    candidate = {name: signal_window(-0.01) for name in so.SIGNAL_WEIGHTS}
    ok, decision = so.signal_accept(candidate, incumbent, cfg("candidate"), cfg("incumbent"))
    assert ok
    assert decision["checks"]["signal_objective_improves"]


def test_precision_random_round_has_valid_metrics():
    out = prb.random_round(set(range(1, 8)), t=101, reps=16)
    assert 0 <= out["mean_max_hits"] <= 7
    assert 0 <= out["mean_ticket_hits"] <= 7
    assert 0 <= out["ge3_rate"] <= 1
    assert 0 <= out["ge4_rate"] <= 1
    assert out["score_se"] >= 0


def test_null_synthetic_history_is_valid_7_of_37():
    x = nsc.synthetic_history(20, seed=123)
    assert x.shape == (20, 37)
    assert np.all(x.sum(axis=1) == 7)
    assert set(np.unique(x)).issubset({0.0, 1.0})


def test_true_nested_prefix_sha_depends_only_on_prefix_content():
    a = nsc.synthetic_history(12, seed=1)
    b = a.copy()
    assert tne.prefix_sha(a) == tne.prefix_sha(b)
    b[-1, 0] = 1.0 - b[-1, 0]
    assert tne.prefix_sha(a) != tne.prefix_sha(b)


def test_null_summary_marks_incomplete_before_target():
    state = {
        "target_worlds": 4,
        "worlds": [
            {"best_signal_objective": -0.1},
            {"best_signal_objective": 0.0},
        ],
    }
    s = nsc.summarize(state, observed=0.05)
    assert s["completed_worlds"] == 2
    assert not s["calibration_complete"]
    assert 0 < s["empirical_tail_p_vs_bounded_null_search"] <= 1
