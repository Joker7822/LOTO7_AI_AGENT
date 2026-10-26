#!/usr/bin/env python3
"""Apply online *research insights* to read-only day-to-day quality control.

Inputs are *existing* audited metadata/protocol results. This is not a paper
implementation, a new optimizer trial, or an authorized Production promotion.
Never changes the lottery model, issued tickets, OOS ledgers or research budget.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import balanced_uniform_portfolio as disjoint35
import disjoint_future_oos as disjoint_oos
import joint_set_v2_signal_oos_guard as trust
import top1_overlap34 as overlap34
from loto7_evolving_agent import make_history, read_csv_flexible

VERSION = "online-research-operational-audit-v1"
READONLY_INPUTS = (
    "loto7.csv",
    "loto7_agent_output/source_validation.json",
    "loto7_agent_output/research_application_readiness.json",
    "loto7_agent_output/research_experiment_proposals.json",
    "loto7_agent_output/research_verified_publications.json",
    "loto7_agent_output/research_cycle_guard.json",
    "loto7_agent_output/advanced_validation_lab_summary.json",
    "loto7_agent_output/future_holdout_state.json",
    "loto7_agent_output/joint_set_v2_signal_oos_state.json",
    "loto7_agent_output/model_champion.json",
    "research/disjoint_future_oos/registration.json",
    "research/disjoint_future_oos/freeze_0701.json",
)


def load(path: Path) -> dict:
    if not path.is_file():
        raise ValueError(f"missing required scientific record: {path}")
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return obj


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_no_unapproved_execution(gate: dict, plans: dict,
                                     literature: dict) -> None:
    if (gate.get("version") != "research-application-gate-v1"
            or gate.get("scope") != "research_triage_and_operational_review_only"
            or gate.get("read_only_science") is not True
            or gate.get("auto_production_release") is not False
            or gate.get("automatic_model_training") is not False
            or gate.get("new_experiments_executed") != 0
            or gate.get("future_oos_or_production_changed") is not False):
        raise ValueError("research gate is malformed or grants execution")
    if (plans.get("version") != "research-literature-review-and-design-v1"
            or plans.get("executed_experiments") != 0
            or plans.get("new_trials_consumed") != 0
            or plans.get("production_modified") is not False
            or plans.get("prior_registration_modified") is not False
            or plans.get("requires_human_approval") is not True):
        raise ValueError("research proposal data grants unapproved experiments")
    if (literature.get("version") != "research-evidence-resilience-v1"
            or literature.get("automatic_adoption") is not False
            or literature.get("production_changed") is not False
            or literature.get("future_registry_changed") is not False
            or literature.get("full_text_reviewed_count") != 0):
        raise ValueError("online bibliography overclaims scientific acceptance")
    entries = plans.get("proposals")
    queue = gate.get("application_queue")
    if not isinstance(entries, list) or not isinstance(queue, list):
        raise ValueError("missing research proposal or gate queue")
    if (len(entries) != plans.get("count")
            or len(queue) != gate.get("proposal_count")
            or {p.get("proposal_id") for p in entries} !=
               {q.get("proposal_id") for q in queue}
            or len({p.get("proposal_id") for p in entries}) != len(entries)):
        raise ValueError("proposal and gate identities or counts differ")
    for p in entries:
        if (not isinstance(p, dict)
                or p.get("status") != "draft_needs_human_method_review"
                or p.get("experiment_approved") is not False
                or p.get("code_execution_authorized") is not False
                or p.get("new_trial_budget_granted") is not False
                or p.get("future_oos_registration_created") is not False
                or p.get("production_promotion_authorized") is not False):
            raise ValueError("unauthorized trial, preregistration or production action")
    for item in queue:
        if (item.get("requires_human_approval") is not True
                or item.get("experiment_execution_allowed") is not False
                or item.get("production_adoption_allowed") is not False):
            raise ValueError("application gate queue is unsafe")


def validated_round(csv_path: Path, source_path: Path) -> tuple[int, str, str]:
    source_check = trust.validate_trusted_source(csv_path, source_path)
    if source_check.get("trusted") is not True:
        raise ValueError("latest lottery results are not independently verified")
    x, frame = make_history(read_csv_flexible(csv_path))
    rounds = [int("".join(c for c in str(v) if c.isdigit()))
              for v in frame["回別"]]
    if rounds != list(range(1, len(x) + 1)):
        raise ValueError("missing or out-of-sequence lottery round")
    last = rounds[-1]
    if last != source_check["round"]:
        raise ValueError("result-source round differs from chronological CSV")
    source = load(source_path)
    fingerprint = sha256(csv_path)
    if ((source.get("verification_provenance") or {}).get("draw_csv_sha256")
            != fingerprint):
        raise ValueError("source validation does not match CSV byte fingerprint")
    return last, fingerprint, frame["抽せん日"].iloc[-1].date().isoformat()


def make_operational_report(root: Path) -> dict:
    root = root.resolve()
    csv_path = root / "loto7.csv"
    record_dir = root / "loto7_agent_output"
    actual_round, csv_sha, last_date = validated_round(
        csv_path, record_dir / "source_validation.json"
    )
    gate = load(record_dir / "research_application_readiness.json")
    plans = load(record_dir / "research_experiment_proposals.json")
    bibliography = load(record_dir / "research_verified_publications.json")
    guard = load(record_dir / "research_cycle_guard.json")
    science = load(record_dir / "advanced_validation_lab_summary.json")
    holdout = load(record_dir / "future_holdout_state.json")
    signal = load(record_dir / "joint_set_v2_signal_oos_state.json")
    champion = load(record_dir / "model_champion.json")

    validate_no_unapproved_execution(gate, plans, bibliography)
    if not str(champion.get("model_version", "")).startswith("baseline-"):
        # This audit is explicitly pinned to the observed Champion identity;
        # a future Champion change requires review of comparisons.
        raise ValueError("unexpected Champion identity: review before operating audit")
    if holdout.get("horizon_trusted_draws") != 26 or signal.get("horizon_trusted_draws") != 26:
        raise ValueError("26-draw registered horizon changed")
    if (not isinstance(holdout.get("trusted_draws"), int)
            or not isinstance(signal.get("trusted_draws"), int)
            or not 0 <= holdout["trusted_draws"] <= 26
            or not 0 <= signal["trusted_draws"] <= 26):
        raise ValueError("invalid OOS horizon progress")
    if (holdout.get("promotion_role") == "production_direct"
            or signal.get("promotion_role") != "diagnostic_only"):
        raise ValueError("OOS roles changed; human scientific review required")

    research_root = root / "research" / "disjoint_future_oos"
    registration = load(research_root / "registration.json")
    disjoint_oos.register_guard(
        registration,
        root / "disjoint_future_oos.py",
        root / "balanced_uniform_portfolio.py",
    )
    freezes, grades = disjoint_oos.archive_guard(research_root, registration)
    if 701 not in freezes or len(freezes[701]["candidate_tickets"]) != 5:
        raise ValueError("first prospective disjoint freeze is missing")
    if registration["first_target"] != 701 or registration["horizon_trusted_draws"] != 26:
        raise ValueError("research prospective registration changed")

    scientific_sha = science.get("historical_data_sha256")
    gate_sha = gate.get("input_draw_sha256")
    plans_sha = plans.get("draw_history_sha256")
    bib_state = bibliography.get("discovery_state_sha256")
    scientific_fresh = scientific_sha == csv_sha
    literature_fresh = (
        gate_sha == csv_sha
        and plans_sha == csv_sha
        and gate.get("latest_round") == actual_round
        and plans.get("last_resolved_round") == actual_round
        and gate.get("research_mode") == guard.get("mode")
        and guard.get("data_sha256") == csv_sha
        and bibliography.get("discovery_state_sha256") ==
            plans.get("discovery_state_sha256")
        and bib_state is not None
    )
    if guard.get("data_sha256") != csv_sha:
        # A blocked guard is not permission for a new same-data search.
        safe_guard_status = "research_guard_stale_stop_new_trials"
    elif guard.get("mode") == "WAIT_FOR_NEW_DATA":
        safe_guard_status = "wait_for_new_data"
    else:
        safe_guard_status = "research_budget_only_as_existing_guard_permits"
    null35 = disjoint35.exact_disjoint_null()
    null34 = overlap34.exact_fair_null()
    if (null35["total_possible_draws"] != math.comb(37, 7)
            or null34["total_possible_draws"] != math.comb(37, 7)
            or null35["any_first_prize_probability"] != null34["first_prize_probability"]):
        raise ValueError("combinatorial counterfactual invariants broken")

    verified_doi_count = sum(
        item.get("status") in ("two_provider_bibliography_matched",
                               "previously_verified_not_refreshed")
        for item in bibliography.get("verifications", [])
    )
    topics = {p["topic"] for p in plans["proposals"]}
    fixed_uses = {
        "calibration": "Audit proper scores only after verified, prefrozen predictions are graded",
        "online_evaluation": "Preserve test-then-train chronology and pre-outcome freeze SHA",
        "anytime_evidence": "Keep strict prospective e-process and 26-draw holdout separate",
        "distribution_shift": "Flag stale/mismatched result and science snapshots, never fit to future",
        "selection_bias": "Reject historical best-of-many as Production promotion proof",
        "ensemble": "Compare only predeclared geometry-matched controls on identical future targets",
    }
    operational_uses = [
        {"topic": topic, "use": fixed_uses[topic],
         "applied_to": "read_only_audit",
         "paper_method_executed": False,
         "predictive_accuracy_confirmed": False}
        for topic in sorted(topics) if topic in fixed_uses
    ]
    blockers = []
    if not scientific_fresh:
        blockers.append("scientific_baseline_snapshot_stale")
    if not literature_fresh:
        blockers.append("online_research_readiness_stale")
    if safe_guard_status != "research_budget_only_as_existing_guard_permits":
        blockers.append(safe_guard_status)
    if holdout["trusted_draws"] < 26:
        blockers.append("formal_26_draw_holdout_incomplete")
    if signal["trusted_draws"] < 26:
        blockers.append("joint_v2_26_draw_signal_test_incomplete")
    if len(grades) < 26:
        blockers.append("disjoint_26_draw_geometry_test_incomplete")

    return {
        "version": VERSION,
        "purpose": "operational_quality_control_from_online_research_topics_only",
        "latest_verified_draw": actual_round,
        "latest_draw_date": last_date,
        "draw_csv_sha256": csv_sha,
        "input_provenance": {
            "source_status": "verified_two_result_sources",
            "research_guard_data_match": guard.get("data_sha256") == csv_sha,
            "historical_science_data_match": scientific_fresh,
            "online_readiness_data_match": literature_fresh,
            "online_readiness_last_round": gate.get("latest_round"),
            "online_designs_last_round": plans.get("last_resolved_round"),
            "research_guard_mode": guard.get("mode"),
        },
        "existing_champion": champion["model_version"],
        "research_doi_metadata_candidates": len(bibliography.get("verifications", [])),
        "bibliographic_candidates_passed_or_previously_verified": verified_doi_count,
        "peer_review_or_full_text_completed": False,
        "pre_registered_future_streams": {
            "existing_holdout": {"trusted": holdout["trusted_draws"], "horizon": 26},
            "joint_v2": {"trusted": signal["trusted_draws"], "horizon": 26},
            "disjoint35_research": {
                "trusted": len(grades), "horizon": 26,
                "frozen_targets": sorted(freezes),
            },
        },
        "fair_world_geometry_controls": {
            "disjoint35_score": null35["score"],
            "one_overlap34_score": null34["score"],
            "disjoint35_any3": null35["ge3"],
            "one_overlap34_any3": null34["ge3"],
            "identical_five_ticket_first_prize_odds": null35["any_first_prize_probability"],
            "note": "Fair-world mathematical geometry, not learned lottery forecasting skill",
        },
        "applied_operational_uses": operational_uses,
        "blockers": blockers,
        "recommended_next_step": (
            "Refresh science/review inputs using the EXISTING authorized pipelines "
            "and their SHA locks; no reset, retroactive freeze or new optimizer trials."
            if not (scientific_fresh and literature_fresh) else
            "Continue trusted result verification and preregistered future scoring, "
            "without changing already frozen predictions."
        ),
        "forecast_skill_established": False,
        "new_research_experiments_executed": 0,
        "unreviewed_external_code_executed": False,
        "production_changed": False,
        "existing_oos_changed": False,
        "research_budget_increased": False,
        "automatic_promotion_allowed": False,
    }


def report_text(record: dict) -> str:
    p = record["input_provenance"]
    streams = record["pre_registered_future_streams"]
    lines = [
        "# Online Research → Operational Quality Audit", "",
        "This is a read-only operational use of research topics, **not** a new model.",
        f"- Latest independently corroborated draw: **{record['latest_verified_draw']}** ({record['latest_draw_date']})",
        f"- Draw CSV fingerprint: `{record['draw_csv_sha256']}`",
        f"- Existing Champion: `{record['existing_champion']}`",
        f"- Scientific baseline current: **{p['historical_science_data_match']}**",
        f"- Online-review readiness current: **{p['online_readiness_data_match']}**",
        f"- Research guard: **{p['research_guard_mode']}**", "",
        "## Operational use of online findings",
    ]
    for item in record["applied_operational_uses"]:
        lines.append(f"- **{item['topic']}**: {item['use']} (audit only)")
    lines.extend(["", "## Trusted future observations"])
    for name, stream in streams.items():
        lines.append(f"- {name}: **{stream['trusted']}/{stream['horizon']}**")
    baseline = record["fair_world_geometry_controls"]
    lines.extend([
        "", "## Exact lottery-null controls",
        f"- Five disjoint tickets (35 numbers): **{baseline['disjoint35_score']:.6f}** composite score",
        f"- One shared anchor (34 numbers): **{baseline['one_overlap34_score']:.6f}** composite score",
        "- Equal five-distinct-ticket first-prize probability; no predictive-skill claim.",
        "", "## Blockers / safe next action",
    ])
    lines += [f"- {b}" for b in record["blockers"]] or ["- none, subject to human review"]
    lines += [
        "", record["recommended_next_step"], "",
        "**Not authorized:** full-paper method execution, new trial budget,",
        "automatic model training, Champion promotion, Production edits or",
        "modification of registered Future-OOS records.",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only operational science audit")
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--out", type=Path, default=Path(
        "research_output/online_research_operational_audit.json"))
    parser.add_argument("--report", type=Path, default=Path(
        "research_output/online_research_operational_audit.md"))
    args = parser.parse_args()
    result = make_operational_report(args.repo_root)
    for target, content in (
        (args.out, json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n"),
        (args.report, report_text(result))
    ):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    print(json.dumps({
        "draw": result["latest_verified_draw"],
        "blockers": result["blockers"],
        "ready_for_auto_promotion": result["automatic_promotion_allowed"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
