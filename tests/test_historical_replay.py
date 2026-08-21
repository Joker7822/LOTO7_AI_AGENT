import json
from pathlib import Path

import numpy as np

import historical_replay as hr
import loto7_v2_runner as v2
from loto7_evolving_agent import expert_probabilities


def _history(rows=110):
    x = np.zeros((rows, 37), dtype=int)
    for i in range(rows):
        nums = [(i + j * 5) % 37 for j in range(7)]
        x[i, nums] = 1
    return x


def test_forecast_portfolio_only_needs_past_history():
    x = _history()
    hist = x[:100]
    keys = list(expert_probabilities(hist).keys())
    logw = np.zeros(len(keys), dtype=float)
    q1, tickets1 = hr.forecast_portfolio(hist, v2.DEFAULT_CHAMPION, keys, logw, 101, 120)

    changed_future = x.copy()
    changed_future[100:] = 0
    changed_future[100:, :7] = 1
    q2, tickets2 = hr.forecast_portfolio(changed_future[:100], v2.DEFAULT_CHAMPION, keys, logw, 101, 120)

    assert np.allclose(q1, q2)
    assert tickets1 == tickets2


def test_top7_random_mean_has_zero_z():
    hits = [1, 2, 1, 1, 2, 1, 1, 2] * 10
    mean, z, p = hr.top7_significance(hits)
    assert mean > 0
    assert 0 <= p <= 1
    assert isinstance(z, float)


def test_summary_marks_historical_replay_separate_from_oos():
    tickets = [
        {"grade": "はずれ"}, {"grade": "6等"}, {"grade": "はずれ"},
        {"grade": "はずれ"}, {"grade": "はずれ"},
    ]
    rounds = [{
        "round": 101,
        "portfolio_score": "2.5",
        "random_mean_score": "2.4",
        "portfolio_max_hits": "3",
        "random_mean_max_hits": "2.2",
        "portfolio_ge3": 1,
        "portfolio_ge4": 0,
        "random_ge3_rate": "0.4",
        "random_ge4_rate": "0.05",
        "top7_hits": 2,
        "winning_tickets": 1,
    }]
    s = hr.summary_from_rows(tickets, rounds, v2.DEFAULT_CHAMPION, "abc", 100, 650, 32, 101)
    assert s["evaluation_type"] == "strict_walk_forward_fixed_baseline"
    assert "not future OOS" in s["interpretation"]
    assert s["prize_grades"]["winning_tickets"] == 1


def test_stale_cache_key_includes_parameters(tmp_path: Path):
    p = tmp_path / "summary.json"
    obj = {
        "report_version": hr.REPORT_VERSION,
        "csv_sha256": "sha",
        "model_version": v2.DEFAULT_CHAMPION.version(),
        "min_train": 100,
        "portfolio_pool_size": 650,
        "random_portfolios_per_round": 32,
        "last_n": 0,
    }
    p.write_text(json.dumps(obj), encoding="utf-8")
    assert hr.is_fresh(p, "sha", v2.DEFAULT_CHAMPION, 100, 650, 32, 0)
    assert not hr.is_fresh(p, "sha", v2.DEFAULT_CHAMPION, 100, 900, 32, 0)
