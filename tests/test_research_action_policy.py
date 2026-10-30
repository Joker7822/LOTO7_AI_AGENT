"""Deterministic, fail-closed tests for research-agent policy self-tuning."""
from __future__ import annotations

import copy

import pytest

import research_action_policy as policy


def task(name: str, impact: int, state: str = "routine_monitoring",
         severity: str = "watch") -> dict:
    delta = 1 if state == "regression_needs_review" else (
        -1 if state == "observed_progress" else 0)
    feedback = "unchanged" if state == "stalled_needs_review" else (
        "still_pending_unmeasured" if state == "human_review_pending" else (
            "worsening" if delta > 0 else "improving" if delta < 0 else "unchanged"
        ))
    return {
        "id": name, "code": name, "priority": severity,
        "attention_state": state, "feedback_state": feedback,
        "stagnation_cycles": 3 if state == "stalled_needs_review" else 0,
        "recurrence_cycles": 4 if state == "human_review_pending" else 1,
        "backlog_observed": 2, "backlog_delta": delta,
        "priority_factors": {"impact": impact,
                             "verified_backlog": 0,
                             "unresolved_recurrence": 0,
                             "observed_trend": 0},
        "priority_score": impact,
        "safe_autonomous_action": "report_only",
        "new_optimizer_trials_authorized": False,
        "forecast_or_production_change_authorized": False,
    }


def test_auto_selects_observed_regression_focus_when_proxy_strictly_improves():
    source = [task("ROUTINE", 60), task("REGRESSION", 55, "regression_needs_review")]
    frozen = copy.deepcopy(source)
    selected, audit = policy.autotune(source)
    assert source == frozen
    assert selected[0]["code"] == "REGRESSION"
    assert audit["selected_policy"] == "regression_focus"
    assert audit["candidate_objectives"]["regression_focus"] > audit[
        "candidate_objectives"]["balanced"]
    assert selected[0]["priority_factors"]["bounded_policy_bonus"] == 8
    assert selected[0]["priority_score"] == sum(
        selected[0]["priority_factors"].values())
    assert audit["automatic_code_or_model_change_authorized"] is False
    assert audit["empirical_agent_productivity_improvement_established"] is False
    assert audit["lottery_prediction_improvement_established"] is False


def test_three_unchanged_cycles_trigger_stagnation_focused_policy():
    tasks = [task("ROUTINE", 58), task("STALLED", 52, "stalled_needs_review")]
    chosen, meta = policy.autotune(tasks)
    assert chosen[0]["code"] == "STALLED"
    assert meta["selected_policy"] == "stagnation_focus"
    assert chosen[0]["priority_factors"]["bounded_policy_bonus"] <= 8


def test_no_signal_adopts_baseline_and_is_byte_stable():
    tasks = [task("A", 90), task("B", 70), task("C", 15, severity="info")]
    one = policy.autotune(tasks)
    two = policy.autotune(tasks)
    assert one == two
    assert one[1]["selected_policy"] == "balanced"
    assert all(t["priority_factors"]["bounded_policy_bonus"] == 0
               for t in one[0])


def test_never_reorders_block_after_watch_despite_bonus():
    tasks = [task("BLOCK", 5, severity="block"),
             task("WATCH", 90, "regression_needs_review", severity="watch"),
             task("INFO", 90, "stalled_needs_review", severity="info")]
    result, meta = policy.autotune(tasks)
    assert [t["code"] for t in result] == ["BLOCK", "WATCH", "INFO"]
    assert meta["reorders_only_within_severity"] is True


@pytest.mark.parametrize("mutate", [
    lambda t: t.update(safe_autonomous_action="execute"),
    lambda t: t.update(new_optimizer_trials_authorized=True),
    lambda t: t.update(forecast_or_production_change_authorized=True),
    lambda t: t.update(priority="root"),
    lambda t: t.update(priority_score=999),
    lambda t: t.update(backlog_delta=0),
    lambda t: t.update(stagnation_cycles=-3),
])
def test_tampered_priority_tasks_fail_closed(mutate):
    t = task("WARNING", 55, "regression_needs_review")
    mutate(t)
    with pytest.raises(ValueError):
        policy.autotune([t])


def test_unconfirmed_human_review_is_not_executed():
    tasks = [task("NORMAL", 55),
             task("HUMAN", 52, "human_review_pending")]
    chosen, meta = policy.autotune(tasks)
    assert all(t["safe_autonomous_action"] == "report_only" for t in chosen)
    assert meta["external_actions_dispatched"] is False
    assert meta["research_budget_override_authorized"] is False
    assert len(chosen) == 2


def test_untrusted_duplicate_id_and_unbounded_queue_fail_closed():
    t = task("ONE", 50)
    with pytest.raises(ValueError, match="duplicate"):
        policy.autotune([t, copy.deepcopy(t)])
    with pytest.raises(ValueError, match="unbounded"):
        policy.autotune([task(f"T{i}", 50) for i in range(26)])
