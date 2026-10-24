"""Regression tests for an explicitly versioned, non-promotable numerical repair."""
import copy
import json
from pathlib import Path

import numpy as np
import pytest

import pair_context_v2 as v2
from loto7_evolving_agent import expert_probabilities, make_history, read_csv_flexible
from agent_operations_planner import build_plan
from tests.test_agent_operations_planner import snapshot


def test_int8_matrix_overflow_is_fixed_before_multiplication():
    x = np.zeros((128, 37), dtype=np.int8)
    x[:, :7] = 1
    legacy_co = x.T @ x
    assert np.all(legacy_co[:7, :7] == -128)
    correct = v2.exact_cooccurrence(x)
    assert np.all(correct[:7, :7] == 128)
    assert np.count_nonzero(legacy_co.astype(np.int64) != correct) == 49
    actual = v2.probability(x)
    assert actual.shape == (37,)
    assert np.isfinite(actual).all()
    assert (actual > 0).all()
    assert actual.sum() == pytest.approx(1.0, abs=1e-12)
    assert not np.allclose(actual, v2.legacy_probability(x))


def test_fixed_math_agrees_with_original_before_int8_wrap():
    rng = np.random.default_rng(774)
    x = np.zeros((80, 37), dtype=np.int8)
    for row in x:
        row[rng.choice(37, size=7, replace=False)] = 1
    np.testing.assert_allclose(
        v2.probability(x), expert_probabilities(x)["pair_context"], rtol=0, atol=1e-14
    )
    np.testing.assert_allclose(
        v2.legacy_probability(x), expert_probabilities(x)["pair_context"], rtol=0, atol=1e-14
    )


def test_corrected_candidate_cannot_use_future_result():
    rng = np.random.default_rng(299)
    x = np.zeros((160, 37), dtype=np.int8)
    for row in x:
        row[rng.choice(37, size=7, replace=False)] = 1
    original = v2.probability(x[:139])
    modified = x.copy()
    modified[139:] = 0
    modified[139:, :7] = 1
    np.testing.assert_array_equal(original, v2.probability(modified[:139]))


@pytest.mark.parametrize("bad", [
    np.zeros((20, 37), dtype=np.int8),
    np.ones((25, 36), dtype=np.int8),
    np.ones((19, 37), dtype=np.int8),
    np.full((30, 37), 2, dtype=np.int64),
    np.ones((28, 37), dtype=float),
])
def test_rejects_malformed_prospective_inputs(bad):
    with pytest.raises(ValueError):
        v2.probability(bad)


def test_real_draws_are_examined_without_evidence_changes(tmp_path):
    csv = Path("loto7.csv")
    before = csv.read_bytes()
    report = v2.diagnostics(csv, last_n=15)
    assert report["version"] == v2.VERSION
    assert report["history_draws"] >= 699
    assert report["int64_corrupted_cooccurrence_cells"] == 0
    assert report["int8_corrupted_cooccurrence_cells"] >= 0
    assert report["evaluated_rounds"] == list(range(
        report["history_draws"] - 14, report["history_draws"] + 1
    ))
    assert report["chronological_prior_only"]
    assert report["historical_selection_only"]
    assert not report["independent_evidence"]
    assert not report["prospective_edge_confirmed"]
    assert report["legacy_runtime_still_uses_v1"]
    assert not report["production_changed"]
    assert not report["future_oos_changed"]
    assert not report["promotion_authorized"]
    assert len(report["latest_v2_p_sha256"]) == 64
    assert csv.read_bytes() == before
    assert not list(tmp_path.iterdir())


def test_registered_frozen_experiment_implementation_is_not_changed():
    # Existing baseline and official frozen forecasts must replay identically.
    # A separate v2 module means old one is still addressable.
    legacy = Path("loto7_evolving_agent.py").read_text(encoding="utf-8")
    assert "co = hist.T @ hist" in legacy
    assert "from loto7_evolving_agent import" in Path("loto7_v2_runner.py").read_text()
    assert "pair_context_v2" not in Path("loto7_v2_runner.py").read_text()
    assert "pair_context_v2" not in Path("weekly_production_prediction.py").read_text()


def test_26_draws_waiting_is_informational_after_both_701_freezes():
    data = snapshot()
    data["sources"]["source"]["latest"]["round"] = 700
    data["sources"]["holdout"]["trusted_draws"] = 7
    data["sources"]["signal"]["current_target_round"] = 701
    data["sources"]["learning"]["current_prefrozen_target"] = 701
    plan = build_plan(data)
    assert plan["counts"]["watch"] == 0
    assert plan["counts"]["info"] == 1
    assert plan["overall"] == "ok"
    item = next(t for t in plan["tasks"] if t["code"] == "COUNCIL:NO_EARLY_PORTFOLIO_CLAIM")
    assert item["priority"] == "info"
    assert not plan["authority"]["model_promotions"]


def test_missing_701_freeze_does_not_hide_holdout_warning():
    data = snapshot()
    data["sources"]["source"]["latest"]["round"] = 700
    data["sources"]["signal"]["current_target_round"] = 701
    data["sources"]["learning"]["current_prefrozen_target"] = None
    plan = build_plan(data)
    assert any(t["code"] == "COUNCIL:NO_EARLY_PORTFOLIO_CLAIM"
               and t["priority"] == "watch" for t in plan["tasks"])
    assert any(t["code"] == "FIRST_FREEZE_REQUIRED:learning" for t in plan["tasks"])


def test_never_label_incomplete_horizon_as_confirmed():
    data = snapshot()
    data["sources"]["source"]["latest"]["round"] = 700
    data["sources"]["signal"]["current_target_round"] = 701
    data["sources"]["learning"]["current_prefrozen_target"] = 701
    data["sources"]["holdout"]["trusted_draws"] = 6
    data["series"]["portfolio"].pop()
    plan = build_plan(data)
    assert plan["checkpoints"]["portfolio"]["trusted_draws"] == 6
    assert plan["checkpoints"]["portfolio"]["fixed_horizon"] == 26
    assert plan["overall"] == "ok"
    assert "confirmed" not in json.dumps(plan).lower()
