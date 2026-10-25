"""Research-only factorial tests; no Production/Champion/Future-OOS writes."""
from pathlib import Path

import numpy as np
import pytest

import loto7_v2_runner as v2
from loto7_evolving_agent import PICKS, expert_probabilities
import signal_portfolio_factorial as lab


def synthetic_history(n=130, seed=471):
    rng = np.random.default_rng(seed)
    x = np.zeros((n, 37), dtype=np.int8)
    for row in x:
        row[rng.choice(37, size=PICKS, replace=False)] = 1
    return x


def test_legacy_probability_matches_existing_baseline_exactly():
    x = synthetic_history(120)
    ex = expert_probabilities(x)
    logw = np.zeros(len(ex), dtype=float)
    np.testing.assert_allclose(
        lab.probability_from_weights(lab.variant_experts(ex, "legacy", x), logw),
        v2._score_distribution(x, list(ex), logw, v2.DEFAULT_CHAMPION),
        rtol=0, atol=1e-14,
    )


@pytest.mark.parametrize("variant", lab.VARIANTS)
def test_ablation_preserves_original_experts(variant):
    x = synthetic_history(130)
    originals = expert_probabilities(x)
    before = {k: value.copy() for k, value in originals.items()}
    result = lab.variant_experts(originals, variant, x)
    assert result
    for key in before:
        np.testing.assert_array_equal(originals[key], before[key])
    if variant == "pair_int64":
        assert "pair_context" in result
    if variant.startswith("drop_"):
        assert len(result) < len(originals)


def test_sampling_and_expected_utility_are_deterministic():
    q = np.linspace(0.6, 1.4, 37)
    q = q / q.sum()
    for factory in (
        lambda: lab.random_tickets(q, 42),
        lambda: lab.optimized_tickets(q, 42, scenarios=32, candidates=16),
    ):
        a, b = factory(), factory()
        assert a == b
        assert len(a) == 5 and len(set(a)) == 5
        assert all(len(t) == 7 and len(set(t)) == 7
                   and min(t) >= 1 and max(t) <= 37 for t in a)


def test_four_arms_and_ablation_are_read_only(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    x = synthetic_history()
    result = lab.evaluate(
        x, min_train=100, last_n=4, scenarios=16, candidates=10,
        random_reps=2, seed=10,
    )
    assert set(result["arms"]) == set(lab.ARMS)
    assert set(result["signal_ablation"]) == set(lab.VARIANTS)
    assert result["evaluated_rounds"] == 4
    assert result["first_round_index"] == 127
    assert result["last_round_index"] == 130
    assert [row["round_index"] for row in result["rounds"]] == list(range(127, 131))
    for arm in result["arms"].values():
        assert 0 <= arm["ge3"] <= 1
        assert 0 <= arm["ge4"] <= 1
        assert 0 <= arm["mean_hits"] <= 7
        assert np.isfinite(arm["score"])
    for name, stats in result["signal_ablation"].items():
        assert np.isfinite(stats["log_edge"])
        assert np.isfinite(stats["brier_edge"])
        if name == "legacy":
            assert stats["delta_log_edge_vs_legacy"] == pytest.approx(0.0)
    assert result["chronological_prior_only"]
    assert not result["independent_evidence"]
    assert not result["production_changed"]
    assert not result["future_oos_changed"]
    assert not result["promotion_authorized"]
    assert list(Path(".").iterdir()) == []


def test_target_result_cannot_influence_its_frozen_forecast():
    x = synthetic_history(n=128)
    changed = x.copy()
    changed[-1] = 0
    changed[-1, 30:37] = 1
    kwargs = dict(min_train=100, last_n=1, scenarios=16,
                  candidates=10, random_reps=2, seed=451)
    original = lab.evaluate(x, **kwargs)
    modified = lab.evaluate(changed, **kwargs)
    assert original["rounds"][0]["forecast_sha256"] == (
        modified["rounds"][0]["forecast_sha256"]
    )
    assert original["rounds"][0]["portfolio_sha256"] == (
        modified["rounds"][0]["portfolio_sha256"]
    )


@pytest.mark.parametrize("error", [
    np.zeros((130, 37), dtype=np.int8),
    np.ones((130, 36), dtype=np.int8),
    np.ones((130, 37), dtype=float),
])
def test_rejects_invalid_histories(error):
    with pytest.raises(ValueError):
        lab.evaluate(error, min_train=100, last_n=4,
                     scenarios=16, candidates=10, random_reps=2)


def test_parameter_budget_validation():
    x = synthetic_history()
    for budget in (
        dict(scenarios=7, candidates=10, random_reps=2),
        dict(scenarios=16, candidates=4, random_reps=2),
        dict(scenarios=16, candidates=10, random_reps=0),
    ):
        with pytest.raises(ValueError):
            lab.evaluate(x, min_train=100, last_n=4, **budget)


def test_old_model_and_prospective_sources_remain_unmodified():
    root = Path(__file__).resolve().parents[1]
    legacy = (root / "loto7_evolving_agent.py").read_text(encoding="utf-8")
    assert "co = hist.T @ hist" in legacy
    runner = (root / "loto7_v2_runner.py").read_text(encoding="utf-8")
    assert "signal_portfolio_factorial" not in runner
    assert "signal_portfolio_factorial" not in (
        root / "weekly_production_prediction.py"
    ).read_text(encoding="utf-8")
    assert "signal_portfolio_factorial" not in (
        root / "joint_set_v2_signal_oos.py"
    ).read_text(encoding="utf-8")
