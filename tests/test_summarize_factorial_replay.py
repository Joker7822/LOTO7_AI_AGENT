"""Validate paired full-history replay summaries and fail-closed metadata."""
import copy

import pytest

import signal_portfolio_factorial as replay
import summarize_factorial_replay as summary
from test_signal_portfolio_factorial import synthetic_history


@pytest.fixture(scope="module")
def synthetic_replay():
    return replay.evaluate(
        synthetic_history(130), min_train=100, last_n=5,
        scenarios=16, candidates=10, random_reps=2, seed=400,
    )


def test_reconciles_all_scores_and_signals(synthetic_replay):
    result = summary.summarize(synthetic_replay, windows=(2, 5))
    assert result["evaluated_rounds"] == 5
    assert set(result["windows"]) == {"2", "5"}
    assert result["windows"]["2"]["from_round"] == 129
    assert result["windows"]["5"]["from_round"] == 126
    for arm in replay.ARMS:
        assert result["windows"]["5"]["arm_scores"][arm] == pytest.approx(
            synthetic_replay["arms"][arm]["score"]
        )
    assert not result["independent_evidence"]
    assert not result["promotion_authorized"]
    for value in result["windows"]["5"]["paired_arm_score_deltas"].values():
        assert value["rounds"] == 5
        assert value["low95"] <= value["high95"]
    assert summary.summarize(synthetic_replay, windows=(2, 5)) == result


def test_rejects_incomplete_full_history(synthetic_replay):
    with pytest.raises(ValueError, match="600-round claims"):
        summary.summarize(synthetic_replay, windows=(5, 600))


def test_rejects_false_future_or_promotion_flags(synthetic_replay):
    for field in ("promotion_authorized", "production_changed",
                  "future_oos_changed", "independent_evidence"):
        changed = copy.deepcopy(synthetic_replay)
        changed[field] = True
        with pytest.raises(ValueError, match="safety flags"):
            summary.summarize(changed, windows=(5,))


def test_rejects_missing_round_or_tampered_score(synthetic_replay):
    missing = copy.deepcopy(synthetic_replay)
    missing["rounds"].pop(0)
    with pytest.raises(ValueError, match="nonchronological"):
        summary.summarize(missing, windows=(4,))
    altered = copy.deepcopy(synthetic_replay)
    altered["rounds"][0]["arm_metrics"]["model_random"]["score"] += 0.4
    with pytest.raises(ValueError, match="reconcile"):
        summary.summarize(altered, windows=(5,))
    mismatched = copy.deepcopy(synthetic_replay)
    mismatched["rounds"][0]["signal_metrics"]["legacy"]["log_edge"] += 0.8
    with pytest.raises(ValueError, match="reconcile"):
        summary.summarize(mismatched, windows=(5,))


def test_score_replay_prefix_does_not_change_existing_forecast():
    x = synthetic_history(131)
    first = replay.evaluate(x[:130], min_train=100, last_n=1,
                            scenarios=16, candidates=10, random_reps=2)
    extended = replay.evaluate(x, min_train=100, last_n=2,
                               scenarios=16, candidates=10, random_reps=2)
    assert first["rounds"][0]["round_index"] == 130
    assert extended["rounds"][0]["round_index"] == 130
    assert first["rounds"][0]["forecast_sha256"] == extended["rounds"][0]["forecast_sha256"]
    assert first["rounds"][0]["portfolio_sha256"] == extended["rounds"][0]["portfolio_sha256"]
    assert first["rounds"][0]["arm_metrics"] == extended["rounds"][0]["arm_metrics"]
    assert first["rounds"][0]["signal_metrics"] == extended["rounds"][0]["signal_metrics"]
