import csv
import json
from pathlib import Path

import numpy as np
import pytest

import joint_set_v2_conversion_audit as a
from joint_set_v2_model import (
    ForecastBundle, N_NUMBERS, PICKS, UNIFORM_INCLUSION,
    bernoulli_signal_metrics, candidate_configs, portfolio_metrics,
)


def uniform_bundle():
    p = np.full(N_NUMBERS, UNIFORM_INCLUSION, dtype=float)
    return ForecastBundle(
        inclusion_p=p.copy(), raw_inclusion_p=p.copy(),
        pair_matrix=np.zeros((N_NUMBERS, N_NUMBERS)), regime=np.array([1., 0., 0.]),
        gate=0.0, effective_pair_strength=0.0, gate_diagnostics={},
    )


def test_scenario_score_is_exact_actual_portfolio_score():
    tickets = [tuple(range(1 + i, 8 + i)) for i in range(5)]
    actuals = [
        set(range(1, 8)), set(range(8, 15)), set(range(1, 15, 2)),
    ]
    hits = np.array([
        [len(set(ticket) & actual) for ticket in tickets]
        for actual in actuals
    ])
    scores = a.scenario_score(hits)
    expected = [portfolio_metrics(tickets, actual)["score"] for actual in actuals]
    np.testing.assert_allclose(scores, expected, atol=1e-12, rtol=0)


def test_candidate_scores_match_exact_portfolio_formula():
    hits = np.array([[0, 1, 3, 2], [4, 3, 1, 0], [2, 2, 4, 3]])
    for selected in ([], [1], [0, 3]):
        scores = a.mean_candidate_scores(hits, selected)
        for j in range(hits.shape[1]):
            expected = a.scenario_score(hits[:, list(selected) + [j]]).mean()
            assert scores[j] == pytest.approx(expected)


def test_aligned_optimizer_is_deterministic_and_five_unique_tickets():
    b = uniform_bundle()
    first, stats = a.aligned_objective_portfolio(
        b, seed=33019, scenarios=20, candidate_count=12,
    )
    second, other_stats = a.aligned_objective_portfolio(
        b, seed=33019, scenarios=20, candidate_count=12,
    )
    assert first == second
    assert stats == other_stats
    assert len(first) == len(set(first)) == 5
    for ticket in first:
        assert len(ticket) == len(set(ticket)) == PICKS
        assert all(1 <= n <= 37 for n in ticket)


def test_aligned_train_objective_matches_replayed_training_sample():
    b = uniform_bundle()
    seed = 10110
    tickets, stats = a.aligned_objective_portfolio(
        b, seed, scenarios=20, candidate_count=12,
    )
    scenarios = a.sample_joint_sets(b, 20, seed=seed + 11)
    assert a.scenario_portfolio_mean(tickets, scenarios) == pytest.approx(stats["train_objective"])


def test_bootstrap_paired_zero_effect_and_validation():
    ci = a.bootstrap_paired([0, 0, 0, 0], reps=20)
    assert ci["mean"] == ci["low95"] == ci["high95"] == 0
    with pytest.raises(ValueError, match="empty"):
        a.bootstrap_paired([])


def test_raw_rank_bucket_partitions_all_37_numbers():
    bucket = {}
    from collections import defaultdict
    buckets = defaultdict(lambda: {
        "count": 0.0, "realized": 0.0,
        "raw_probability": 0.0, "gated_probability": 0.0,
    })
    raw = np.linspace(0.11, 0.29, N_NUMBERS)
    raw *= PICKS / raw.sum()
    gated = np.full(N_NUMBERS, UNIFORM_INCLUSION)
    y = np.zeros(N_NUMBERS)
    y[:7] = 1
    a.append_rank_buckets(buckets, raw, gated, y)
    assert sum(int(v["count"]) for v in buckets.values()) == N_NUMBERS
    assert sum(v["realized"] for v in buckets.values()) == PICKS
    assert sum(v["raw_probability"] for v in buckets.values()) == pytest.approx(PICKS)


def test_stored_historical_rounds_must_be_unique_and_contiguous(tmp_path):
    path = tmp_path / "v2.csv"
    path.write_text("round_index\n699\n699\n", encoding="utf-8")
    with pytest.raises(ValueError, match="contiguous"):
        a.load_historical_rows(path)


def test_end_to_end_audit_rejects_replay_mismatch_and_never_adopts(monkeypatch, tmp_path):
    # Synthetic historical outcomes only: it never writes to real output or shadow state.
    csv_path = tmp_path / "loto7.csv"
    with csv_path.open("w", encoding="utf-8") as f:
        f.write("抽せん日,本数字,回別\n")
        from datetime import date, timedelta
        date0 = date(2013, 4, 5)
        for n in range(1, 141):
            f.write(f"{date0 + timedelta(days=(n-1)*7)},01 02 03 04 05 06 07,第{n}回\n")

    saved_path = tmp_path / "saved.csv"
    cfg = candidate_configs()[0]
    b = uniform_bundle()
    metrics = bernoulli_signal_metrics(b.inclusion_p, np.arange(7))
    baseline = [tuple(range(j + 1, j + 8)) for j in range(5)]
    score = portfolio_metrics(baseline, set(range(1, 8)))["score"]
    with saved_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "round_index", "selected_config", "gate", "signal_top7_hits",
            "signal_log_edge", "portfolio_score",
        ])
        w.writeheader()
        for n in (139, 140):
            w.writerow({
                "round_index": n, "selected_config": cfg.version(),
                "gate": 0., "signal_top7_hits": metrics["top7_hits"],
                "signal_log_edge": metrics["log_edge"], "portfolio_score": score,
            })
    summary_path = tmp_path / "nested.json"
    summary_path.write_text(json.dumps({
        "evaluation_type": "strict_prior_only_prequential_inclusion_probability_joint_set_v2",
        "evaluated_rounds": 2,
        "min_train": 100,
        "validation_scenarios": 12,
        "validation_candidates": 8,
        "config_versions": [cfg.version()],
        "data_sha256": "synthetic-for-unit-test",
    }))
    monkeypatch.setattr(a, "build_prequential_signal", lambda *args: [{}] * 40)
    monkeypatch.setattr(a, "forecast", lambda *args: b)
    monkeypatch.setattr(a, "expected_utility_portfolio", lambda *args, **kwargs: (baseline, {}))
    monkeypatch.setattr(a, "aligned_objective_portfolio", lambda *args, **kwargs: (baseline, {}))
    monkeypatch.setattr(a, "sample_joint_sets",
                        lambda *args, **kwargs: np.tile(np.arange(1, 8), (args[1], 1)))
    report = a.audit(csv_path, saved_path, summary_path, tmp_path / "research", rounds=2, independent_scenarios=13)
    assert report["historical_rounds"] == 2
    assert report["promotion_eligible"] is False
    assert report["independent_evidence"] is False
    assert report["portfolio"]["aligned_minus_baseline_realized_paired"]["mean"] == 0.
    assert report["baseline_reconstruction_verified_rounds"] == 2
    assert (tmp_path / "research" / "joint_set_v2_conversion_audit_rows.csv").exists()
    assert not (tmp_path / "research" / "joint_set_v2_signal_oos_registration.json").exists()

    # A changed reference real-outcome score invalidates the benchmark.
    text = saved_path.read_text()
    saved_path.write_text(text.replace(str(score), "0.0"))
    with pytest.raises(RuntimeError, match="not reconstructed"):
        a.audit(csv_path, saved_path, summary_path, tmp_path / "broken", rounds=2)
