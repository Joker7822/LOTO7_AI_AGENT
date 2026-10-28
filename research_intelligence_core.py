#!/usr/bin/env python3
"""Evidence-grounded research decision intelligence for LOTO7.

Deterministic, explainable decision support atop four independent specialists,
Crossref/OpenAlex SHA-verified metadata intelligence, and precommitted future
tests. It is NOT an LLM, lottery predictive breakthrough, autonomous retrainer,
code executor, or Production release authority.

Hard trust boundaries are NOT overridden by multi-agent voting. No outside
paper instructions enter the planner. All outputs are advisory-only artifacts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import online_research_intelligence as internet
import research_specialist_agents as specialists

VERSION = "evidence-grounded-intelligence-core-v1"
OUTPUT = Path("research_output/intelligence_core")
SOURCE_FILES = {
    "draw": "loto7.csv",
    "source_attestation": "loto7_agent_output/source_validation.json",
    "research_guard": "loto7_agent_output/research_cycle_guard.json",
    "literature_review": "loto7_agent_output/research_literature_reviews.json",
    "cross_provider_checks": "loto7_agent_output/research_verified_publications.json",
    "proposal_gate": "loto7_agent_output/research_application_readiness.json",
    "historical_baseline": "loto7_agent_output/historical_replay_summary.json",
    "future_holdout": "loto7_agent_output/future_holdout_state.json",
    "joint_v2": "loto7_agent_output/joint_set_v2_signal_oos_state.json",
    "prospective_registration": "research/disjoint_future_oos/registration.json",
    "initial_future_freeze": "research/disjoint_future_oos/freeze_0701.json",
    "production_champion": "loto7_agent_output/model_champion.json",
}
RISK = {"critical": 100, "high": 75, "medium": 45, "low": 15}
# Fixed, locally authored actions: external paper text can never be instructions.
CATALOG = {
    "VERIFY_TRUSTED_DRAW": (
        "source_sentinel", "critical", 100,
        "Obtain two independently consistent draw results and matching CSV SHA",
        (), "operator_source_verification",
    ),
    "REPAIR_EVIDENCE_INTEGRITY": (
        "source_sentinel", "critical", 95,
        "Resolve conflicting source SHA or specialist evidence before decisions",
        (), "operator_evidence_review",
    ),
    "RESPECT_SEARCH_BUDGET": (
        "literature_examiner", "high", 85,
        "Keep existing WAIT_FOR_NEW_DATA/trial limits; do not restart optimizer",
        (), "observe_trial_budget",
    ),
    "REFRESH_RESEARCH_SNAPSHOT": (
        "literature_examiner", "high", 75,
        "Refresh metadata and application-readiness only with existing authorized pipeline",
        (), "operator_review_source_snapshots",
    ),
    "REFRESH_SCIENCE_DIAGNOSTIC": (
        "calibration_analyst", "medium", 55,
        "Recompute historical scientific summary using existing authorized code and current SHA",
        (), "operator_review_statistics",
    ),
    "VERIFY_BIBLIOGRAPHY": (
        "literature_examiner", "medium", 60,
        "Resolve DOI/metadata conflicts using permitted Crossref and OpenAlex checks",
        (), "operator_verify_doi",
    ),
    "REVIEW_EXTERNAL_METHODS": (
        "literature_examiner", "medium", 45,
        "Review complete methods, provenance, licensing and fair-lottery relevance",
        ("VERIFY_BIBLIOGRAPHY",), "human_methodology_review",
    ),
    "CONTINUE_PRE_REGISTERED_OOS": (
        "prospective_custodian", "high", 70,
        "Continue existing 26-draw streams only after trusted prefrozen results",
        ("VERIFY_TRUSTED_DRAW",), "wait_for_future_trusted_draws",
    ),
    "AUDIT_HISTORICAL_SIGNAL": (
        "calibration_analyst", "low", 20,
        "Compare exploratory Top7 performance against 49/37 without promotion",
        (), "review_historical_calibration_only",
    ),
}
NO_AUTHORITY = {
    "prediction_or_ticket_issuance": False,
    "new_optimizer_trials": False,
    "automatic_champion_promotion": False,
    "code_or_shell_execution_from_papers": False,
    "retroactive_future_oos_scoring": False,
    "rewrite_preregistered_freezes": False,
    "budget_override": False,
}


def _sha(data: object) -> str:
    return hashlib.sha256(json.dumps(
        data, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
        allow_nan=False
    ).encode("utf-8")).hexdigest()


def _sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _task(code: str, evidence: list[str]) -> dict:
    owner, risk, priority, instruction, dependencies, class_name = CATALOG[code]
    return {
        "task_id": code,
        "owner": owner,
        "severity": risk,
        "priority": priority,
        "reason": instruction,
        "required_prior_tasks": list(dependencies),
        "next_step_class": class_name,
        "evidence_node_ids": sorted(set(evidence)),
        "permission": "recommendation_only_no_side_effects",
        "new_experiment_authorized": False,
        "production_release_authorized": False,
    }


def _order_tasks(tasks: dict[str, dict]) -> list[dict]:
    """Explainable dependency-aware scheduling; cycle/unavailable deps fail."""
    # An unsatisfied prior task is a non-executable prerequisite. It is still
    # listed as a prerequisite even if the task wasn't created: never quietly
    # mark it completed. Dependency cycles fail closed.
    seen: dict[str, int] = {}
    result = []

    def visit(code: str) -> None:
        if seen.get(code) == 2:
            return
        if seen.get(code) == 1:
            raise ValueError("cycle in research work plan")
        if code not in tasks:
            return
        seen[code] = 1
        for dep in tasks[code]["required_prior_tasks"]:
            if dep not in CATALOG:
                raise ValueError("unknown safety precondition")
            visit(dep)
        seen[code] = 2
        result.append(tasks[code])

    for code in sorted(tasks, key=lambda k: (-tasks[k]["priority"], k)):
        visit(code)
    if len(result) != len(tasks):
        raise ValueError("unresolved task graph")
    return result


def evidence_engine(
    specialist_reports: dict[str, dict],
    scholarly: dict,
    *,
    fingerprints: dict[str, str],
    champion_version: str,
) -> dict:
    """Combine authenticated, separately originated evidence into safe actions.

    Trust is a hard AND condition, never a vote or mean confidence score.
    Labels indicate SOURCE QUALITY, not probabilities of winning a lottery.
    """
    if set(specialist_reports) != set(specialists.AGENTS):
        raise ValueError("specialist evidence set incomplete")
    if (scholarly.get("version") != internet.VERSION
            or not scholarly.get("quality_checks", {}).get("audit_chain_verified")
            or not scholarly.get("quality_checks", {}).get("metadata_lineage_verified")
            or not scholarly.get("quality_checks", {}).get("bibliography_statuses_reconciled")
            or scholarly.get("new_real_experiments") != 0
            or scholarly.get("new_predictions_generated") != 0
            or scholarly.get("auto_promotion_authorized") is not False
            or scholarly.get("production_or_champion_changed") is not False):
        raise ValueError("scholarly analysis lacks required safety guarantees")
    if (not isinstance(champion_version, str)
            or not champion_version.startswith("baseline-")):
        raise ValueError("unexpected Champion requires human review")
    for name, report in specialist_reports.items():
        if (report.get("version") != specialists.VERSION
                or report.get("agent") != name
                or report.get("decision") != "advisory_only_no_model_release"
                or report.get("permissions") != specialists.AUTHORIZED
                or report.get("production_changed") is not False
                or report.get("existing_oos_changed") is not False
                or report.get("new_real_experiments_executed") != 0
                or report.get("inputs_are_read_only") is not True
                or report.get("model_prediction_skill_claimed") is not False):
            raise ValueError("specialist attempts incompatible evidence/authority")
        checks = report.get("checks")
        if not isinstance(checks, list) or not 1 <= len(checks) <= 12:
            raise ValueError("invalid specialist checks")
        if (len(set(c["code"] for c in checks)) != len(checks)
                or any(c.get("status") not in ("pass", "watch", "block")
                       for c in checks)):
            raise ValueError("invalid specialist grading")
        expected_status = ("block" if any(c["status"] == "block" for c in checks)
                           else "watch" if any(c["status"] == "watch" for c in checks)
                           else "pass")
        if report.get("status") != expected_status:
            raise ValueError("specialist finding/status conflict")

    source = specialist_reports["source_sentinel"]
    source_ctx = source["context"]
    scholar_src = scholarly["source"]
    if source_ctx.get("draw_sha256") != scholar_src.get("sha256"):
        raise ValueError("specialists disagree about source SHA/verified round")
    source_checks = {c["code"]: c for c in source["checks"]}
    if not {"two_source_trust", "source_sha256"} <= source_checks.keys():
        raise ValueError("missing non-negotiable trust prerequisites")
    is_verified = scholar_src.get("independent_two_source_verified") is True
    # The pinned historical 699 fixture has a KNOWN round but not a
    # VERIFIED result. The source guard may return the known round even
    # when trusted=False. Never infer trust from round equality alone.
    declared_round = source_ctx.get("trusted_round")
    if is_verified:
        if declared_round != scholar_src.get("round") or (
                source_checks["two_source_trust"]["status"] != "pass"):
            raise ValueError("specialists disagree about source SHA/verified round")
    else:
        if (source_checks["two_source_trust"]["status"] == "pass"
                or declared_round not in (None, scholar_src.get("round"))):
            raise ValueError("unverified draw cannot masquerade as verified")
    source_trusted = (
        is_verified
        and source_checks["two_source_trust"]["status"] == "pass"
        and source_checks["source_sha256"]["status"] == "pass"
    )
    if source_trusted and (
        fingerprints["draw"] != scholar_src["sha256"]
        or not scholarly["quality_checks"]["current_draw_verified"]
    ):
        raise ValueError("trusted draw disagrees with its exact byte fingerprint")

    calibration = specialist_reports["calibration_analyst"]
    oos = specialist_reports["prospective_custodian"]
    literature = specialist_reports["literature_examiner"]
    obs = oos["context"].get("trusted_draws_by_stream")
    if (not isinstance(obs, dict)
            or set(obs) != {"existing_holdout", "joint_v2_signal", "disjoint35_geometry"}
            or any(type(x) is not int or x < 0 or x > 26 for x in obs.values())
            or oos["context"].get("fixed_horizon") != 26):
        raise ValueError("invalid fixed prospective sample ledger")
    if (literature["context"]["candidate_dois"] !=
            scholarly["research_snapshot"]["paper_count"]):
        raise ValueError("bibliographic candidate count disagreement")
    if (literature["context"]["draft_proposals"] !=
            scholarly["research_snapshot"]["proposal_count"]):
        raise ValueError("proposal count disagreement")

    nodes = [
        {"id": "draw", "kind": "verified_lottery_observation" if source_trusted
         else "untrusted_lottery_observation",
         "reference": SOURCE_FILES["draw"], "sha256": fingerprints["draw"],
         "round": scholar_src["round"], "evidence_tier":
             "two_independent_results" if source_trusted else "not_verified"},
        {"id": "source_attestation", "kind": "attestation",
         "reference": SOURCE_FILES["source_attestation"],
         "sha256": fingerprints["source_attestation"],
         "evidence_tier": "corroborated" if source_trusted else "untrusted"},
        {"id": "research_guard", "kind": "budget_authority",
         "reference": SOURCE_FILES["research_guard"],
         "sha256": fingerprints["research_guard"],
         "evidence_tier": "checked_local_config"},
        {"id": "historical_backtest", "kind": "exploratory_historical_evidence",
         "reference": SOURCE_FILES["historical_baseline"],
         "sha256": fingerprints["historical_baseline"],
         "evidence_tier": "retrospective_not_independent"},
        {"id": "scholarly_metadata", "kind": "curated_bibliographic_candidates",
         "reference": SOURCE_FILES["cross_provider_checks"],
         "sha256": fingerprints["cross_provider_checks"],
         "evidence_tier": "identity_metadata_not_method_or_accuracy"},
        {"id": "formal_holdout", "kind": "registered_future_observations",
         "reference": SOURCE_FILES["future_holdout"],
         "sha256": fingerprints["future_holdout"], "trusted": obs["existing_holdout"],
         "evidence_tier": "preregistered_incomplete" if obs["existing_holdout"] < 26
                          else "preregistered_horizon_reached_review_required"},
        {"id": "joint_signal", "kind": "registered_future_observations",
         "reference": SOURCE_FILES["joint_v2"],
         "sha256": fingerprints["joint_v2"], "trusted": obs["joint_v2_signal"],
         "evidence_tier": "preregistered_incomplete" if obs["joint_v2_signal"] < 26
                          else "preregistered_horizon_reached_review_required"},
        {"id": "disjoint_geometry", "kind": "prospective_geometry_evidence",
         "reference": SOURCE_FILES["prospective_registration"],
         "sha256": fingerprints["prospective_registration"],
         "trusted": obs["disjoint35_geometry"],
         "evidence_tier": "coverage_geometry_not_prediction_signal"},
        {"id": "champion", "kind": "unchanged_production_identity",
         "reference": SOURCE_FILES["production_champion"],
         "sha256": fingerprints["production_champion"],
         "evidence_tier": "frozen_model_identity_not_newly_promoted"},
    ]
    edges = [
        {"from": "source_attestation", "to": "draw", "type": "must_corroborate"},
        {"from": "draw", "to": "formal_holdout", "type": "required_for_trusted_scoring"},
        {"from": "draw", "to": "joint_signal", "type": "required_for_trusted_scoring"},
        {"from": "draw", "to": "disjoint_geometry", "type": "required_for_trusted_scoring"},
        {"from": "research_guard", "to": "historical_backtest",
         "type": "limits_new_optimizer_search"},
        {"from": "scholarly_metadata", "to": "champion",
         "type": "cannot_authorize_automatic_promotion"},
        {"from": "historical_backtest", "to": "champion",
         "type": "cannot_authorize_automatic_promotion"},
    ]
    tasks: dict[str, dict] = {}

    def suggest(code: str, why: list[str]) -> None:
        if code not in tasks:
            tasks[code] = _task(code, why)
        else:
            tasks[code]["evidence_node_ids"] = sorted(set(
                tasks[code]["evidence_node_ids"] + why
            ))

    if not source_trusted:
        suggest("VERIFY_TRUSTED_DRAW", ["draw", "source_attestation"])
    if source_checks["source_sha256"]["status"] != "pass":
        suggest("REPAIR_EVIDENCE_INTEGRITY", ["draw", "source_attestation"])
    if scholar_src["sha256"] != source_ctx["draw_sha256"]:
        raise ValueError("cross-agent checksum conflict")
    if not scholarly["quality_checks"]["research_guard_matches_current_draw"]:
        suggest("REPAIR_EVIDENCE_INTEGRITY", ["research_guard", "draw"])
    if scholarly["quality_checks"]["research_budget_mode"] == "WAIT_FOR_NEW_DATA":
        suggest("RESPECT_SEARCH_BUDGET", ["research_guard"])

    if not scholarly["quality_checks"]["literature_synced_to_current_draw"]:
        suggest("REFRESH_RESEARCH_SNAPSHOT", ["draw", "scholarly_metadata"])
    calcheck = {c["code"]: c["status"] for c in calibration["checks"]}
    if (calcheck.get("scientific_null_freshness") != "pass"
            or calcheck.get("historical_replay_freshness") != "pass"):
        suggest("REFRESH_SCIENCE_DIAGNOSTIC", ["draw", "historical_backtest"])

    pending = sum(
        t["pending_or_conflicting"] for t in scholarly["topic_analytics"]
    )
    if pending:
        suggest("VERIFY_BIBLIOGRAPHY", ["scholarly_metadata"])
    if scholarly["research_snapshot"]["proposal_count"]:
        suggest("REVIEW_EXTERNAL_METHODS", ["scholarly_metadata"])
    if min(obs.values()) < 26:
        suggest("CONTINUE_PRE_REGISTERED_OOS",
                ["draw", "formal_holdout", "joint_signal", "disjoint_geometry"])
    suggest("AUDIT_HISTORICAL_SIGNAL", ["historical_backtest"])

    # Non-executable dependency: if result source is untrusted, the OOS task
    # is held, even if other agents regard the tests as promising.
    if "CONTINUE_PRE_REGISTERED_OOS" in tasks and not source_trusted:
        tasks["CONTINUE_PRE_REGISTERED_OOS"]["status"] = "await_verified_draw"
    for task in tasks.values():
        task.setdefault("status", "advisory")
        if task["task_id"] == "REVIEW_EXTERNAL_METHODS" and pending:
            task["status"] = "blocked_until_bibliography_verification"
    ordered = _order_tasks(tasks)
    assert all(set(task["evidence_node_ids"]) <=
               {node["id"] for node in nodes} for task in ordered)
    graph = {"nodes": nodes, "edges": edges}
    return {
        "version": VERSION,
        "purpose": "bounded_evidence_grounded_research_decision_support",
        "latest_known_draw": scholar_src["round"],
        "latest_draw_trusted": source_trusted,
        "source_of_truth_sha256": fingerprints["draw"],
        "champion_version": champion_version,
        "specialist_statuses": {
            name: specialist_reports[name]["status"] for name in specialists.AGENTS
        },
        "independent_evidence_tiers": {
            "latest_result": "two_source_verified" if source_trusted else "unverified",
            "historical_model_skill": "exploratory_not_confirmed",
            "online_papers": "bibliography_not_full_text_validation",
            "future_oos": "incomplete" if min(obs.values()) < 26
                          else "ready_for_human_protocol_review",
            "geometry": "exact_fair_world_coverage_not_signal",
        },
        "evidence_graph": graph,
        "evidence_graph_sha256": _sha(graph),
        "work_plan": ordered,
        "work_plan_sha256": _sha(ordered),
        "top_actions": [t["task_id"] for t in ordered[:3]],
        "blocked_automated_actions": dict(NO_AUTHORITY),
        "next_workflow": "review_recommendations_only",
        "no_model_training_started": True,
        "no_live_forecast_issued": True,
        "no_production_writes": True,
        "no_registered_evidence_writes": True,
        "predictive_skill_proven": False,
        "explainability": (
            "Hard provenance and future-freeze gates are not subject to voting; "
            "task ordering follows fixed risk priorities and dependencies. "
            "Historical metrics and DOI metadata cannot grant model authority."
        ),
    }


def recent_online_research_projection(root: Path) -> dict:
    """Make *verified public metadata* usable by the established decision core."""
    from frequent_online_research_feed import FILE, VERSION, TWO_SOURCE
    import always_on_accuracy_agent as discovery
    from research_literature_pipeline import paper_topics
    from online_research_intelligence import SAFE_METHODS
    p = root / "loto7_agent_output" / FILE
    if not p.exists():
        return {"status": "not_yet_published", "model_change_authorized": False}
    record = json.loads(p.read_text(encoding="utf-8"))
    if (not isinstance(record, dict) or record.get("version") != VERSION
            or record.get("automatic_paper_method_execution") is not False
            or record.get("champion_or_production_modified") is not False
            or record.get("future_oos_modified") is not False
            or record.get("claim_of_lottery_predictive_improvement") is not False
            or record.get("new_optimizer_trials") != 0):
        raise ValueError("unsafe external discovery sidecar")
    state = root / "loto7_agent_output" / "always_on_accuracy_research_state.json"
    journal = root / "loto7_agent_output" / "always_on_accuracy_research_journal.jsonl"
    chain = discovery.read_chain(journal)
    if (record.get("discovery_state_sha256") != _sha_file(state)
            or not chain
            or record.get("discovery_chain_tip") != chain[-1]["record_sha256"]):
        return {"status": "stale_discovery_snapshot",
                "model_change_authorized": False}
    entries = record.get("candidates")
    if not isinstance(entries, list) or len(entries) > 48:
        raise ValueError("invalid bounded external DOI candidates")
    matched = []
    for paper in entries:
        if (not isinstance(paper, dict)
                or paper.get("status") != TWO_SOURCE):
            continue
        if (paper.get("crossref_consistent") is not True
                or paper.get("openalex_consistent") is not True
                or any(paper.get(flag) is not False for flag in (
                    "full_text_reviewed", "peer_review_confirmed",
                    "methods_reproduced_from_paper", "lottery_prediction_improved"
                ))):
            raise ValueError("untrusted source claims verified external method")
        matched.append(paper)
    themes = sorted({
        topic for p in matched
        for topic in paper_topics(p["title"])
        if topic in SAFE_METHODS
    })
    return {
        "status": "fresh_metadata_review_candidates" if themes else "no_new_dual_source_leads",
        "feed_sha256": _sha_file(p),
        "last_online_search_utc": record.get("checked_at_utc"),
        "new_candidate_count": record.get("candidate_count", 0),
        "two_source_matches_from_last_cycle": len(matched),
        "priority_topics_for_human_review": themes,
        "locally_fixed_handoffs": [SAFE_METHODS[t][0] for t in themes],
        "model_change_authorized": False,
        "source_identity_only_not_methodology_validated": True,
    }


def run(root: Path) -> dict:
    root = root.resolve()
    # Snapshot BEFORE any analysis, then reject a concurrent source change.
    fingerprints = {name: _sha_file(root / path)
                    for name, path in SOURCE_FILES.items()}
    reports = {name: specialists.execute(root, name) for name in specialists.AGENTS}
    scholarly = internet.run(root)
    champion = json.loads(
        (root / SOURCE_FILES["production_champion"]).read_text(encoding="utf-8")
    )
    if not isinstance(champion, dict):
        raise ValueError("invalid current champion evidence")
    fresh = {name: _sha_file(root / path) for name, path in SOURCE_FILES.items()}
    if fresh != fingerprints:
        raise RuntimeError("concurrent evidence modification; retry on coherent snapshot")
    result = evidence_engine(
        reports, scholarly, fingerprints=fingerprints,
        champion_version=champion.get("model_version"),
    )
    result["frequent_verified_online_research"] = recent_online_research_projection(root)
    return result


def markdown(result: dict) -> str:
    lines = [
        "# Evidence-Grounded LOTO7 Intelligence",
        "",
        f"- Latest result: **#{result['latest_known_draw']}**, independently verified: **{result['latest_draw_trusted']}**",
        f"- Production Champion (unchanged): `{result['champion_version']}`",
        "- This is an **explainable, policy-bounded research planner**, not a lottery-prediction model.",
        "",
        "## Four independent agents",
    ]
    for name, status in result["specialist_statuses"].items():
        lines.append(f"- **{name}**: {status}")
    if "frequent_verified_online_research" in result:
        fresh = result["frequent_verified_online_research"]
        lines += ["", "## Frequently verified new online evidence",
                  f"- Status: {fresh['status']}",
                  "- Public bibliographic metadata only; no model authority."]
        for topic in fresh.get("priority_topics_for_human_review", []):
            lines.append(f"- Human review priority: {topic}")
    lines += ["", "## Ranked next steps (advisory only)"]
    for i, task in enumerate(result["work_plan"], 1):
        deps = ", ".join(task["required_prior_tasks"]) or "none"
        lines.append(
            f"{i}. **{task['task_id']}** ({task['severity']}, risk priority {task['priority']}; "
            f"status {task['status']}) — {task['reason']}. Prerequisites: {deps}."
        )
    lines += [
        "", "## Evidence-level limits",
        "- Fair-world coverage mathematics does not predict which balls will appear.",
        "- Crossref/OpenAlex matching verifies bibliographic identity only.",
        "- Retrospective performance does not establish a future predictive edge.",
        "- No automatic Champion promotion, new trial budget or Production ticket changes.",
        f"- Evidence graph SHA256: `{result['evidence_graph_sha256']}`",
        f"- Work plan SHA256: `{result['work_plan_sha256']}`",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repo-root", type=Path, default=Path("."))
    p.add_argument("--out-dir", type=Path, default=OUTPUT)
    a = p.parse_args()
    report = run(a.repo_root)
    a.out_dir.mkdir(parents=True, exist_ok=True)
    (a.out_dir / "decision_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8")
    (a.out_dir / "decision_report.md").write_text(markdown(report), encoding="utf-8")
    print(json.dumps({
        "trusted": report["latest_draw_trusted"],
        "agents": report["specialist_statuses"],
        "top_actions": report["top_actions"],
        "no_production_writes": report["no_production_writes"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
