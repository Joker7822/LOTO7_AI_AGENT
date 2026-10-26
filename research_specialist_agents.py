#!/usr/bin/env python3
"""Four independently scheduled, bounded LOTO7 research specialists.

Each agent analyzes existing evidence only; no new optimizer, bookmaker,
ticket publication, paper code or OOS grade. Other agents' findings are not
an authorization channel. Outputs are disposable GitHub Actions artifacts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import balanced_uniform_portfolio as geometry
import disjoint_future_oos as future_geometry
import joint_set_v2_signal_oos_guard as source_guard
import online_research_operational_audit as safety
import production_ticket_geometry35 as production
import top1_overlap34 as overlapping

VERSION = "bounded-research-specialists-v1"
AGENTS = ("source_sentinel", "calibration_analyst",
          "prospective_custodian", "literature_examiner")
OUT = Path("research_output/autonomous_specialists")
AUTHORIZED = {
    "new_optimizer_trials": False,
    "automatic_champion_promotion": False,
    "production_ticket_issuance": False,
    "registered_future_oos_edits": False,
    "external_paper_code_execution": False,
    "research_budget_override": False,
}


def load(root: Path, name: str) -> dict:
    return safety.load(root / name)


def checksum(root: Path, name: str) -> str:
    return hashlib.sha256((root / name).read_bytes()).hexdigest()


def issue(code: str, status: str, detail: str, *, value: object = None) -> dict:
    if status not in ("pass", "watch", "block"):
        raise ValueError("unknown specialist finding severity")
    record = {"code": code, "status": status, "detail": detail}
    if value is not None:
        record["value"] = value
    return record


def report(name: str, root: Path, checks: list[dict],
           *, context: dict | None = None) -> dict:
    if name not in AGENTS or not checks:
        raise ValueError("invalid or empty specialist report")
    status = ("block" if any(c["status"] == "block" for c in checks)
              else "watch" if any(c["status"] == "watch" for c in checks)
              else "pass")
    return {
        "version": VERSION, "agent": name, "status": status,
        "checks": checks, "context": context or {},
        "decision": "advisory_only_no_model_release",
        "source_repo": "Joker7822/LOTO7_AI_AGENT",
        "permissions": dict(AUTHORIZED),
        "model_prediction_skill_claimed": False,
        "new_real_experiments_executed": 0,
        "production_changed": False,
        "existing_oos_changed": False,
        "inputs_are_read_only": True,
    }


def source_sentinel(root: Path) -> dict:
    csv_name = "loto7.csv"
    source_name = "loto7_agent_output/source_validation.json"
    actual_sha = checksum(root, csv_name)
    state = load(root, source_name)
    provenance = (state.get("verification_provenance") or {})
    claimed_verified = state.get("verification") == "verified_two_result_sources"
    try:
        verdict = source_guard.validate_trusted_source(
            root / csv_name, root / source_name)
    except (ValueError, RuntimeError, KeyError, TypeError) as exc:
        # The report remains usable for incident triage, but cannot approve
        # source trust or any dependent action.
        verdict = {"trusted": False, "round": None, "error": type(exc).__name__}
    trusted = verdict.get("trusted") is True
    current = provenance.get("draw_csv_sha256") == actual_sha
    if claimed_verified and not trusted:
        raise ValueError("declared verified source failed independent trust guard")
    checks = [
        issue("two_source_trust", "pass" if trusted else "block",
              "Result source has independently matching drawing provenance"
              if trusted else "Latest result is unverified: future grading must wait"),
        issue("source_sha256", "pass" if current else "block",
              "Result-source provenance matches exact draw CSV bytes"
              if current else "Result-source fingerprint and draw CSV differ"),
    ]
    research_guard = load(root, "loto7_agent_output/research_cycle_guard.json")
    guard_match = research_guard.get("data_sha256") == actual_sha
    checks.append(issue("research_guard_sha256",
        "pass" if guard_match else "watch",
        "Trial budget guard refers to current draw data"
        if guard_match else "Research trial budget guard is stale; do not reopen search"))
    if research_guard.get("search_enabled") is True and research_guard.get("mode") != "SEARCH":
        raise ValueError("research guard grants trials without SEARCH mode")
    return report("source_sentinel", root, checks, context={
        "claimed_verified": claimed_verified,
        "trusted_round": verdict.get("round"),
        "draw_sha256": actual_sha,
        "research_mode": research_guard.get("mode"),
        "research_guard_matches_csv": guard_match,
    })


def calibration_analyst(root: Path) -> dict:
    history = load(root, "loto7_agent_output/historical_replay_summary.json")
    science = load(root, "loto7_agent_output/advanced_validation_lab_summary.json")
    actual_sha = checksum(root, "loto7.csv")
    if (history.get("evaluation_type") != "strict_walk_forward_fixed_baseline"
            or history.get("first_evaluated_round") != 101
            or history.get("last_evaluated_round") !=
               history.get("first_evaluated_round") + history.get("evaluated_rounds") - 1):
        raise ValueError("historical calibration report chronology invalid")
    top7 = history.get("top7") or {}
    portfolio = history.get("portfolio_5_tickets") or {}
    p = top7.get("approx_two_sided_p")
    edge = portfolio.get("mean_score_delta_vs_random")
    if (not isinstance(p, (float, int)) or isinstance(p, bool)
            or not math.isfinite(p) or not 0 <= p <= 1
            or not isinstance(edge, (float, int)) or isinstance(edge, bool)
            or not math.isfinite(edge)):
        raise ValueError("calibration metric is invalid")
    top7_expected = 49.0 / 37.0
    observed_baseline = top7.get("random_theoretical_mean_hits")
    if (not isinstance(observed_baseline, (float, int))
            or abs(observed_baseline - top7_expected) > 1e-10):
        raise ValueError("historical uniform seven-of-37 baseline changed")
    hist_current = history.get("csv_sha256") == actual_sha
    sci_current = science.get("historical_data_sha256") == actual_sha
    checks = [
        issue("historical_replay_freshness", "pass" if hist_current else "watch",
              "Backtest and current draw data have identical hashes"
              if hist_current else "Historical scoring uses a different data snapshot"),
        issue("scientific_null_freshness", "pass" if sci_current else "watch",
              "Statistical null references current draw CSV"
              if sci_current else "Advanced scientific null report is historically pinned"),
        issue("top7_signal", "watch",
              "Descriptive reused-history Top7 p-value is NOT independent OOS",
              value=round(float(p), 8)),
        issue("ticket_layout_backtest", "watch",
              "Observed historical portfolio score delta is exploratory only",
              value=round(float(edge), 8)),
    ]
    return report("calibration_analyst", root, checks, context={
        "draw_sha256": actual_sha,
        "historical_rounds_evaluated": history["evaluated_rounds"],
        "top7_uniform_expected_matches": top7_expected,
        "historical_top7_mean_matches": top7.get("mean_hits"),
        "historical_p_value_descriptive_only": float(p),
        "historical_score_delta_exploratory": float(edge),
        "future_predictive_edge_confirmed": False,
    })


def prospective_custodian(root: Path) -> dict:
    holdout = load(root, "loto7_agent_output/future_holdout_state.json")
    signal = load(root, "loto7_agent_output/joint_set_v2_signal_oos_state.json")
    regdir = root / "research/disjoint_future_oos"
    registration = load(regdir.parent.parent, "research/disjoint_future_oos/registration.json")
    future_geometry.register_guard(
        registration,
        root / "disjoint_future_oos.py",
        root / "balanced_uniform_portfolio.py",
    )
    freezes, grades = future_geometry.archive_guard(regdir, registration)
    if not all(f in freezes for f in grades):
        raise ValueError("an OOS target was graded without a prior frozen forecast")
    if (holdout.get("protocol_lock_status") != "verified"
            or holdout.get("protocol_lock_version") != "future-holdout-protocol-lock-v1"
            or signal.get("promotion_role") != "diagnostic_only"
            or signal.get("interim_model_changes_allowed") is not False
            or signal.get("interim_endpoint_based_tuning_allowed") is not False):
        raise ValueError("registered future OOS authority or protocol drift")
    counts = {
        "existing_holdout": holdout.get("trusted_draws"),
        "joint_v2_signal": signal.get("trusted_draws"),
        "disjoint35_geometry": len(grades),
    }
    if any(type(n) is not int or not 0 <= n <= 26 for n in counts.values()):
        raise ValueError("future OOS trusted count out of registered horizon")
    if registration.get("horizon_trusted_draws") != 26:
        raise ValueError("disjoint geometry horizon changed")
    checks = [
        issue("immutable_registered_geometry", "pass",
              "Verified source-code locks and append-only future research chain"),
        issue("holdout_prospective_sample",
              "pass" if counts["existing_holdout"] == 26 else "watch",
              "Existing holdout: trusted observations within fixed 26-draw horizon",
              value=counts["existing_holdout"]),
        issue("joint_v2_prospective_sample",
              "pass" if counts["joint_v2_signal"] == 26 else "watch",
              "Joint Set v2: trusted observations within fixed 26-draw horizon",
              value=counts["joint_v2_signal"]),
        issue("disjoint_prospective_sample",
              "pass" if counts["disjoint35_geometry"] == 26 else "watch",
              "35-number research geometry: frozen, trusted results only",
              value=counts["disjoint35_geometry"]),
    ]
    return report("prospective_custodian", root, checks, context={
        "fixed_horizon": 26,
        "trusted_draws_by_stream": counts,
        "prefrozen_research_targets": sorted(freezes),
        "formal_automatic_promotion_eligible": False,
        "existing_holdout_protocol_sha256": holdout.get("protocol_lock_sha256"),
    })


def literature_examiner(root: Path) -> dict:
    gate = load(root, "loto7_agent_output/research_application_readiness.json")
    plans = load(root, "loto7_agent_output/research_experiment_proposals.json")
    bibliography = load(root, "loto7_agent_output/research_verified_publications.json")
    safety.validate_no_unapproved_execution(gate, plans, bibliography)
    actual_sha = checksum(root, "loto7.csv")
    stale = (gate.get("input_draw_sha256") != actual_sha
             or plans.get("draw_history_sha256") != actual_sha)
    verifications = bibliography["verifications"]
    if not isinstance(verifications, list) or len(verifications) > 36:
        raise ValueError("unbounded scholarly reference set")
    statuses = {}
    seen = set()
    for item in verifications:
        doi = item.get("doi")
        if not isinstance(doi, str) or doi in seen:
            raise ValueError("invalid/duplicate DOI")
        seen.add(doi)
        status = item.get("status")
        statuses[status] = statuses.get(status, 0) + 1
    n_conflict = statuses.get("conflict_do_not_use", 0)
    n_unchecked = statuses.get("not_yet_checked", 0) + statuses.get("single_provider_only", 0)
    checks = [
        issue("research_metadata_freshness", "watch" if stale else "pass",
              "Literature application review still uses an older draw history"
              if stale else "Literature application review matches current draw history"),
        issue("bibliography_conflicts", "watch" if n_conflict else "pass",
              "Conflicted records are excluded from model decisions", value=n_conflict),
        issue("bibliography_pending", "watch" if n_unchecked else "pass",
              "Bibliographic identities require bounded independent checking",
              value=n_unchecked),
        issue("unreviewed_methodology", "watch",
              "Title/DOI and short abstracts are NOT peer-review or validated methods",
              value=plans["count"]),
    ]
    return report("literature_examiner", root, checks, context={
        "candidate_dois": len(verifications),
        "status_counts": dict(sorted(statuses.items())),
        "draft_proposals": plans["count"],
        "full_text_reviewed_count": bibliography.get("full_text_reviewed_count"),
        "paper_method_training_approved": False,
    })


FUNCTIONS = {
    "source_sentinel": source_sentinel,
    "calibration_analyst": calibration_analyst,
    "prospective_custodian": prospective_custodian,
    "literature_examiner": literature_examiner,
}


def execute(root: Path, agent: str) -> dict:
    if agent not in FUNCTIONS:
        raise ValueError("unregistered agent")
    obj = FUNCTIONS[agent](root.resolve())
    if (obj["agent"] != agent
            or obj["decision"] != "advisory_only_no_model_release"
            or any(obj["permissions"].values())
            or not obj["inputs_are_read_only"]):
        raise ValueError("research specialist attempted privilege escalation")
    return obj


def main() -> int:
    parser = argparse.ArgumentParser(description="Four bounded autonomous research specialists")
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--agent", required=True, choices=AGENTS)
    parser.add_argument("--output-dir", type=Path, default=OUT)
    opts = parser.parse_args()
    report_data = execute(opts.repo_root, opts.agent)
    opts.output_dir.mkdir(parents=True, exist_ok=True)
    (opts.output_dir / (opts.agent + ".json")).write_text(
        json.dumps(report_data, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8")
    summary = [
        "# " + opts.agent, "",
        "Result: **" + report_data["status"] + "**",
        "Scope: read-only, no forecast/promotion/new-trial permissions.", "",
    ]
    for check in report_data["checks"]:
        summary.append("- **" + check["status"] + "** `" + check["code"] +
                       "`: " + check["detail"])
    (opts.output_dir / (opts.agent + ".md")).write_text(
        "\n".join(summary) + "\n", encoding="utf-8")
    print(json.dumps({"agent": opts.agent, "status": report_data["status"],
                      "checks": len(report_data["checks"]),
                      "permissions": report_data["permissions"]},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
