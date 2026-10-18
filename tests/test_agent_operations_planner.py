"""The operations agent can recommend work, but never mutate protected evidence."""
import copy
from datetime import datetime, timezone

import pytest

from agent_operations_planner import VERSION, WORKFLOW_PLAYBOOKS, build_plan

T0 = datetime(2026, 10, 18, 12, 40, tzinfo=timezone.utc)


def snapshot():
    workflows = [
        {"file": p, "label": x, "health": "ok", "status": "completed",
         "conclusion": "success", "run_id": i + 100,
         "url": f"https://github.com/Joker7822/LOTO7_AI_AGENT/actions/runs/{i+100}"}
        for i, (p, x) in enumerate(WORKFLOW_PLAYBOOKS.items())
    ]
    return {
        "version": "loto7-ops-snapshot-v1", "source_commit": "a" * 40,
        "generated_at_jst": "2026-10-18T21:30:00+09:00",
        "sources": {
            "source": {"status": "ok", "verification": "verified_two_result_sources",
                       "latest": {"round": 699}},
            "council": {"overall": "watch", "handoff_tasks": [
                {"owner": "oos_risk_officer", "priority": "watch",
                 "issue_code": "NO_EARLY_PORTFOLIO_CLAIM", "evidence": "holdout=7/26"}]},
            "holdout": {"trusted_draws": 7, "horizon_trusted_draws": 26},
            "signal": {"trusted_draws": 0, "current_target_round": None},
            "learning": {"trusted_draws": 0, "current_prefrozen_target": None},
        },
        "series": {
            "portfolio": [{"round": i, "mean_delta_vs_random": -0.02} for i in range(693, 700)],
            "v2": [], "adaptive": [],
        },
        "workflows": workflows,
    }


def test_coordinator_splits_waiting_from_failure_and_keeps_evidence_untouched():
    payload = snapshot()
    original = copy.deepcopy(payload)
    plan = build_plan(payload, now=T0)
    assert payload == original
    assert plan["version"] == VERSION
    assert plan["overall"] == "watch"
    assert plan["counts"] == {"block": 0, "watch": 1, "info": 2}
    assert [x["priority"] for x in plan["tasks"]] == ["watch", "info", "info"]
    assert all(x["autonomous_mutation_allowed"] is False for x in plan["tasks"])
    assert not any(plan["authority"][key] for key in (
        "model_promotions", "forecast_overwrites", "retroactive_freezes",
        "workflow_retries", "production_publication",
    ))
    assert plan["source_commit"] == "a" * 40


def test_failed_research_run_becomes_top_priority_even_if_old_fix_landed():
    payload = snapshot()
    payload["workflows"][0].update(health="block", conclusion="failure", run_id=772)
    p = build_plan(payload, now=T0)
    assert p["overall"] == "block"
    assert p["tasks"][0]["code"] == "WORKFLOW_FAILED:continuous_loto7_v4.yml"
    assert "研究CI" in p["tasks"][0]["recommended_action"]
    assert p["tasks"][0]["url"].endswith("/100")
    assert "自動" not in p["tasks"][0]["recommended_action"]


def test_unknown_and_cancelled_actions_require_audit_not_success():
    payload = snapshot()
    payload["workflows"][2].update(health="unknown")
    payload["workflows"][3].update(health="warning")
    p = build_plan(payload, now=T0)
    assert p["counts"]["block"] == 0
    assert p["counts"]["watch"] == 3
    assert any(x["code"].startswith("WORKFLOW_UNVERIFIED") for x in p["tasks"])
    assert any(x["code"].startswith("WORKFLOW_WARNING") for x in p["tasks"])


def test_verified_700_requests_correct_initial_future_freezes():
    payload = snapshot()
    payload["sources"]["source"]["latest"]["round"] = 700
    p = build_plan(payload, now=T0)
    codes = {x["code"] for x in p["tasks"]}
    assert "FIRST_FREEZE_REQUIRED:signal" in codes
    assert "FIRST_FREEZE_REQUIRED:learning" in codes
    assert not any(x.startswith("MISSING_PREFREEZE") for x in codes)


def test_missed_prefreeze_fails_closed_not_backfilled():
    payload = snapshot()
    payload["sources"]["source"]["latest"]["round"] = 701
    p = build_plan(payload, now=T0)
    assert p["overall"] == "block"
    codes = {x["code"] for x in p["tasks"]}
    assert "MISSING_PREFREEZE:signal" in codes
    assert "MISSING_PREFREEZE:learning" in codes
    assert "事後復元" in next(x["recommended_action"] for x in p["tasks"]
                          if x["code"] == "MISSING_PREFREEZE:signal")


def test_untrusted_source_raises_blocker_without_scoring():
    payload = snapshot()
    payload["sources"]["source"]["verification"] = "single_source"
    p = build_plan(payload, now=T0)
    assert any(t["code"] == "UNTRUSTED_SOURCE" and t["priority"] == "block" for t in p["tasks"])


def test_prospective_drift_is_only_a_research_review_after_12_actual_results():
    payload = snapshot()
    payload["sources"]["learning"]["trusted_draws"] = 12
    payload["series"]["adaptive"] = [
        {"round": n, "mean_log_edge": -0.005} for n in range(701, 713)
    ]
    plan = build_plan(payload, now=T0)
    assert any(x["code"] == "ADAPTIVE_PROSPECTIVE_SCORE_BELOW_UNIFORM" for x in plan["tasks"])
    assert not plan["authority"]["model_promotions"]
    payload["sources"]["learning"]["trusted_draws"] = 11
    payload["series"]["adaptive"].pop()
    plan = build_plan(payload, now=T0)
    assert not any(x["code"] == "ADAPTIVE_PROSPECTIVE_SCORE_BELOW_UNIFORM" for x in plan["tasks"])


def test_missing_state_mismatch_does_not_make_reassuring_plan():
    payload = snapshot()
    payload["sources"]["holdout"]["trusted_draws"] = 8
    with pytest.raises(ValueError, match="portfolio future OOS state mismatch"):
        build_plan(payload, now=T0)
    payload = snapshot()
    payload["sources"]["council"]["overall"] = "not_available"
    with pytest.raises(ValueError, match="council state"):
        build_plan(payload, now=T0)


def test_untrusted_action_url_is_never_published():
    payload = snapshot()
    payload["workflows"][0].update(health="block", url="javascript:alert(1)")
    p = build_plan(payload, now=T0)
    assert p["tasks"][0]["url"] is None


def test_stable_incident_identity_across_repeated_runs():
    payload = snapshot()
    payload["workflows"][0]["health"] = "block"
    a = build_plan(payload, now=T0)
    b = build_plan(payload, now=T0)
    assert a == b
    assert len({t["id"] for t in a["tasks"]}) == len(a["tasks"])
