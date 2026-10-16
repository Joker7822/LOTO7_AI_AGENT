import numpy as np

import joint_set_v2_null_calibration as jsn
import joint_set_v2_research as jsr
from joint_set_v2_model import (
    UNIFORM_P,
    bernoulli_signal_metrics,
    candidate_configs,
    dynamic_uniform_gate,
    expected_utility_portfolio,
    forecast,
    project_inclusion,
    sample_joint_sets,
)


def synthetic_history(draws=150, seed=321):
    rng = np.random.default_rng(seed)
    x = np.zeros((draws, 37), dtype=np.int8)
    for i in range(draws):
        x[i, rng.choice(np.arange(37), size=7, replace=False)] = 1
    return x


def signal_row(log_edge=0.01, brier=0.001, top7=2.0, mass=0.20):
    return {
        "top7_hits": top7,
        "actual_mass": mass,
        "log_edge": log_edge,
        "brier_edge": brier,
        "inclusion_sum": 7.0,
    }


def test_projection_is_valid_inclusion_probability_vector():
    p = project_inclusion(np.linspace(-0.5, 1.8, 37))
    assert p.shape == (37,)
    assert np.all(p >= 0.0)
    assert np.all(p <= 1.0)
    assert abs(float(p.sum()) - 7.0) < 1e-8


def test_uniform_inclusion_has_zero_proper_score_edge():
    actual = np.array([0, 2, 5, 10, 16, 24, 36])
    row = bernoulli_signal_metrics(UNIFORM_P, actual)
    assert abs(row["log_edge"]) < 1e-12
    assert abs(row["brier_edge"]) < 1e-12
    assert abs(row["inclusion_sum"] - 7.0) < 1e-12


def test_dynamic_gate_suppresses_negative_bernoulli_proper_scores():
    cfg = candidate_configs()[1]
    regime = np.array([0.7, 0.2, 0.1])
    good = [signal_row(log_edge=0.015, brier=0.0010, top7=2.0, mass=0.205) for _ in range(70)]
    bad = [signal_row(log_edge=-0.02, brier=-0.0010, top7=1.0, mass=0.175) for _ in range(70)]
    good_gate, _ = dynamic_uniform_gate(good, regime, cfg)
    bad_gate, _ = dynamic_uniform_gate(bad, regime, cfg)
    assert 0.0 <= bad_gate <= good_gate <= cfg.gate_ceiling
    assert bad_gate <= 0.05


def test_forecast_and_sampler_preserve_exact_set_semantics():
    x = synthetic_history(120)
    cfg = candidate_configs()[1]
    bundle = forecast(x, cfg, [signal_row() for _ in range(45)])
    assert np.all(bundle.inclusion_p >= 0.0)
    assert np.all(bundle.inclusion_p <= 1.0)
    assert abs(float(bundle.inclusion_p.sum()) - 7.0) < 1e-8
    draws = sample_joint_sets(bundle, 40, seed=777)
    assert draws.shape == (40, 7)
    assert np.all((draws >= 1) & (draws <= 37))
    for row in draws:
        assert len(set(row.tolist())) == 7
        assert list(row) == sorted(row.tolist())


def test_expected_utility_optimizer_returns_unique_five_ticket_portfolio():
    x = synthetic_history(130)
    cfg = candidate_configs()[1]
    bundle = forecast(x, cfg, [signal_row() for _ in range(50)])
    tickets, diag = expected_utility_portfolio(bundle, seed=707, scenarios=64, candidate_count=24, local_passes=1)
    assert len(tickets) == 5
    assert len(set(tickets)) == 5
    assert diag["scenario_count"] == 64
    assert diag["expected_max_hits"] >= 0.0


def test_config_selection_cannot_see_future_rows():
    cfg_a, cfg_b = candidate_configs()[:2]
    positive = signal_row(log_edge=0.02, brier=0.001, top7=2.0, mass=0.20)
    negative = signal_row(log_edge=-0.02, brier=-0.001, top7=1.0, mass=0.17)
    huge = signal_row(log_edge=0.30, brier=0.02, top7=7.0, mass=0.80)
    preq = {
        cfg_a.version(): [positive.copy() for _ in range(40)] + [negative.copy() for _ in range(10)],
        cfg_b.version(): [negative.copy() for _ in range(40)] + [huge.copy() for _ in range(10)],
    }
    chosen, _ = jsr.select_config([cfg_a, cfg_b], preq, prior_count=40, selection_window=40)
    assert chosen.version() == cfg_a.version()


def test_v2_synthetic_null_world_is_deterministic_and_fair():
    a = jsn.synthetic_fair_world(25, seed=77)
    b = jsn.synthetic_fair_world(25, seed=77)
    assert np.array_equal(a, b)
    assert a.shape == (25, 37)
    assert np.all(a.sum(axis=1) == 7)
