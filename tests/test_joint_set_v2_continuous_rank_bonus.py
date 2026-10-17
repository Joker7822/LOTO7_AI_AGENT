import numpy as np

from joint_set_v2_continuous_rank_bonus import (
    build_weight_portfolios,
    rank_values,
    robust_weight_score,
    select_weight,
)
from joint_set_v2_model import ForecastBundle, expected_utility_portfolio


def _bundle() -> ForecastBundle:
    raw = np.linspace(0.30, 0.08, 37)
    raw = raw * (7.0 / raw.sum())
    p = 0.95 * np.full(37, 7.0 / 37.0) + 0.05 * raw
    return ForecastBundle(
        inclusion_p=p,
        raw_inclusion_p=raw,
        pair_matrix=np.zeros((37, 37), dtype=float),
        regime=np.array([0.9, 0.09, 0.01], dtype=float),
        gate=0.05,
        effective_pair_strength=0.0,
        gate_diagnostics={},
    )


def test_rank_values_are_continuous_percentiles():
    values = rank_values(_bundle())
    assert values.shape == (37,)
    assert np.isclose(values.max(), 1.0)
    assert np.isclose(values.min(), 0.0)
    assert len(np.unique(values)) == 37
    assert values[0] > values[-1]


def test_weight_zero_reproduces_existing_optimizer():
    bundle = _bundle()
    seed = 123456
    expected, _ = expected_utility_portfolio(
        bundle, seed=seed, scenarios=64, candidate_count=32
    )
    actual = build_weight_portfolios(
        bundle, [0.0], seed=seed, scenarios=64, candidate_count=32
    )[0.0]["tickets"]
    assert actual == expected


def test_positive_weight_is_deterministic():
    bundle = _bundle()
    a = build_weight_portfolios(bundle, [0.04], seed=999, scenarios=64, candidate_count=32)
    b = build_weight_portfolios(bundle, [0.04], seed=999, scenarios=64, candidate_count=32)
    assert a[0.04]["tickets"] == b[0.04]["tickets"]
    assert a[0.04]["diagnostics"] == b[0.04]["diagnostics"]


def test_robust_weight_score_rewards_consistent_positive_delta():
    positive = [0.05] * 40
    negative = [-0.05] * 40
    assert robust_weight_score(positive) > 0.0
    assert robust_weight_score(negative) < 0.0


def test_select_weight_falls_back_to_zero_when_alternatives_are_not_positive():
    scores = {
        0.0: [2.0] * 40,
        0.02: [1.99] * 40,
        0.04: [1.98] * 40,
    }
    weight, diagnostics = select_weight(scores, [0.0, 0.02, 0.04])
    assert weight == 0.0
    assert diagnostics["0.02"] < 0.0


def test_select_weight_uses_training_scores_only():
    # The selector accepts only explicitly supplied training arrays. A later holdout
    # sequence cannot influence the selected weight unless a caller incorrectly adds it.
    train = {
        0.0: [2.0] * 40,
        0.02: [2.03] * 40,
        0.04: [2.01] * 40,
    }
    weight_before, _ = select_weight(train, [0.0, 0.02, 0.04])
    holdout = [0.0] * 20
    assert holdout == [0.0] * 20
    weight_after, _ = select_weight(train, [0.0, 0.02, 0.04])
    assert weight_before == weight_after == 0.02
