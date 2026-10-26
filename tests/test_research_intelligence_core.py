"""E2E tests for evidence-grounded, dependency-aware intelligence core."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

import research_intelligence_core as intelligence
import research_specialist_agents as specialists
import online_research_intelligence as internet

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def evidence():
    agents = {name: specialists.execute(ROOT, name) for name in specialists.AGENTS}
    data = internet.run(ROOT)
    fps = {name: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
           for name, path in intelligence.SOURCE_FILES.items()}
    return agents, data, fps


def combine(evidence):
    agents, data, fps = evidence
    champion = json.loads((ROOT / intelligence.SOURCE_FILES["production_champion"]).read_text())
    return intelligence.evidence_engine(
        copy.deepcopy(agents), copy.deepcopy(data), fingerprints=copy.deepcopy(fps),
        champion_version=champion["model_version"],
    )


def test_four_specialists_are_integrated_with_sha_verified_online_intelligence(evidence):
    r = combine(evidence)
    assert r["version"] == intelligence.VERSION
    assert len(r["specialist_statuses"]) == len(specialists.AGENTS) == 4
    assert len(r["evidence_graph"]["nodes"]) >= 9
    assert len(r["evidence_graph"]["edges"]) >= 6
    assert all(n["sha256"] == evidence[2][next(
        name for name, path in intelligence.SOURCE_FILES.items()
        if path == n["reference"]
    )] for n in r["evidence_graph"]["nodes"])
    assert r["evidence_graph_sha256"] == intelligence._sha(r["evidence_graph"])
    assert r["work_plan_sha256"] == intelligence._sha(r["work_plan"])
    assert len(r["top_actions"]) == min(3, len(r["work_plan"]))
    assert not any(r["blocked_automated_actions"].values())
    assert r["champion_version"].startswith("baseline-")


def test_risk_aware_dependencies_and_action_provenance(evidence):
    r = combine(evidence)
    actions = {t["task_id"]: t for t in r["work_plan"]}
    ids = {n["id"] for n in r["evidence_graph"]["nodes"]}
    assert "AUDIT_HISTORICAL_SIGNAL" in actions
    assert "CONTINUE_PRE_REGISTERED_OOS" in actions
    for t in actions.values():
        assert set(t["evidence_node_ids"]) <= ids
        assert t["permission"] == "recommendation_only_no_side_effects"
        assert t["new_experiment_authorized"] is False
        assert t["production_release_authorized"] is False
        assert t["priority"] == intelligence.CATALOG[t["task_id"]][2]
        assert all(d in intelligence.CATALOG for d in t["required_prior_tasks"])
    if not r["latest_draw_trusted"]:
        assert actions["CONTINUE_PRE_REGISTERED_OOS"]["status"] == "await_verified_draw"
        assert "VERIFY_TRUSTED_DRAW" in actions


def test_bibliography_must_be_reviewed_before_safe_handoff(evidence):
    r = combine(evidence)
    actions = {t["task_id"]: t for t in r["work_plan"]}
    if "VERIFY_BIBLIOGRAPHY" in actions:
        assert actions["REVIEW_EXTERNAL_METHODS"]["status"] == (
            "blocked_until_bibliography_verification"
        )
        assert "VERIFY_BIBLIOGRAPHY" in actions["REVIEW_EXTERNAL_METHODS"]["required_prior_tasks"]


def test_historical_staleness_looks_like_work_not_predictive_skill(evidence):
    r = combine(evidence)
    assert r["predictive_skill_proven"] is False
    assert r["independent_evidence_tiers"]["historical_model_skill"] == "exploratory_not_confirmed"
    assert r["independent_evidence_tiers"]["online_papers"] == "bibliography_not_full_text_validation"
    assert r["no_model_training_started"] and r["no_live_forecast_issued"]
    assert r["no_production_writes"] and r["no_registered_evidence_writes"]
    if not evidence[1]["quality_checks"]["literature_synced_to_current_draw"]:
        assert "REFRESH_RESEARCH_SNAPSHOT" in r["top_actions"] or any(
            t["task_id"] == "REFRESH_RESEARCH_SNAPSHOT" for t in r["work_plan"]
        )


def test_report_is_exactly_deterministic(evidence):
    a, b = combine(evidence), combine(evidence)
    assert a == b
    assert intelligence.markdown(a) == intelligence.markdown(b)
    assert "advisory only" in intelligence.markdown(a).lower()


@pytest.mark.parametrize("agent", specialists.AGENTS)
def test_forged_permission_or_specialist_identity_is_rejected(evidence, agent):
    agents, online, fingerprints = evidence
    bad = copy.deepcopy(agents)
    bad[agent]["permissions"]["new_optimizer_trials"] = True
    with pytest.raises(ValueError, match="incompatible"):
        intelligence.evidence_engine(
            bad, copy.deepcopy(online), fingerprints=copy.deepcopy(fingerprints),
            champion_version="baseline-5fdb8dc2ad",
        )


def test_multi_agent_agreement_cannot_override_unverified_draw(evidence):
    agents, paper, fps = evidence
    good = copy.deepcopy(agents)
    unverified = copy.deepcopy(paper)
    for agent in good.values():
        agent["status"] = "pass"
        agent["checks"] = [{**check, "status": "pass"} for check in agent["checks"]]
    good["source_sentinel"]["context"]["trusted_round"] = None
    good["source_sentinel"]["checks"][0]["status"] = "block"
    good["source_sentinel"]["status"] = "block"
    unverified["source"]["independent_two_source_verified"] = False
    unverified["quality_checks"]["current_draw_verified"] = False
    report = intelligence.evidence_engine(
        good, unverified, fingerprints=fps,
        champion_version="baseline-5fdb8dc2ad",
    )
    assert not report["latest_draw_trusted"]
    assert "VERIFY_TRUSTED_DRAW" in report["top_actions"]
    assert {a["task_id"]: a for a in report["work_plan"]}[
        "CONTINUE_PRE_REGISTERED_OOS"]["status"] == "await_verified_draw"


def test_known_but_unverified_round_is_not_trusted_by_majority(evidence):
    agents, online, fps = evidence
    reports = copy.deepcopy(agents)
    web = copy.deepcopy(online)
    source = reports["source_sentinel"]
    source["context"]["trusted_round"] = web["source"]["round"]
    source["checks"][0]["status"] = "block"
    source["status"] = "block"
    web["source"]["independent_two_source_verified"] = False
    web["quality_checks"]["current_draw_verified"] = False
    result = intelligence.evidence_engine(
        reports, web, fingerprints=fps,
        champion_version="baseline-5fdb8dc2ad",
    )
    assert not result["latest_draw_trusted"]
    assert result["independent_evidence_tiers"]["latest_result"] == "unverified"
    assert result["work_plan"][0]["task_id"] == "VERIFY_TRUSTED_DRAW"
    assert {task["task_id"]: task for task in result["work_plan"]}[
        "CONTINUE_PRE_REGISTERED_OOS"]["status"] == "await_verified_draw"


def test_forged_trust_disagreement_is_rejected(evidence):
    agents, online, fingerprints = evidence
    new = copy.deepcopy(online)
    new["source"]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="source SHA"):
        intelligence.evidence_engine(
            copy.deepcopy(agents), new, fingerprints=fingerprints,
            champion_version="baseline-5fdb8dc2ad",
        )


def test_unregistered_agent_and_changed_evidence_tier_are_not_accepted(evidence):
    agents, online, fingerprints = evidence
    extra = copy.deepcopy(agents)
    extra["auto_promotion_agent"] = extra["source_sentinel"]
    with pytest.raises(ValueError, match="incomplete"):
        intelligence.evidence_engine(extra, online, fingerprints=fingerprints,
                                     champion_version="baseline-5fdb8dc2ad")
    forged = copy.deepcopy(online)
    forged["auto_promotion_authorized"] = True
    with pytest.raises(ValueError, match="safety guarantees"):
        intelligence.evidence_engine(agents, forged, fingerprints=fingerprints,
                                     champion_version="baseline-5fdb8dc2ad")


def test_unknown_champion_rejected_even_if_other_specialists_support_it(evidence):
    agents, online, fps = evidence
    with pytest.raises(ValueError, match="Champion"):
        intelligence.evidence_engine(
            agents, online, fingerprints=fps, champion_version="unreviewed-high-accuracy")


def test_duplicate_check_ids_or_inconsistent_status_fails_closed(evidence):
    agents, online, fps = evidence
    bad = copy.deepcopy(agents)
    bad["literature_examiner"]["checks"][1]["code"] = bad["literature_examiner"]["checks"][0]["code"]
    with pytest.raises(ValueError, match="invalid specialist grading"):
        intelligence.evidence_engine(bad, online, fingerprints=fps,
                                     champion_version="baseline-5fdb8dc2ad")
    bad = copy.deepcopy(agents)
    bad["source_sentinel"]["status"] = ("pass" if bad["source_sentinel"]["status"] != "pass"
                                         else "block")
    with pytest.raises(ValueError, match="finding/status conflict"):
        intelligence.evidence_engine(bad, online, fingerprints=fps,
                                     champion_version="baseline-5fdb8dc2ad")


def test_dependency_order_is_consistent_and_cycles_are_blocked():
    t = intelligence._task("REVIEW_EXTERNAL_METHODS", ["scholarly_metadata"])
    prior = intelligence._task("VERIFY_BIBLIOGRAPHY", ["scholarly_metadata"])
    order = intelligence._order_tasks({t["task_id"]: t, prior["task_id"]: prior})
    assert [x["task_id"] for x in order] == [
        "VERIFY_BIBLIOGRAPHY", "REVIEW_EXTERNAL_METHODS"
    ]
    x = intelligence._task("VERIFY_BIBLIOGRAPHY", ["scholarly_metadata"])
    x["required_prior_tasks"] = ["REVIEW_EXTERNAL_METHODS"]
    with pytest.raises(ValueError, match="cycle"):
        intelligence._order_tasks({t["task_id"]: t, x["task_id"]: x})


def test_no_protected_file_mutated_after_full_engine(tmp_path, monkeypatch):
    before = {k: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
              for k, path in intelligence.SOURCE_FILES.items()}
    monkeypatch.chdir(tmp_path)
    r = intelligence.run(ROOT)
    assert r["latest_known_draw"] >= 699
    assert list(tmp_path.iterdir()) == []
    after = {k: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
             for k, path in intelligence.SOURCE_FILES.items()}
    assert after == before


def test_concurrent_input_change_blocks_incoherent_evidence(monkeypatch):
    original = intelligence.specialists.execute
    state = {"count": 0}
    def mutate_virtual(root, name):
        state["count"] += 1
        return original(root, name)
    monkeypatch.setattr(intelligence.specialists, "execute", mutate_virtual)
    original_hash = intelligence._sha_file
    def changed(path):
        if path.name == "loto7.csv" and state["count"] > 0:
            return "0" * 64
        return original_hash(path)
    monkeypatch.setattr(intelligence, "_sha_file", changed)
    with pytest.raises(RuntimeError, match="concurrent evidence modification"):
        intelligence.run(ROOT)
