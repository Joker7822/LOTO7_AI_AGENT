#!/usr/bin/env python3
"""Research evidence -> human-reviewed, non-executable application readiness.

Combines the existing SHA-audited online discovery, metadata-only paper triage,
Crossref/OpenAlex validation, research proposals and fair-world sandbox. It
checks a *synthetic null control* mathematically and uses a deterministic,
non-actionable recommendation queue. Never executes unapproved experiments,
extends research budgets or changes frozen forecasts / Production.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import always_on_accuracy_agent as discovery
import research_literature_pipeline as reviews
import research_evidence_resilience as evidence

VERSION = "research-application-gate-v1"
STATUS_FILE = "research_application_readiness.json"
REPORT_FILE = "research_application_readiness_report.md"
VALID_BIBLIO = {"two_provider_bibliography_matched",
                "previously_verified_not_refreshed"}
HUMAN_PHASES = ("bibliographic_review", "full_text_and_license",
                "methodological_review", "new_future_preregistration",
                "independent_prospective_validation", "human_release_decision")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load(path: Path) -> dict:
    if not path.is_file():
        raise ValueError("missing required research input: " + path.name)
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError("malformed research input: " + path.name)
    return obj


def verify_inputs(root: Path) -> tuple[dict, dict, dict, dict, list[dict]]:
    out = root / "loto7_agent_output"
    trusted = discovery.inspect_evidence(root)
    state_path = out / discovery.STATE
    state = load(state_path)
    chain = discovery.read_chain(out / discovery.LEDGER)
    papers = reviews.checked_papers(state, chain)
    review = load(out / reviews.REVIEW_FILE)
    plans = load(out / reviews.DESIGN_FILE)
    verification = load(out / evidence.EVIDENCE)
    sandbox = load(out / evidence.SANDBOX)
    history_sha = trusted["draw_history_sha256"]
    state_sha = sha(state_path.read_bytes())
    chain_tip = chain[-1]["record_sha256"]
    for name, record in (("review", review), ("plan", plans)):
        if (record.get("version") != reviews.VERSION
                or record.get("discovery_state_sha256") != state_sha
                or record.get("discovery_chain_tip") != chain_tip
                or record.get("draw_history_sha256") != history_sha
                or record.get("research_mode") != trusted["research_mode"]):
            raise ValueError(name + " input changed since verified discovery")
    if (review.get("full_text_reviewed_count") != 0
            or review.get("automatic_model_selection") is not False
            or review.get("production_promotion_authorized") is not False
            or review.get("count") != len(review.get("reviews", []))
            or review["count"] != len(papers)):
        raise ValueError("metadata reviews overclaim scientific verification")
    if (plans.get("count") != len(plans.get("proposals", []))
            or plans.get("executed_experiments") != 0
            or plans.get("new_trials_consumed") != 0
            or plans.get("prior_registration_modified") is not False
            or plans.get("production_modified") is not False
            or plans.get("requires_human_approval") is not True):
        raise ValueError("proposal execution permissions invalid")
    # Recompute the exact fixed safe templates from audited metadata, rather
    # than trusting even well-formed but potentially edited model proposals.
    expected_review = [reviews.review(p) for p in papers]
    expected_review.sort(key=lambda x: (-x["triage_score_not_accuracy"], x["doi"]))
    if review["reviews"] != expected_review:
        raise ValueError("paper triage was altered after discovery")
    if plans["proposals"] != reviews.proposals(expected_review, trusted):
        raise ValueError("experiment proposals differ from locked non-executable templates")
    if (verification.get("version") != evidence.VERSION
            or verification.get("discovery_state_sha256") != state_sha
            or verification.get("discovery_tip_sha256") != chain_tip
            or verification.get("automatic_adoption") is not False
            or verification.get("future_registry_changed") is not False
            or verification.get("production_changed") is not False
            or verification.get("full_text_reviewed_count") != 0):
        raise ValueError("bibliographic verification is stale or unsafe")
    verified = verification.get("verifications", [])
    if not isinstance(verified, list) or len(verified) != len(papers):
        raise ValueError("metadata verification missing one or more candidates")
    by_doi = {}
    for item in verified:
        if not isinstance(item, dict) or not isinstance(item.get("doi"), str):
            raise ValueError("invalid bibliographic verification record")
        if item["doi"] in by_doi or item["doi"] not in {p["doi"] for p in papers}:
            raise ValueError("unregistered or duplicate verification DOI")
        if (item.get("status") not in VALID_BIBLIO
                | {"single_provider_only", "conflict_do_not_use",
                   "unavailable", "not_yet_checked"}):
            raise ValueError("unknown bibliographic verification status")
        if (item.get("peer_review_confirmed") is True
                or item.get("lottery_prediction_improved") is True
                or item.get("full_text_reviewed") is True):
            raise ValueError("metadata cannot claim paper review or proven lottery improvement")
        by_doi[item["doi"]] = item
    if len(by_doi) != len(papers):
        raise ValueError("incomplete bibliographic verification")
    return trusted, plans, sandbox, by_doi, papers


def check_synthetic_null(sandbox: dict) -> dict:
    """Mathematical counterexample: uniform is optimal under fair draws.

    The configured biased probability vector has 7 values p=.3 and 30
    others q=(7-2.1)/30. With a fair 7/37 marginal draw, expected
    Bernoulli proper log-edge is a negative average KL divergence, and
    expected Brier edge is exactly negative squared probability error.
    These are analytic checks, not evidence about real future outcomes.
    """
    q = 7 / 37
    p1 = .3
    p0 = (7 - 7 * p1) / 30
    predicted = [p1] * 7 + [p0] * 30
    expected_log = sum(
        q * math.log(p / q) + (1 - q) * math.log((1 - p) / (1 - q))
        for p in predicted
    ) / 37
    expected_brier = -sum((p - q) ** 2 for p in predicted) / 37
    expected_factor = 1.
    if (sandbox.get("scope") != "methodology_smoke_test_on_synthetic_fair_7_of_37_only"
            or sandbox.get("worlds") != evidence.FAIR_WORLDS
            or sandbox.get("draws_per_world") != evidence.DRAWS_PER_WORLD
            or sandbox.get("fixed_seed") != evidence.SEED
            or sandbox.get("forecasts_compared") !=
            ["uniform_7_of_37", "fixed_biased_probabilities"]
            or sandbox.get("future_oos_draws_consumed") != 0
            or sandbox.get("real_model_experiments_executed") != 0
            or sandbox.get("auto_promotion_allowed") is not False
            or sandbox.get("no_claim_about_actual_lottery_predictability") is not True):
        raise ValueError("synthetic sandbox was replaced or became an unauthorized real experiment")
    values = ("biased_sum_inclusion_p", "biased_minus_uniform_mean_log_score",
              "biased_minus_uniform_mean_brier_edge", "observed_null_mean_e_factor",
              "null_max_e_threshold_rate")
    for k in values:
        if (isinstance(sandbox.get(k), bool)
                or not isinstance(sandbox.get(k), (float, int))
                or not math.isfinite(sandbox[k])):
            raise ValueError("nonfinite synthetic diagnostic " + k)
    if (abs(sandbox["biased_sum_inclusion_p"] - 7) > 1e-8
            or sandbox.get("anytime_threshold") != 20
            or sandbox.get("nominal_alpha") != .05
            or not 0 <= sandbox["null_max_e_threshold_rate"] <= 1):
        raise ValueError("synthetic null invariant broken")
    # These tolerances account for fixed Monte Carlo sample sizes, not a
    # hypothesis test on actual draw outcomes.
    if (abs(sandbox["biased_minus_uniform_mean_log_score"] - expected_log) > .003
            or abs(sandbox["biased_minus_uniform_mean_brier_edge"] - expected_brier) > .003
            or abs(sandbox["observed_null_mean_e_factor"] - expected_factor) > .06
            or sandbox["null_max_e_threshold_rate"] > .10):
        raise ValueError("synthetic fairness control diverged from analytic null")
    return {
        "status": "synthetic_controls_passed",
        "fair_worlds": evidence.FAIR_WORLDS,
        "draws_per_world": evidence.DRAWS_PER_WORLD,
        "theoretical_biased_log_edge": expected_log,
        "observed_biased_log_edge": sandbox["biased_minus_uniform_mean_log_score"],
        "theoretical_biased_brier_edge": expected_brier,
        "observed_biased_brier_edge": sandbox["biased_minus_uniform_mean_brier_edge"],
        "expected_e_factor": 1.0,
        "observed_e_factor": sandbox["observed_null_mean_e_factor"],
        "null_threshold_crossing_rate": sandbox["null_max_e_threshold_rate"],
        "real_outcomes_used": 0,
        "real_model_accuracy_verified": False,
    }


def run(root: Path) -> dict:
    root = root.resolve()
    info, plan, sandbox, biblios, papers = verify_inputs(root)
    null = check_synthetic_null(sandbox)
    actionable = []
    for draft in plan["proposals"]:
        refs = draft["source_dois"]
        matched = [doi for doi in refs if biblios[doi]["status"] == "two_provider_bibliography_matched"]
        previously = [doi for doi in refs if biblios[doi]["status"] == "previously_verified_not_refreshed"]
        if not refs or not matched:
            status, next_step = ("bibliography_needs_verification",
                                 "Verify DOI/title/year with both Crossref and OpenAlex before reading methodology.")
        else:
            status, next_step = ("awaiting_full_text_and_methodology_review",
                                 "Review complete paper, assumptions, data, code, license and relevance; log explicit human decision.")
        # Actual research application is never permitted based solely on
        # bibliography and a synthetic null smoke test.
        if not info["two_source_verified"]:
            gate = "hold_new_prospective_grading_until_two_source_result_check"
        elif info["research_mode"] == "WAIT_FOR_NEW_DATA":
            gate = "wait_for_new_data_no_same_history_optimizer_search"
        else:
            gate = "methodology_review_required_before_any_new_study"
        actionable.append({
            "proposal_id": draft["proposal_id"], "topic": draft["topic"],
            "status": status, "application_gate": gate,
            "two_provider_matched_dois": matched,
            "previously_verified_not_refreshed_dois": previously,
            "next_step": next_step,
            "requires_human_approval": True,
            "full_text_review_completed": False,
            "prospective_results_available_for_this_proposal": False,
            "experiment_execution_allowed": False,
            "production_adoption_allowed": False,
        })
    out = root / "loto7_agent_output"
    report = {
        "version": VERSION,
        "scope": "research_triage_and_operational_review_only",
        "input_draw_sha256": info["draw_history_sha256"],
        "latest_round": info["latest_round"],
        "trusted_result_source": info["two_source_verified"],
        "research_mode": info["research_mode"],
        "research_trial_budget_unchanged": True,
        "read_only_science": True,
        "synthetic_control": null,
        "reviewed_publication_count": len(papers),
        "two_provider_bibliographic_matches": sum(
            x["status"] == "two_provider_bibliography_matched" for x in biblios.values()),
        "proposal_count": len(actionable),
        "application_queue": actionable,
        "human_review_phases": list(HUMAN_PHASES),
        "actual_prediction_accuracy_improvement_verified": False,
        "new_experiments_executed": 0,
        "automatic_model_training": False,
        "auto_production_release": False,
        "future_oos_or_production_changed": False,
    }
    (out / STATUS_FILE).write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8")
    lines = [
        "# Research-to-Application Scientific Gate", "",
        "Status: **Research-only; human validation required.**",
        "Two-source draw trust: **" + str(info["two_source_verified"]) + "**",
        "Research mode: **" + info["research_mode"] + "**",
        "Public paper records: **" + str(len(papers)) + "**",
        "Two-provider matching DOI records: **" + str(report["two_provider_bibliographic_matches"]) + "**",
        "Synthetic 7-of-37 controls: **" + null["status"] + "**",
        "Real lottery predictive improvement established: **NO**",
        "", "## Safe application queue",
    ]
    for item in actionable:
        lines.append("- " + item["topic"] + ": " + item["status"] + " — " + item["next_step"])
    lines.extend([
        "", "Evidence labels do not authorize code changes, new trials, prior-OOS",
        "modification, Champion promotion or Production publication.",
        "Fresh independent future results and separate human-approved preregistration",
        "are required for any future scientific or deployment claim.",
    ])
    (out / REPORT_FILE).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def main() -> int:
    p = argparse.ArgumentParser(description="Non-executable research application readiness")
    p.add_argument("--repo-root", type=Path, default=Path("."))
    args = p.parse_args()
    result = run(args.repo_root)
    print(json.dumps({"proposals":result["proposal_count"],
                      "null":result["synthetic_control"]["status"],
                      "promotion_allowed":result["auto_production_release"]},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
