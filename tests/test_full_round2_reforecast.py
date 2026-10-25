"""Boundaries and reproducibility for 2..N historical reforecast."""
from pathlib import Path

import numpy as np
import pytest

import full_round2_reforecast as replay
import loto7_v2_runner as v2
from loto7_evolving_agent import PICKS, expert_probabilities
import signal_portfolio_factorial as factor


def synthetic(n=25, seed=7):
    rng = np.random.default_rng(seed)
    x = np.zeros((n, 37), dtype=np.int8)
    for row in x:
        row[rng.choice(37, size=PICKS, replace=False)] = 1
    return x


def small(x):
    return replay.reforecast(
        x, scenarios=8, candidates=5, random_reps=1, seed=731
    )


def test_round_two_exactly_one_prior_and_uniform_before_21():
    x = synthetic(25)
    output = small(x)
    assert output["evaluated_rounds"] == 24
    assert output["first_target_round"] == 2
    assert output["last_target_round"] == 25
    assert output["cold_start_rounds"] == 19
    assert output["adaptive_from_round"] == 21
    assert output["rounds"][0]["prior_draws"] == 1
    assert [row["round"] for row in output["rounds"]] == list(range(2, 26))
    for row in output["rounds"][:19]:
        assert row["regime"] == "uniform_cold_start"
        assert row["signal_top7"]["uniform"] == row["signal_top7"]["legacy"]
        assert row["portfolio"]["uniform_optimized"] == (
            row["portfolio"]["legacy_optimized"]
        )
    for row in output["rounds"][19:]:
        assert row["regime"] == "online_adaptive"


def test_uniform_top7_tiebreak_is_seeded_not_fixed_numbers():
    first = replay.top7_ranking(replay.UNIFORM_Q, 991)
    assert first == replay.top7_ranking(replay.UNIFORM_Q, 991)
    assert len(first) == 7 and len(set(first)) == 7
    assert first != replay.top7_ranking(replay.UNIFORM_Q, 992)


def test_same_input_same_predictions_and_checksums():
    x = synthetic(25)
    first = small(x)
    second = small(x)
    assert first == second
    assert len(set(r["forecast_sha256"] for r in first["rounds"])) == 24


def test_target_result_not_used_to_predict_itself():
    x = synthetic(25)
    changed = x.copy()
    changed[-1] = 0
    changed[-1, 30:37] = 1
    before = small(x)["rounds"][-1]
    after = small(changed)["rounds"][-1]
    assert before["actual_numbers"] != after["actual_numbers"]
    assert before["forecast_sha256"] == after["forecast_sha256"]
    assert before["signal_top7"] == after["signal_top7"]
    assert before["tickets"] == after["tickets"]
    assert before["uniform_random_sample_tickets"] == (
        after["uniform_random_sample_tickets"]
    )


def test_baseline_legacy_weights_match_existing_baseline_at_first_eligible_round():
    x = synthetic(25)
    t = 20
    experts = expert_probabilities(x[:t])
    w = np.zeros(len(experts), dtype=float)
    got = factor.probability_from_weights(experts, w)
    expected = v2._score_distribution(
        x[:t], list(experts), w, v2.DEFAULT_CHAMPION
    )
    np.testing.assert_allclose(got, expected, rtol=0, atol=1e-14)


def test_portfolio_hit_metrics_consistent_with_disclosed_tickets():
    report = small(synthetic(25))
    for row in report["rounds"]:
        actual = set(row["actual_numbers"])
        assert len(actual) == 7
        for arm, tickets in row["tickets"].items():
            expected = factor.ticket_metrics(
                [tuple(t) for t in tickets], actual
            )
            assert row["portfolio"][arm] == expected
        for label in ("uniform", "legacy"):
            top = row["signal_top7"][label]
            assert row["signal"][label]["top7_hits"] == float(
                len(set(top) & actual)
            )
    assert report["summary"]["all_rounds_2_onward"]["n"] == 24
    assert report["summary"]["cold_start_rounds_2_to_20"]["n"] == 19
    assert report["summary"]["adaptive_rounds_21_onward"]["n"] == 5


def test_no_ledger_writes_and_no_promotion(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    report = small(synthetic(25))
    assert not report["production_changed"]
    assert not report["future_oos_changed"]
    assert not report["independent_evidence"]
    assert not report["promotion_authorized"]
    assert not report["target_outcome_used_before_prediction"]
    assert list(Path(".").iterdir()) == []


@pytest.mark.parametrize("bad", [
    np.zeros((25, 37), dtype=np.int8),
    np.ones((25, 36), dtype=np.int8),
    np.ones((25, 37), dtype=float),
    synthetic(20),
])
def test_reject_bad_data(bad):
    with pytest.raises(ValueError):
        small(bad)


def test_reject_nonfixed_scope_and_invalid_budget():
    x = synthetic()
    with pytest.raises(ValueError):
        replay.reforecast(
            x, start_round=3, scenarios=8, candidates=5, random_reps=1
        )
    with pytest.raises(ValueError):
        replay.reforecast(
            x, scenarios=0, candidates=5, random_reps=1
        )
    with pytest.raises(ValueError):
        replay.reforecast(
            x, scenarios=8, candidates=5, random_reps=1,
            actual_dates=["2026-01-01"],
        )
