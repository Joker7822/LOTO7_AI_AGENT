import math

import numpy as np

import feedback_optimizer as fo
import loto7_v2_runner as v2


def _summary(obj: float, log_edge: float, top7_edge: float = 0.05, score120: float = 3.0):
    windows = {}
    for name in ("full", "120", "60", "30"):
        windows[name] = {
            "max_hits": 2.6,
            "mean_hits": 1.4,
            "ge3": 0.5,
            "ge4": 0.1,
            "score": score120 if name == "120" else 3.0,
            "random_max_hits": 2.4,
            "random_mean_hits": 1.32,
            "random_ge3": 0.43,
            "random_ge4": 0.07,
            "random_score": 2.75,
            "score_delta_vs_random": (score120 if name == "120" else 3.0) - 2.75,
            "max_hits_delta_vs_random": 0.2,
            "signal": {
                "top7_hits": fo.UNIFORM_TOP7_HITS + top7_edge,
                "top7_hits_delta_vs_uniform": top7_edge,
                "actual_mass": fo.UNIFORM_ACTUAL_MASS + 0.01,
                "actual_mass_delta_vs_uniform": 0.01,
                "mean_log_prob_actual": fo.UNIFORM_LOG_PROB + log_edge,
                "log_edge_vs_uniform": log_edge,
                "brier": 0.01,
                "uniform_brier": 0.011,
                "brier_edge_vs_uniform": 0.001,
            },
        }
    return {
        "feedback_objective": obj,
        "signal_objective": log_edge + 0.05,
        "windows": windows,
    }


def test_uniform_distribution_has_zero_signal_edges():
    actual_idx = np.arange(7)
    got = fo.aggregate_signal([fo.signal_metrics(np.full(37, 1 / 37), actual_idx)])
    assert abs(got["top7_hits_delta_vs_uniform"] - (7 - fo.UNIFORM_TOP7_HITS)) > 0
    assert abs(got["actual_mass_delta_vs_uniform"]) < 1e-12
    assert abs(got["log_edge_vs_uniform"]) < 1e-12
    assert abs(got["brier_edge_vs_uniform"]) < 1e-12


def test_signal_metrics_reward_probability_mass_on_actual_numbers():
    actual_idx = np.arange(7)
    q = np.full(37, 0.2 / 30)
    q[:7] = 0.8 / 7
    got = fo.aggregate_signal([fo.signal_metrics(q, actual_idx)])
    assert got["actual_mass_delta_vs_uniform"] > 0
    assert got["log_edge_vs_uniform"] > 0
    assert got["brier_edge_vs_uniform"] > 0
    assert got["top7_hits"] == 7


def test_portfolio_improvement_is_rejected_when_signal_regresses():
    incumbent = _summary(0.20, log_edge=0.020, top7_edge=0.08)
    candidate = _summary(0.30, log_edge=0.010, top7_edge=0.08)
    cfg_i = v2.ModelConfig("i", 1.0, 0.99, 0.2, 0.2, 1.0)
    cfg_c = v2.ModelConfig("c", 1.1, 0.99, 0.2, 0.2, 1.0)
    ok, decision = fo.decide_accept(candidate, incumbent, cfg_c, cfg_i)
    assert ok is False
    assert decision["checks"]["signal_full_log_not_regressed"] is False


def test_candidate_can_pass_when_portfolio_and_signal_both_improve():
    incumbent = _summary(0.20, log_edge=0.020, top7_edge=0.08)
    candidate = _summary(0.30, log_edge=0.025, top7_edge=0.09)
    cfg_i = v2.ModelConfig("i", 1.0, 0.99, 0.2, 0.2, 1.0)
    cfg_c = v2.ModelConfig("c", 1.1, 0.99, 0.2, 0.2, 1.0)
    ok, decision = fo.decide_accept(candidate, incumbent, cfg_c, cfg_i)
    assert ok is True
    assert all(decision["checks"].values())


def test_boundary_penalty_prefers_interior_parameters():
    boundary = v2.ModelConfig("b", 0.10, 0.975, 0.02, 0.55, 2.00)
    interior = v2.ModelConfig("i", 1.5, 0.99, 0.2, 0.25, 1.0)
    assert fo.boundary_penalty(boundary) > fo.boundary_penalty(interior)
