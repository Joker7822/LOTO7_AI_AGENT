"""Mathematical checks for the research-only disjoint portfolio strategy."""
import math

import numpy as np
import pytest

import balanced_uniform_portfolio as geometry
import full_round2_reforecast as replay


@pytest.mark.parametrize("seed", [0, 1, 2, 17, 20261025, 2147483647])
def test_covers_35_distinct_numbers_with_no_ticket_overlap(seed):
    tickets = geometry.disjoint_portfolio(seed)
    assert tickets == geometry.disjoint_portfolio(seed)
    assert len(tickets) == 5
    assert len({n for ticket in tickets for n in ticket}) == 35
    assert all(len(ticket) == 7 and len(set(ticket)) == 7 for ticket in tickets)
    assert all(tuple(ticket) == tuple(sorted(ticket)) for ticket in tickets)
    assert set(range(1, 38)) - {n for t in tickets for n in t}


def test_disjoint_null_is_exact_and_has_correct_symmetries():
    report = geometry.exact_disjoint_null()
    baseline = geometry.exact_independent_random_null()
    assert report["total_possible_draws"] == math.comb(37, 7)
    assert report["covered_distinct_numbers"] == 35
    assert report["mean_hits"] == pytest.approx(49.0 / 37.0, abs=1e-14)
    assert report["any_first_prize_probability"] == pytest.approx(
        5.0 / math.comb(37, 7), abs=1e-15
    )
    assert report["score"] == pytest.approx(
        report["max_hits"] + 0.35 * report["ge3"] +
        0.75 * report["ge4"] + 0.10 * report["mean_hits"], abs=1e-14
    )
    assert 2.94 < report["score"] < 2.97
    assert report["score"] > baseline["score"]
    assert report["ge3"] > baseline["ge3"]
    assert report["ge4"] > 0
    assert report["exact"] and baseline["exact"]
    assert not geometry.theory_report()["production_changed"]
    assert not geometry.theory_report()["promotion_authorized"]
    assert geometry.theory_report()["no_predictive_signal_claim"]


def test_theoretical_score_is_not_fitted_to_history(monkeypatch):
    # Mathematical benchmark must not depend on the draw archive, seed, or
    # any existing model. It is a pure, exact combinatorial enumeration.
    one = geometry.theory_report()
    two = geometry.theory_report()
    assert one == two


@pytest.mark.parametrize("invalid", [
    [(1, 2, 3, 4, 5, 6, 7)] * 5,
    [(1, 2, 3, 4, 5, 6, 38)] * 5,
    [],
])
def test_invalid_portfolios_fail_closed(invalid):
    with pytest.raises(ValueError):
        geometry.validate_portfolio(invalid)


def test_replay_contains_disjoint_arm_and_hashed_pre_result():
    rng = np.random.default_rng(215)
    x = np.zeros((22, 37), dtype=np.int8)
    for row in x:
        row[rng.choice(37, 7, replace=False)] = 1
    report = replay.reforecast(
        x, scenarios=8, candidates=5, random_reps=1, seed=303
    )
    assert "uniform_disjoint" in report["portfolio_arms"]
    assert "fair_world_exact_theory" in report
    assert report["evaluated_rounds"] == 21
    assert not report["independent_evidence"]
    for record in report["rounds"]:
        tickets = [tuple(t) for t in record["tickets"]["uniform_disjoint"]]
        geometry.validate_portfolio(tickets)
        assert record["portfolio"]["uniform_disjoint"]["score"] >= 0


def test_changing_target_after_freeze_does_not_change_disjoint_tickets():
    rng = np.random.default_rng(44)
    x = np.zeros((22, 37), dtype=np.int8)
    for row in x:
        row[rng.choice(37, 7, replace=False)] = 1
    y = x.copy()
    y[-1] = 0
    y[-1, 30:37] = 1
    a = replay.reforecast(x, scenarios=8, candidates=5, random_reps=1, seed=303)["rounds"][-1]
    b = replay.reforecast(y, scenarios=8, candidates=5, random_reps=1, seed=303)["rounds"][-1]
    assert a["tickets"]["uniform_disjoint"] == b["tickets"]["uniform_disjoint"]
    assert a["forecast_sha256"] == b["forecast_sha256"]
