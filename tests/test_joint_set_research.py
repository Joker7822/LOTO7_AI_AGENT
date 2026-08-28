import datetime as dt

import numpy as np

import joint_set_null_calibration as jsn
import joint_set_research as jsr
import research_metadata as rm
from joint_set_model import (
    candidate_configs,
    dynamic_uniform_gate,
    expected_utility_portfolio,
    forecast,
    low_rank_pair_matrix,
    sample_joint_sets,
)


def synthetic_history(draws=150, seed=123):
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
    }


def test_candidate_family_is_small_and_predeclared():
    cfgs = candidate_configs()
    assert len(cfgs) == 5
    assert len({c.version() for c in cfgs}) == 5


def test_pair_matrix_is_symmetric_and_zero_diagonal():
    x = synthetic_history(140)
    mat = low_rank_pair_matrix(x, candidate_configs()[1])
    assert mat.shape == (37, 37)
    assert np.allclose(mat, mat.T)
    assert np.allclose(np.diag(mat), 0.0)
    assert np.isfinite(mat).all()


def test_dynamic_gate_suppresses_negative_proper_score_history():
    cfg = candidate_configs()[1]
    regime = np.array([0.7, 0.2, 0.1])
    good = [signal_row(log_edge=0.025, brier=0.0015, top7=2.0, mass=0.205) for _ in range(70)]
    bad = [signal_row(log_edge=-0.03, brier=-0.0015, top7=1.0, mass=0.175) for _ in range(70)]
    good_gate, _ = dynamic_uniform_gate(good, regime, cfg)
    bad_gate, _ = dynamic_uniform_gate(bad, regime, cfg)
    assert 0.0 <= bad_gate <= good_gate <= cfg.gate_ceiling
    assert bad_gate < 0.10


def test_joint_sampler_produces_valid_seven_number_sets():
    x = synthetic_history(100)
    cfg = candidate_configs()[0]
    bundle = forecast(x, cfg, [signal_row() for _ in range(40)])
    draws = sample_joint_sets(bundle, 30, seed=999)
    assert draws.shape == (30, 7)
    assert np.all((draws >= 1) & (draws <= 37))
    for row in draws:
        assert len(set(row.tolist())) == 7
        assert list(row) == sorted(row.tolist())


def test_expected_utility_optimizer_returns_five_unique_tickets():
    x = synthetic_history(110)
    cfg = candidate_configs()[1]
    bundle = forecast(x, cfg, [signal_row() for _ in range(45)])
    tickets, diag = expected_utility_portfolio(
        bundle, seed=101, scenarios=64, candidate_count=24, local_passes=1
    )
    assert len(tickets) == 5
    assert len(set(tickets)) == 5
    assert diag["scenario_count"] == 64
    assert diag["expected_max_hits"] >= 0.0


def test_metadata_rejects_post_cutoff_and_untrusted_rows():
    jst = dt.timezone(dt.timedelta(hours=9))
    records = [
        rm.MetadataRecord(10, dt.datetime(2026, 1, 2, 17, 0, tzinfo=jst), "machine_temp", "22.5", "official", "verified"),
        rm.MetadataRecord(10, dt.datetime(2026, 1, 2, 19, 0, tzinfo=jst), "late_value", "1", "x", "verified"),
        rm.MetadataRecord(10, dt.datetime(2026, 1, 2, 16, 0, tzinfo=jst), "rumor", "1", "x", "unverified"),
        rm.MetadataRecord(11, dt.datetime(2026, 1, 2, 16, 0, tzinfo=jst), "other_round", "1", "x", "verified"),
    ]
    fmap = rm.feature_map_for_target(records, 10, "2026-01-02", cutoff_hour_jst=18)
    assert fmap == {"machine_temp": 22.5}


def test_metadata_categorical_feature_is_one_hot_and_prior_available():
    jst = dt.timezone(dt.timedelta(hours=9))
    records = [
        rm.MetadataRecord(20, dt.datetime(2026, 2, 1, 10, 0, tzinfo=jst), "previous_set_ball", "A", "source", "trusted")
    ]
    mat, names, _ = rm.design_matrix(records, [20], ["2026-02-01"], cutoff_hour_jst=18)
    assert names == ["previous_set_ball=A"]
    assert mat.shape == (1, 1)
    assert mat[0, 0] == 1.0


def test_config_selection_cannot_see_future_signal_rows():
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


def test_synthetic_null_world_is_deterministic_and_fair_shape():
    a = jsn.synthetic_fair_world(25, seed=77)
    b = jsn.synthetic_fair_world(25, seed=77)
    assert np.array_equal(a, b)
    assert a.shape == (25, 37)
    assert np.all(a.sum(axis=1) == 7)
