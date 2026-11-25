#!/usr/bin/env python3
"""Make existing online scholarly metadata useful as audited research intelligence.

No paper method is implemented or executed. The inputs are DOI/title/year only,
SHA-anchored discovery and independently checked bibliographic identities. The
outputs are topic-level evidence quality, descriptive operational benchmarks,
and fixed *unapproved* research handoffs. No model, trial or ledger edits.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
from collections import Counter
from pathlib import Path

import always_on_accuracy_agent as discovery
import research_literature_pipeline as review
import research_evidence_resilience as verification
import research_application_gate as gate
import online_research_operational_audit as operations
import balanced_uniform_portfolio as disjoint
import top1_overlap34 as shared

VERSION = "online-evidence-intelligence-v1"
OUTPUT = Path("research_output/online_evidence_intelligence")
VERIFIED = {"two_provider_bibliography_matched", "previously_verified_not_refreshed"}
ALLOWED = VERIFIED | {"not_yet_checked", "single_provider_only", "conflict_do_not_use", "unavailable"}
MAX_PAPERS = 36
# These tasks are OUR fixed implementation choices, not commands extracted
# from untrusted titles, abstracts, DOIs, or paper metadata.
SAFE_METHODS = {
    "calibration": ("Audit fixed historical Top7 versus fair 49/37 baseline",
                    "Read-only descriptive baseline audit; do not refit probabilities"),
    "online_evaluation": ("Audit test-before-train ordering and frozen target hashes",
                          "Never score a forecast constructed after its outcome"),
    "anytime_evidence": ("Check registered, prefrozen 26-draw evidence horizons",
                         "No interim model changes, optional stopping or retroactive scores"),
    "distribution_shift": ("Check age and SHA agreement across research inputs",
                           "Do not infer a change in lottery ball probabilities"),
    "selection_bias": ("Keep explored historical winners out of promotion evidence",
                       "New trials require an independently registered budget"),
    "ensemble": ("Audit matched portfolio geometry and fixed references",
                 "No cherry-picked comparator or candidate on graded outcomes"),
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read(path: Path) -> dict:
    return gate.load(path)


def _chain_anchored_frozen_papers(
    state: dict, chain: list[dict], reviewed: dict,
    current_papers: list[dict], state_sha: str,
) -> tuple[list[dict], bool]:
    """Recover *historical* verified metadata only during observation-only drift.

    The live scientific state may advance its SHA-chained journal while an
    original pre-draw freeze is missing. That hourly observation must not
    destroy the previously checked bibliography, and must not make the older
    bibliography look current either. Validate the entire current chain first;
    then reconstruct the exact earlier DOI/title/year catalog from its prefix.
    Never silently accept altered, missing, or newly forged bibliographic data.
    """
    latest_tip = chain[-1]["record_sha256"]
    frozen_tip = reviewed.get("discovery_chain_tip")
    frozen_state_sha = reviewed.get("discovery_state_sha256")
    if frozen_tip == latest_tip and frozen_state_sha == state_sha:
        return current_papers, False
    if (state.get("observation_only") is not True
            or state.get("registered_science_status") != "BLOCKED_MISSING_PREFROZEN_701"
            or not isinstance(frozen_state_sha, str)
            or len(frozen_state_sha) != 64
            or any(ch not in "0123456789abcdef" for ch in frozen_state_sha)
            or not isinstance(frozen_tip, str)):
        raise ValueError("online reviewed metadata is stale or altered against SHA chain")
    matches = [i for i, event in enumerate(chain)
               if event["record_sha256"] == frozen_tip]
    if len(matches) != 1 or matches[0] >= len(chain) - 1:
        raise ValueError("online reviewed metadata is not anchored to a past SHA chain")
    i = matches[0]
    anchor_event = chain[i]
    if (anchor_event.get("evidence_sha256") != reviewed.get("draw_history_sha256")
            or anchor_event.get("research_mode") != reviewed.get("research_mode")
            or any(event.get("read_only") is not True
                   or event.get("source_data_modified") is not False
                   or event.get("automatic_model_selection") is not False
                   for event in chain[i + 1:])):
        raise ValueError("unsafe or inconsistent observation-only journal tail")
    origins = {}
    for event in chain[:i+1]:
        for record in event.get("new_papers", []):
            if not isinstance(record, dict):
                raise ValueError("invalid original research paper record")
            doi = record.get("doi")
            origins[doi] = (record.get("title"), record.get("year"))
    original_reviews = reviewed.get("reviews")
    if (not isinstance(original_reviews, list)
            or len(original_reviews) != len(origins)
            or len(original_reviews) > MAX_PAPERS):
        raise ValueError("historical discovery paper count mismatches original journal")
    by_doi = {paper["doi"]: paper for paper in current_papers}
    if len(by_doi) != len(current_papers):
        raise ValueError("duplicate paper in current journal")
    historic = []
    seen = set()
    for record in original_reviews:
        doi = record.get("doi") if isinstance(record, dict) else None
        if (not isinstance(doi, str) or doi in seen or doi not in origins
                or doi not in by_doi
                or (record.get("title"), record.get("year")) != origins[doi]
                or by_doi[doi]["title"] != origins[doi][0]
                or by_doi[doi]["year"] != origins[doi][1]):
            raise ValueError("historical DOI/title/year differs from authentic SHA journal")
        seen.add(doi)
        historic.append(by_doi[doi])
    if seen != set(origins):
        raise ValueError("missing historically collected papers")
    return historic, True


def frozen_inputs(root: Path) -> tuple[list[dict], dict, dict, dict, dict, dict, dict]:
    out = root / "loto7_agent_output"
    state_path = out / discovery.STATE
    state = read(state_path)
    chain = discovery.read_chain(out / discovery.LEDGER)
    current_papers = review.checked_papers(state, chain)
    if len(current_papers) > MAX_PAPERS:
        raise ValueError("online candidate budget exceeded")
    reviewed = read(out / review.REVIEW_FILE)
    live_state_sha = sha(state_path.read_bytes())
    papers, historical_snapshot = _chain_anchored_frozen_papers(
        state, chain, reviewed, current_papers, live_state_sha
    )
    plans = read(out / review.DESIGN_FILE)
    verified = read(out / verification.EVIDENCE)
    readiness = read(out / gate.STATUS_FILE)
    guard = read(out / discovery.FILES["budget"])
    operations.validate_no_unapproved_execution(readiness, plans, verified)
    state_hash = reviewed.get("discovery_state_sha256") if historical_snapshot else live_state_sha
    tip = reviewed.get("discovery_chain_tip") if historical_snapshot else chain[-1]["record_sha256"]
    expected_reviews = sorted(
        [review.review(p) for p in papers],
        key=lambda p: (-p["triage_score_not_accuracy"], p["doi"]),
    )
    if (reviewed.get("version") != review.VERSION
            or reviewed.get("discovery_state_sha256") != state_hash
            or reviewed.get("discovery_chain_tip") != tip
            or reviewed.get("research_mode") != state["research_mode"]
            or reviewed.get("reviews") != expected_reviews
            or reviewed.get("count") != len(papers)
            or reviewed.get("full_text_reviewed_count") != 0
            or reviewed.get("automatic_model_selection") is not False
            or reviewed.get("production_promotion_authorized") is not False):
        raise ValueError("online reviewed metadata is stale or altered against SHA chain")
    if (plans.get("discovery_state_sha256") != state_hash
            or plans.get("discovery_chain_tip") != tip
            or plans.get("research_mode") != state["research_mode"]
            or reviewed.get("draw_history_sha256") != plans.get("draw_history_sha256")
            or reviewed.get("last_resolved_round") != plans.get("last_resolved_round")):
        raise ValueError("research designs and reviewed sources have inconsistent lineage")
    if (type(guard.get("search_enabled")) is not bool
            or (guard.get("mode") == "SEARCH") != guard["search_enabled"]):
        raise ValueError("trial budget guard grants inconsistent search authority")
    # Plans are immutable evidence from the discovery snapshot (and can
    # legitimately predate a new trusted draw). Reconstruct their historical
    # permission bit from the SHA-anchored research_mode, NEVER from today's
    # unrelated research budget. Doing otherwise rejects correct old plans
    # whenever a new draw flips WAIT_FOR_NEW_DATA into SEARCH.
    frozen_mode = plans.get("research_mode")
    if frozen_mode not in {"SEARCH", "WAIT_FOR_NEW_DATA"}:
        raise ValueError("unrecognized frozen research budget mode")
    frozen_search = frozen_mode == "SEARCH"
    if (plans.get("draw_history_sha256") == guard.get("data_sha256")
            and frozen_search != guard["search_enabled"]):
        raise ValueError("current research budget contradicts same-data frozen permission")
    expected_plans = review.proposals(
        expected_reviews, {"search_enabled": frozen_search}
    )
    if plans.get("proposals") != expected_plans:
        raise ValueError("proposal deviates from locked human-authored designs")
    # The bounded DOI verifier may advance during observation-only operation
    # while proposal/readiness evidence remains anchored to an older prefix.
    # Validate the complete newer catalog before intersecting it with that
    # historical proposal catalog. Never re-label newer evidence as old.
    aligned = (verified.get("discovery_state_sha256") == state_hash
               and verified.get("discovery_tip_sha256") == tip
               and verified.get("latest_round") == plans["last_resolved_round"])
    live_bibliography = (
        historical_snapshot
        and verified.get("discovery_state_sha256") == live_state_sha
        and verified.get("discovery_tip_sha256") == chain[-1]["record_sha256"]
        and verified.get("latest_round") == state.get("latest_resolved_round")
    )
    if (not (aligned or live_bibliography)
            or verified.get("version") != verification.VERSION
            or verified.get("research_mode") != state["research_mode"]
            or readiness.get("input_draw_sha256") != plans["draw_history_sha256"]
            or readiness.get("latest_round") != plans["last_resolved_round"]
            or readiness.get("research_mode") != state["research_mode"]):
        raise ValueError("online verification/readiness does not trace to source audit")
    catalog = {p["doi"]: p for p in (current_papers if live_bibliography else papers)}
    if (not isinstance(verified.get("verifications"), list)
            or len(verified["verifications"]) != len(catalog)):
        raise ValueError("incomplete cross-provider identity reconciliation")
    statuses = {}
    for item in verified["verifications"]:
        if not isinstance(item, dict):
            raise ValueError("malformed DOI verification")
        doi = item.get("doi")
        if (doi not in catalog or doi in statuses
                or item.get("year") != catalog[doi]["year"]
                or item.get("status") not in ALLOWED):
            raise ValueError("duplicate, forged or unknown verified bibliographic item")
        if (item.get("full_text_reviewed") is not False
                or item.get("peer_review_confirmed") is not False
                or item.get("lottery_prediction_improved") is not False
                or item.get("methods_reproduced_from_paper") is True):
            raise ValueError("bibliographic evidence falsely claims a validated method")
        if item["status"] in VERIFIED and (
                item.get("crossref_consistent") is not True
                or item.get("openalex_consistent") is not True):
            raise ValueError("two-provider bibliographic identity is not corroborated")
        if item["status"] == "conflict_do_not_use" and (
                item.get("crossref_consistent") is True
                and item.get("openalex_consistent") is True):
            raise ValueError("claimed bibliographic conflict has two matching providers")
        statuses[doi] = item
    if set(catalog) != set(statuses):
        raise ValueError("one or more discovered works have no verified identity record")
    # Keep the real verifier provenance in the returned object. Only the
    # scoped status view is reduced to the historical proposal catalog.
    statuses = {p["doi"]: statuses[p["doi"]] for p in papers}
    return papers, reviewed, plans, verified, readiness, guard, statuses


def current_source(root: Path) -> dict:
    csv_path = root / "loto7.csv"
    src_path = root / "loto7_agent_output/source_validation.json"
    csv_sha = sha(csv_path.read_bytes())
    src = read(src_path)
    verified = src.get("verification") == "verified_two_result_sources"
    # Independent two-source guard. A failure on the pinned 699 fixture is
    # informative, but CANNOT authorize downstream prospective operations.
    status = operations.trust.validate_trusted_source(csv_path, src_path)
    trusted = status.get("trusted") is True
    if verified and not trusted:
        raise ValueError("claimed independent source verification fails trust guard")
    round_number = (src.get("latest") or {}).get("round")
    if type(round_number) is not int or round_number <= 0:
        raise ValueError("latest lottery result round invalid")
    if trusted and (
        status.get("round") != round_number
        or (src.get("verification_provenance") or {}).get("draw_csv_sha256") != csv_sha
    ):
        raise ValueError("verified draw source data fingerprint inconsistent")
    return {"round": round_number, "sha256": csv_sha,
            "independent_two_source_verified": trusted}


def topic_analytics(papers: list[dict], reviews: dict,
                    statuses: dict[str, dict], plans: dict, readiness: dict) -> tuple[list[dict], list[dict]]:
    by_doi = {v["doi"]: v for v in reviews["reviews"]}
    source_dois = {p["doi"] for p in papers}
    if set(by_doi) != source_dois:
        raise ValueError("review bibliography is incomplete")
    queue = {a["topic"]: a for a in readiness["application_queue"]}
    proposals = {p["topic"]: p for p in plans["proposals"]}
    if (len(queue) != len(readiness["application_queue"])
            or len(proposals) != len(plans["proposals"])
            or set(queue) != set(proposals)):
        raise ValueError("methodological proposal queue diverges from review")
    matrix = []
    actions = []
    for topic, _ in review.TOPICS:
        tagged = [p for p in papers if topic in by_doi[p["doi"]]["topics"]]
        status_count = Counter(statuses[p["doi"]]["status"] for p in tagged)
        matched_now = status_count["two_provider_bibliography_matched"]
        earlier_verified = status_count["previously_verified_not_refreshed"]
        pending = len(tagged) - matched_now - earlier_verified
        # Source includes title/DOI metadata, not validated methods. Even two
        # independent bibliographic services do not permit paper adoption.
        matrix.append({
            "topic": topic, "papers_tagged": len(tagged),
            "distinct_dois": sorted(p["doi"] for p in tagged),
            "publication_year_counts": {str(year): sum(p["year"] == year for p in tagged)
                                        for year in sorted({p["year"] for p in tagged})},
            "verification_status_counts": dict(sorted(status_count.items())),
            "currently_two_provider_matched": matched_now,
            "previously_matched_not_refreshed": earlier_verified,
            "pending_or_conflicting": pending,
            "full_text_examined": 0,
            "reproducibility_established": False,
            "lottery_skill_established": False,
            "bibliometric_scope": "nonrepresentative_capped_title_filtered_intake",
        })
        if topic not in proposals:
            if tagged:
                raise ValueError("research topic has papers but no proposed methodology")
            continue
        proposal = proposals[topic]
        queue_item = queue[topic]
        if (proposal.get("source_dois") !=
                [p["doi"] for p in reviews["reviews"]
                 if topic in p["topics"]][:4]):
            raise ValueError("draft source links were changed")
        # Content originates exclusively in fixed local templates.
        title, limitation = SAFE_METHODS[topic]
        if not tagged:
            raise ValueError("empty research proposal topic")
        action = {
            "action_id": sha((VERSION + ":" + topic).encode())[:16],
            "topic": topic,
            "safe_operational_application": title,
            "explicit_limit": limitation,
            "relevant_doi_count": len(tagged),
            "current_bibliography_mismatches_or_unchecked": pending,
            "matched_doi_count": matched_now,
            "verified_earlier_doi_count": earlier_verified,
            "blocked_research_protocol": proposal["proposal_id"],
            "review_stage": queue_item["status"],
            "handoff_priority": (
                "verify_bibliographic_identity" if pending
                else "review_full_text_methods_and_license"
            ),
            "method_from_external_paper_executed": False,
            "experiment_authorized": False,
            "new_budget_granted": False,
            "future_oos_registered": False,
            "production_promotion_allowed": False,
        }
        actions.append(action)
    actions.sort(key=lambda x: (-x["current_bibliography_mismatches_or_unchecked"],
                                -x["relevant_doi_count"], x["topic"]))
    return matrix, actions


def run(root: Path) -> dict:
    root = root.resolve()
    papers, reviews, plans, biblios, readiness, guard, statuses = frozen_inputs(root)
    source = current_source(root)
    matrix, actions = topic_analytics(papers, reviews, statuses, plans, readiness)
    research_sha = plans["draw_history_sha256"]
    live_state_sha = sha((root / "loto7_agent_output" / discovery.STATE).read_bytes())
    live_chain_tip = discovery.read_chain(
        root / "loto7_agent_output" / discovery.LEDGER
    )[-1]["record_sha256"]
    observation_snapshot_stale = (
        reviews["discovery_state_sha256"] != live_state_sha
        or reviews["discovery_chain_tip"] != live_chain_tip
    )
    stale = (source["sha256"] != research_sha
             or source["round"] != plans["last_resolved_round"])
    if (guard.get("mode") != "WAIT_FOR_NEW_DATA"
            and guard.get("mode") != "VALIDATION_ONLY"
            and guard.get("mode") != "SEARCH"):
        raise ValueError("unknown research budget mode")
    if guard.get("search_enabled") is True:
        # The analysis never consumes budget even if a separate guard has
        # permitted some other pre-approved experiment.
        budget_status = "search_approval_still_required"
    else:
        budget_status = "existing_optimizer_search_disallowed"
    # Pure mathematical, exact fair-world comparison: an approved
    # *operational* sanity check, not an experiment on new lottery outcomes.
    disjoint_null = disjoint.exact_disjoint_null()
    overlap_null = shared.exact_fair_null()
    if (disjoint_null["total_possible_draws"] != math.comb(37, 7)
            or overlap_null["total_possible_draws"] != math.comb(37, 7)
            or abs(disjoint_null["mean_hits"] - 49 / 37) > 1e-12
            or abs(overlap_null["mean_hits"] - 49 / 37) > 1e-12):
        raise ArithmeticError("fixed fair-lottery control invalid")
    checks = {
        "audit_chain_verified": True,
        "metadata_lineage_verified": True,
        "bibliography_statuses_reconciled": True,
        "discovery_metadata_is_current": not observation_snapshot_stale,
        "observation_only_historical_snapshot_validated": observation_snapshot_stale,
        "current_draw_verified": source["independent_two_source_verified"],
        "literature_synced_to_current_draw": not stale,
        "research_guard_matches_current_draw": guard.get("data_sha256") == source["sha256"],
        "research_budget_mode": guard["mode"],
        "optimizer_trials_opened": False,
    }
    blockers = []
    if not checks["current_draw_verified"]:
        blockers.append("latest_draw_requires_independent_source_corroboration")
    if stale:
        blockers.append("online_literature_analysis_uses_older_draw_snapshot")
    if observation_snapshot_stale:
        blockers.append("research_metadata_anchored_to_prior_observational_snapshot")
    if not checks["research_guard_matches_current_draw"]:
        blockers.append("research_budget_snapshot_stale")
    if any(t["pending_or_conflicting"] for t in matrix):
        blockers.append("bibliographic_identity_checks_incomplete")
    blockers.append("full_text_methodological_review_not_completed")
    return {
        "version": VERSION,
        "scope": "audited_collected_online_metadata_and_safe_operational_controls_only",
        "source": source,
        "research_snapshot": {
            "last_resolved_round": plans["last_resolved_round"],
            "draw_sha256": research_sha,
            "discovery_state_sha256": reviews["discovery_state_sha256"],
            "discovery_chain_tip": reviews["discovery_chain_tip"],
            "live_discovery_state_sha256": live_state_sha,
            "live_discovery_chain_tip": live_chain_tip,
            "historical_snapshot_validated": observation_snapshot_stale,
            "paper_count": len(papers), "topic_count": len(review.TOPICS),
            "bibliography_candidate_count": len(biblios["verifications"]),
            "bibliography_discovery_state_sha256": biblios["discovery_state_sha256"],
            "bibliography_discovery_chain_tip": biblios["discovery_tip_sha256"],
            "proposal_count": plans["count"],
            "search_query_bias": "small_curated_keyword_queries_not_systematic_review",
        },
        "quality_checks": checks,
        "provider_status_distribution": dict(sorted(
            Counter(v["status"] for v in statuses.values()).items()
        )),
        "distinct_papers_by_year": {str(year): sum(p["year"] == year for p in papers)
                                    for year in sorted({p["year"] for p in papers})},
        "topic_analytics": matrix,
        "practical_handoffs": actions,
        "executed_fixed_analytical_controls": {
            "uniform_seven_of_37_expected_top7_hits": 49 / 37,
            "disjoint35_expected_composite": disjoint_null["score"],
            "one_shared34_expected_composite": overlap_null["score"],
            "first_prize_probability_five_distinct_tickets":
                5 / math.comb(37, 7),
            "fair_lottery_predictive_skill_measured": False,
            "real_candidate_trials": 0,
        },
        "research_budget_status": budget_status,
        "blockers": blockers,
        "production_readiness": "not_authorized_without_full_text_review_and_future_oos",
        "new_predictions_generated": 0,
        "new_real_experiments": 0,
        "automatic_paper_method_execution": False,
        "production_or_champion_changed": False,
        "future_oos_registry_modified": False,
        "registered_protocols_changed": False,
        "auto_promotion_authorized": False,
    }


def csv_export(result: dict) -> str:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(["topic", "papers_tagged", "two_provider_matched_current",
                     "matched_earlier_not_refreshed", "pending_conflict_unchecked",
                     "next_safe_handoff", "lottery_skill_verified"])
    queue = {p["topic"]: p for p in result["practical_handoffs"]}
    for item in result["topic_analytics"]:
        topic = item["topic"]
        writer.writerow([topic, item["papers_tagged"],
                         item["currently_two_provider_matched"],
                         item["previously_matched_not_refreshed"],
                         item["pending_or_conflicting"],
                         queue[topic]["handoff_priority"] if topic in queue else "no_proposal",
                         "false"])
    return stream.getvalue()


def markdown(result: dict) -> str:
    r = result["research_snapshot"]
    s = result["source"]
    lines = [
        "# Online Evidence Intelligence — practical research handoff",
        "",
        "This analyzes previously collected DOI/title/year metadata only; it does not",
        "read complete papers or train a lottery predictor.",
        "",
        f"- Collected candidates: **{r['paper_count']}**; research proposals: **{r['proposal_count']}**",
        f"- Last audited lottery result: **#{s['round']}**, independently corroborated: **{s['independent_two_source_verified']}**",
        f"- Research literature snapshot through: **#{r['last_resolved_round']}**",
        f"- Research budget status: **{result['research_budget_status']}**",
        "",
        "## Theme analysis of the curated intake (NOT literature-wide trends)",
        "",
        "| Theme | DOI candidates | two-source fresh | older two-source | unverified/conflict |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for p in result["topic_analytics"]:
        lines.append(
            f"| {p['topic']} | {p['papers_tagged']} | {p['currently_two_provider_matched']} "
            f"| {p['previously_matched_not_refreshed']} | {p['pending_or_conflicting']} |"
        )
    lines.extend(["", "## Practical methodological handoffs (review required)"])
    for a in result["practical_handoffs"]:
        lines.append(
            f"- **{a['topic']}** — {a['safe_operational_application']}. "
            f"Next: `{a['handoff_priority']}`; related DOI count: {a['relevant_doi_count']}. "
            "**Not approved as a model change.**"
        )
    lines += ["", "## Blockers", *["- " + b for b in result["blockers"]],
              "", "Theoretical fair-world controls are mathematical checks only.",
              "No experimental optimizer budget, prediction, Champion, "
              "Production or registered Future OOS changes.",
              "DOI metadata is not proof of peer review, methodological "
              "reproducibility or increased lottery accuracy."]
    return "\n".join(lines) + "\n"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repo-root", type=Path, default=Path("."))
    p.add_argument("--output-dir", type=Path, default=OUTPUT)
    a = p.parse_args()
    result = run(a.repo_root)
    a.output_dir.mkdir(parents=True, exist_ok=True)
    (a.output_dir / "report.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8")
    (a.output_dir / "report.md").write_text(markdown(result), encoding="utf-8")
    (a.output_dir / "topics.csv").write_text(csv_export(result), encoding="utf-8")
    print(json.dumps({
        "papers": result["research_snapshot"]["paper_count"],
        "latest_verified": result["source"]["independent_two_source_verified"],
        "blockers": result["blockers"], "new_real_experiments": 0,
        "auto_promotion": False
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
