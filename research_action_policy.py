#!/usr/bin/env python3
"""Bounded, deterministic research-agent priority policy auto-tuning.

Compares three *hard-coded* advisory ranking strategies on the same audited
queue, using only measured backlog trend / reviewed-stagnation state. This is
not an LLM, unrestricted self-rewriter, prediction optimizer, or outcome trial.
No workflow, model, source data, or registered future record is touched.
"""
from __future__ import annotations

from copy import deepcopy

VERSION = "safe-agent-policy-autotune-v1"
SEVERITY = {"block": 0, "watch": 1, "info": 2}
ATTENTION_WEIGHTS = {
    "regression_needs_review": 12,
    "stalled_needs_review": 9,
    "human_review_pending": 4,
}
# Fixed allowable bonuses. Bound the largest adjustment to eight points,
# below the fixed source-integrity impact score separation in normal queues.
POLICIES = {
    "balanced": {},
    "regression_focus": {
        "regression_needs_review": 8,
        "stalled_needs_review": 2,
        "human_review_pending": 1,
    },
    "stagnation_focus": {
        "regression_needs_review": 5,
        "stalled_needs_review": 8,
        "human_review_pending": 2,
    },
}


def _validate(tasks: list[dict]) -> None:
    if not isinstance(tasks, list) or len(tasks) > 25:
        raise ValueError("unbounded agent action queue")
    seen = set()
    permitted = set(ATTENTION_WEIGHTS) | {"observed_progress", "routine_monitoring"}
    for t in tasks:
        if not isinstance(t, dict) or not isinstance(t.get("id"), str):
            raise ValueError("malformed research task")
        if t["id"] in seen:
            raise ValueError("duplicate action identifier")
        seen.add(t["id"])
        factors = t.get("priority_factors")
        if (t.get("priority") not in SEVERITY
                or t.get("attention_state") not in permitted
                or t.get("safe_autonomous_action") != "report_only"
                or t.get("new_optimizer_trials_authorized") is not False
                or t.get("forecast_or_production_change_authorized") is not False
                or not isinstance(factors, dict)
                or not factors
                or any(type(n) is not int or not -5 <= n <= 100
                       for n in factors.values())
                or type(t.get("priority_score")) is not int
                or t["priority_score"] != sum(factors.values())):
            raise ValueError("unsafe or unverified action cannot enter auto-tuning")
        attention = t["attention_state"]
        delta, count = t.get("backlog_delta"), t.get("backlog_observed")
        stalled = t.get("stagnation_cycles")
        recurring = t.get("recurrence_cycles")
        if (attention == "regression_needs_review"
                and (type(delta) is not int or delta <= 0)):
            raise ValueError("regression not supported by measured backlog")
        if (attention == "stalled_needs_review"
                and (t.get("feedback_state") != "unchanged"
                     or type(stalled) is not int or stalled < 3)):
            raise ValueError("stagnation not supported by observations")
        if (attention == "human_review_pending"
                and (t.get("feedback_state") != "still_pending_unmeasured"
                     or type(recurring) is not int or recurring < 4)):
            raise ValueError("human review not supported by recurrence")
        if (attention == "observed_progress"
                and (type(delta) is not int or delta >= 0)):
            raise ValueError("improvement not supported by measured backlog")
        if count is not None and (type(count) is not int or count < 0):
            raise ValueError("invalid observed backlog")


def _rank(tasks: list[dict], name: str) -> list[dict]:
    bonuses = POLICIES[name]
    ranking = deepcopy(tasks)
    for task in ranking:
        bonus = bonuses.get(task["attention_state"], 0)
        task["priority_factors"]["bounded_policy_bonus"] = bonus
        task["priority_score"] += bonus
    ranking.sort(key=lambda task: (
        SEVERITY[task["priority"]], -task["priority_score"], task["code"]
    ))
    return ranking


def _objective(ranking: list[dict], baseline_positions: dict[str, int]) -> int:
    # Reward earlier attention to objectively unresolved operational hazards.
    # Penalize gratuitous reordering. Severity is partitioned by construction.
    score = 0
    for group in SEVERITY:
        cohort = [t for t in ranking if t["priority"] == group]
        length = len(cohort)
        for position, task in enumerate(cohort):
            attention = task["attention_state"]
            if attention in ATTENTION_WEIGHTS:
                score += ATTENTION_WEIGHTS[attention] * (length - position)
            score -= abs(position - baseline_positions[task["id"]])
    return score


def autotune(tasks: list[dict]) -> tuple[list[dict], dict]:
    """Choose a fixed allowlisted ranking only on strictly better *proxy* score.

    A proxy score is not empirical evidence of a causal productivity increase.
    In particular, it is not a lottery forecast skill measurement.
    """
    _validate(tasks)
    ranked = {name: _rank(tasks, name) for name in POLICIES}
    baseline = ranked["balanced"]
    positions = {
        task["id"]: i
        for severity in SEVERITY
        for i, task in enumerate(t for t in baseline
                                 if t["priority"] == severity)
    }
    objectives = {name: _objective(ranking, positions)
                  for name, ranking in ranked.items()}
    selected = "balanced"
    for name in POLICIES:
        if objectives[name] > objectives[selected]:
            selected = name
    chosen = ranked[selected]
    # Runtime assertion prevents any accidental severity or authority escape.
    before = sorted((t["id"], t["priority"]) for t in tasks)
    after = sorted((t["id"], t["priority"]) for t in chosen)
    if before != after or any(
        t["safe_autonomous_action"] != "report_only"
        or t["new_optimizer_trials_authorized"] is not False
        or t["forecast_or_production_change_authorized"] is not False
        or t["priority_factors"]["bounded_policy_bonus"] > 8
        for t in chosen
    ):
        raise ValueError("auto-tuned plan violated fixed authority constraints")
    return chosen, {
        "version": VERSION,
        "selected_policy": selected,
        "candidate_objectives": objectives,
        "objective": "bounded_advisory_attention_rank_minus_reordering_penalty",
        "priority_bonus_cap": 8,
        "reorders_only_within_severity": True,
        "evaluation_is_operational_proxy_only": True,
        "empirical_agent_productivity_improvement_established": False,
        "lottery_prediction_improvement_established": False,
        "automatic_code_or_model_change_authorized": False,
        "research_budget_override_authorized": False,
        "external_actions_dispatched": False,
    }
