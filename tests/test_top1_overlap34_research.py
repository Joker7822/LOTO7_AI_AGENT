"""34-number Top1-double geometry and leakage-control regression tests."""
from pathlib import Path

import numpy as np
import pytest

import balanced_uniform_portfolio as disjoint
import signal_portfolio_factorial as metrics
import top1_overlap34 as model
import top1_overlap34_research as research
from loto7_evolving_agent import expert_probabilities


def synthetic(n=25, seed=21):
    rng = np.random.default_rng(seed)
    rows = np.zeros((n, 37), dtype=np.int8)
    for r in rows:
        r[rng.choice(37, size=7, replace=False)] = 1
    return rows


@pytest.mark.parametrize("top1", [1, 2, 17, 37])
@pytest.mark.parametrize("seed", [0, 1, 20261025])
def test_only_selected_top1_is_duplicated_twice(top1, seed):
    tickets = model.make_portfolio(top1, seed)
    assert tickets == model.make_portfolio(top1, seed)
    model.validate_tickets(tickets, top1)
    counts = {n: sum(n in t for t in tickets) for n in range(1, 38)}
    assert counts[top1] == 2
    assert sorted(counts.values()).count(2) == 1
    assert sorted(counts.values()).count(1) == 33
    assert sorted(counts.values()).count(0) == 3
    assert len({n for t in tickets for n in t}) == 34
    assert set(tickets[0]) & set(tickets[1]) == {top1}
    for i in range(5):
        for j in range(i + 1, 5):
            assert len(set(tickets[i]) & set(tickets[j])) == (
                1 if (i, j) == (0, 1) else 0
            )


@pytest.mark.parametrize("invalid", [-1, 0, 38, 0.5, "7", None])
def test_reject_bad_anchor(invalid):
    with pytest.raises((ValueError, TypeError)):
        model.make_portfolio(invalid, 17)


def test_exact_fair_null_preserves_score_identity():
    m = model.exact_fair_null()
    d = disjoint.exact_disjoint_null()
    assert m["exact"]
    assert m["total_possible_draws"] == 10_295_472
    assert m["distinct_numbers"] == 34
    assert m["shared_number_copies"] == 2
    assert m["mean_hits"] == pytest.approx(49.0 / 37.0, abs=1e-14)
    assert m["score"] == pytest.approx(
        m["max_hits"] + 0.35 * m["ge3"] +
        0.75 * m["ge4"] + 0.10 * m["mean_hits"], abs=1e-14
    )
    assert m["score"] == pytest.approx(2.941705965496288, abs=1e-12)
    assert m["ge3"] == pytest.approx(0.5040983065176614, abs=1e-12)
    assert m["first_prize_probability"] == pytest.approx(
        d["any_first_prize_probability"]
    )
    assert m["score"] < d["score"]
    assert m["ge3"] < d["ge3"]


def test_seeded_uniform_anchor_is_unbiased_tie_resolution():
    uniform = np.full(37, 1 / 37)
    a = research.top1_from_q(uniform, 101)
    assert a == research.top1_from_q(uniform, 101)
    assert 1 <= a <= 37
    choices = {research.top1_from_q(uniform, seed) for seed in range(50)}
    assert len(choices) >= 15


def test_uses_previous_draws_only_and_scores_actual_tickets():
    x = synthetic(25)
    result = research.evaluate(x, seed=303)
    assert result["evaluated_rounds"] == 24
    assert result["first_target_round"] == 2
    assert result["last_target_round"] == 25
    assert result["periods"]["cold_start_2_to_20"]["count"] == 19
    assert result["periods"]["online_21_to_latest"]["count"] == 5
    for row in result["rows"]:
        assert row["prior_draws"] == row["round"] - 1
        assert set(row["tickets"]) == set(research.ARMS)
        model.validate_tickets(
            [tuple(t) for t in row["tickets"]["legacy_top1_overlap34"]],
            row["legacy_top1"],
        )
        model.validate_tickets(
            [tuple(t) for t in row["tickets"]["uniform_anchor_overlap34"]],
            row["uniform_anchor"],
        )
        disjoint.validate_portfolio(
            [tuple(t) for t in row["tickets"]["uniform_disjoint35"]]
        )
        for arm in research.ARMS:
            calculated = metrics.ticket_metrics(
                [tuple(t) for t in row["tickets"][arm]],
                set(row["actual_numbers"])
            )
            assert row["scores"][arm] == calculated
        if row["round"] <= 20:
            assert row["legacy_top1"] == row["uniform_anchor"]
            assert row["tickets"]["legacy_top1_overlap34"] == (
                row["tickets"]["uniform_anchor_overlap34"]
            )
    assert not result["independent_evidence"]
    assert not result["pre_registered_prospective_evidence"]
    assert not result["production_changed"]
    assert not result["existing_future_oos_changed"]
    assert not result["promotion_authorized"]


def test_current_target_change_does_not_affect_prior_forecast():
    x = synthetic(25, seed=99)
    changed = x.copy()
    changed[-1] = 0
    changed[-1, 30:37] = 1
    a = research.evaluate(x, seed=44)["rows"][-1]
    b = research.evaluate(changed, seed=44)["rows"][-1]
    assert a["pre_outcome_forecast_sha256"] == b["pre_outcome_forecast_sha256"]
    assert a["legacy_top1"] == b["legacy_top1"]
    assert a["tickets"] == b["tickets"]


def test_no_writes_to_production_or_any_record(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    output = research.evaluate(synthetic(25), seed=42)
    assert output["evaluated_rounds"] == 24
    assert not list(Path(".").iterdir())


def test_exact_repeatability_and_weighting():
    x = synthetic(24, seed=77)
    a, b = research.evaluate(x, seed=2026), research.evaluate(x, seed=2026)
    assert a == b
    ex = expert_probabilities(x[:20])
    assert len(ex) > 0


@pytest.mark.parametrize("bad", [
    np.zeros((25, 37), dtype=np.int8),
    np.ones((25, 37), dtype=np.int8),
    np.ones((25, 37), dtype=float),
    np.zeros((25, 36), dtype=np.int8),
    synthetic(20),
])
def test_invalid_history_fails_closed(bad):
    with pytest.raises(ValueError):
        research.evaluate(bad)


def test_invalid_probability_rank_fails_closed():
    with pytest.raises(ValueError):
        research.top1_from_q(np.zeros(37), seed=7)
    with pytest.raises(ValueError):
        research.top1_from_q(np.ones(36) / 36, seed=7)
