import json
from pathlib import Path

import numpy as np
import pytest

import predictive_expert_agent as a
from joint_set_v2_model import N_NUMBERS, PICKS, UNIFORM_INCLUSION


def fair(seed, n=180):
    return a.synthetic_fair_history(n, seed)


def test_synthetic_draws_have_exactly_seven_unique_hits():
    x = fair(1000)
    assert x.shape == (180, N_NUMBERS)
    assert np.all(x.sum(axis=1) == PICKS)
    assert np.all((x == 0) | (x == 1))


def test_experts_are_calibrated_valid_inclusion_vectors():
    x = fair(2828)
    cumulative = np.vstack((np.zeros((1, N_NUMBERS), dtype=int),
                            np.cumsum(x.astype(int), axis=0)))
    for t in (10, 100, 179):
        vec = a.expert_vectors(cumulative, t)
        assert vec.shape == (4, N_NUMBERS)
        np.testing.assert_allclose(vec.sum(axis=1), np.full(4, PICKS), atol=1e-9)
        assert np.all(vec >= 0) and np.all(vec <= 1)
        assert np.all(vec[0] == UNIFORM_INCLUSION)


def test_weights_prior_and_highly_negative_signal_reverts_to_uniform():
    assert tuple(a.EXPERTS) == (
        "uniform", "bayes_short40", "bayes_long160", "momentum_shrink"
    )
    w = a.weights_from_prior_scores(np.zeros(4))
    np.testing.assert_allclose(w, a.PRIOR, atol=1e-12)
    w = a.weights_from_prior_scores(np.array([0., -100., -100., -100.]))
    assert w[0] > 0.9999
    assert np.all(w >= 0)
    assert w.sum() == pytest.approx(1.)


def test_full_walk_reproducible_fixed_seed_and_no_future_target_leakage():
    x = fair(711, 180)
    unchanged, saved_rows = a.walk(x, min_train=100, last_n=40)
    again, same_rows = a.walk(x, min_train=100, last_n=40)
    assert saved_rows == same_rows
    assert unchanged == again
    assert len(saved_rows) == 40
    assert list(range(141, 181)) == [r["round_index"] for r in saved_rows]
    assert sum(row["observations"] for row in unchanged["rank_bucket_calibration"]) == 40*37
    assert all(abs(sum(r[k] for k in (
        "weight_uniform", "weight_short", "weight_long", "weight_momentum")) - 1) < 1e-10
               for r in saved_rows)

    # Change the outcome at the final target. The forecaster's target-time
    # weights, learned solely from 179 earlier draws, must remain identical.
    changed = x.copy()
    changed[-1] = 0
    changed[-1, 7:14] = 1
    _, changed_rows = a.walk(changed, min_train=100, last_n=40)
    for key in ("weight_uniform", "weight_short", "weight_long", "weight_momentum"):
        assert changed_rows[-1][key] == saved_rows[-1][key]
    assert changed_rows[:-1] == saved_rows[:-1]


def test_algorithm_handles_no_outcome_signal_without_computed_advantage():
    x = fair(9000, 180)
    summary, _ = a.walk(x, 100, 40)
    assert np.isfinite(summary["mean_log_edge_vs_uniform"])
    assert np.isfinite(summary["mean_brier_edge_vs_uniform"])
    assert 0 <= summary["mean_top7_hits"] <= 7


def test_full_budget_matched_fair_null_is_reproducible():
    n = a.full_budget_synthetic_null(165, 100, 30, worlds=4)
    n2 = a.full_budget_synthetic_null(165, 100, 30, worlds=4)
    assert n == n2
    assert n["worlds"] == 4
    assert n["matching_algorithm_and_history_length"] is True
    assert 0 <= a.upper_tail_p(0.0, n["null_log_edges"]) <= 1
    assert a.upper_tail_p(1e6, n["null_log_edges"]) == pytest.approx(1 / 5)


def test_fail_closed_malformed_data_or_invalid_test_window():
    x = fair(44, 140)
    invalid = x.copy()
    invalid[99, :] = 0  # guaranteed malformed: no winning numbers at this draw
    with pytest.raises(ValueError, match="exactly seven"):
        a.walk(invalid, 100, 30)
    with pytest.raises(ValueError, match="test window"):
        a.walk(x, 100, 50)
    with pytest.raises(ValueError, match="world budget"):
        a.full_budget_synthetic_null(150, 100, 30, worlds=0)
    with pytest.raises(ValueError, match="empty"):
        a.mean_bootstrap_ci([])


def test_research_pipeline_writes_own_three_outputs_no_shadow_mutation(tmp_path):
    # Synthetic CSV deliberately held in a separate temporary repository
    # fixture so registered prospective evidence can never be generated here.
    x = fair(12019, 165)
    from datetime import date, timedelta
    path = tmp_path / "mock_draws.csv"
    with path.open("w", encoding="utf-8") as f:
        f.write("抽せん日,本数字,回別\n")
        for i, values in enumerate(x):
            nums = " ".join(str(n+1) for n in np.flatnonzero(values))
            f.write(f"{date(2013, 4, 5) + timedelta(days=7*i)},{nums},第{i+1}回\n")
    output = tmp_path / "research_only"
    summary = a.run(path, output, min_train=100, last_n=30,
                    worlds=3, v2_saved_summary=tmp_path / "absent.json")
    assert summary["promotion_eligible"] is False
    assert summary["independent_evidence"] is False
    assert summary["prospective_shadow_updated"] is False
    assert summary["handoff"]["automatic_model_adoption"] is False
    assert summary["scout"]["mean_top7_hits"] >= 0
    assert sorted(p.name for p in output.iterdir()) == [
        "predictive_expert_agent_report.md",
        "predictive_expert_agent_rounds.csv",
        "predictive_expert_agent_summary.json",
    ]
    assert not any("joint_set_v2_signal_oos" in p.name for p in output.iterdir())

    # Retrospective comparator matching a *different* dataset must be rejected.
    bad_ref = tmp_path / "bad_summary.json"
    bad_ref.write_text(json.dumps({
        "data_sha256": "an unrelated data revision", "evaluated_rounds": 30,
        "evaluation_type": "strict_prior_only_prequential_inclusion_probability_joint_set_v2",
    }))
    with pytest.raises(ValueError, match="stale"):
        a.run(path, tmp_path / "rejected", min_train=100, last_n=30,
              worlds=1, v2_saved_summary=bad_ref)


def test_code_does_not_import_production_publisher_or_write_nonreport_files():
    text = Path("predictive_expert_agent.py").read_text(encoding="utf-8")
    for forbidden in (
        "weekly_production_prediction", "strict_oos_governance",
        "model_champion.json", "future_holdout_registry.json",
        "joint_set_v2_signal_oos_registry.json",
    ):
        assert forbidden not in text
