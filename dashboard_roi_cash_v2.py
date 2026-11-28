#!/usr/bin/env python3
"""Read-only, SHA-anchored ROI-cash v2 dashboard projection.

Historical payouts below are the audited exploratory three-arm walk-forward
report at source draw #704, NOT actual receipts or prospective validation.
The source hash pins which historical dataset supported the exact figures;
a later source change marks the benchmark historical, never up-to-date.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from production_disjoint35_policy import ROI_CASH_VERSION, publication_policy_for_target

VERSION = "dashboard-roi-cash-v2-v1"
CHAMPION = "baseline-5fdb8dc2ad"
AUDITED_SOURCE_SHA256 = "9114a6f11003e7cc590e317f50b08da7cfc32cd5dfb1b9779432b032eca87b80"
AUDITED_LAST_ROUND = 704
AUDIT_RUN = "https://github.com/Joker7822/LOTO7_AI_AGENT/actions/runs/44990515557"
ADOPTION_PR = "https://github.com/Joker7822/LOTO7_AI_AGENT/pull/161"
COST_PER_TICKET_YEN = 300
TICKETS_PER_DRAW = 5
COST_PER_DRAW_YEN = COST_PER_TICKET_YEN * TICKETS_PER_DRAW
AUDITED_DRAW_COUNT = 703
AUDITED_CANDIDATE_PAYOUT_YEN = 922_400
AUDITED_PREVIOUS_PAYOUT_YEN = 228_600
AUDITED_BASELINE_PAYOUT_YEN = 205_500
AUDITED_LARGEST_SINGLE_PAYOUT_YEN = 705_400


def project_roi_cash_v2(root: Path, sources: dict, latest_prediction: dict) -> dict:
    """Produce a safe public operations view, independent of candidate tickets.

    Never use research preview as a public issued ticket. Never label the
    retrospective cash figures as purchases, skill, expected future ROI, or
    candidate-specific future OOS data.
    """
    source = sources.get("source", {})
    latest = source.get("latest", {})
    round_number = latest.get("round")
    if type(round_number) is not int or round_number < 1:
        raise ValueError("ROI dashboard requires a validated current draw number")
    verified = (source.get("status") == "ok"
                and source.get("verification") == "verified_two_result_sources")
    champion = sources.get("champion", {}).get("model_version")
    if not isinstance(champion, str) or not champion.startswith("baseline-"):
        raise ValueError("ROI dashboard requires valid approved Champion identity")
    if champion != CHAMPION:
        raise ValueError("ROI dashboard Champion differs from audited ROI v2 assignment")

    next_target = round_number + 1
    selected = (next_target >= 705 and
                publication_policy_for_target(next_target) == ROI_CASH_VERSION)
    issued = latest_prediction.get("status") == "published"
    issued_model = latest_prediction.get("model") if issued else None
    issued_target = latest_prediction.get("target_round") if issued else None
    if issued and (type(issued_target) is not int or not isinstance(issued_model, str)):
        raise ValueError("ROI dashboard received malformed issued Production metadata")
    issued_v2 = bool(
        issued and issued_target >= 705 and
        issued_model.endswith("+" + ROI_CASH_VERSION)
    )
    # An earlier frozen, still-published target can legitimately use the old
    # assignment. It is not a failed v2 deployment and must never be relabeled.
    if issued_v2 and issued_target == next_target:
        issuance_status = "roi_v2_published"
    elif selected and verified:
        issuance_status = "selected_not_yet_issued"
    elif selected:
        issuance_status = "source_unverified"
    else:
        issuance_status = "outside_current_policy"
    csv_path = root / "loto7.csv"
    if not csv_path.is_file():
        raise ValueError("ROI dashboard source CSV missing")
    data_sha = hashlib.sha256(csv_path.read_bytes()).hexdigest()
    audit_current = (round_number == AUDITED_LAST_ROUND
                     and data_sha == AUDITED_SOURCE_SHA256 and verified)
    cost = AUDITED_DRAW_COUNT * COST_PER_DRAW_YEN
    if AUDITED_CANDIDATE_PAYOUT_YEN - AUDITED_LARGEST_SINGLE_PAYOUT_YEN < 0:
        raise AssertionError("invalid historical cashflow audit fixture")
    return {
        "version": VERSION,
        "policy": ROI_CASH_VERSION,
        "champion": champion,
        "operator_selected": selected,
        "adoption": "explicit_operator_instruction_not_statistical_promotion",
        "new_issuance_from_round": 705,
        "next_selected_policy": publication_policy_for_target(next_target),
        "next_target_round": next_target,
        "latest_issued_target_round": issued_target,
        "latest_issued_policy": (
            issued_model.split("+", 1)[1]
            if issued_model and "+" in issued_model else None
        ),
        "latest_issued_v2": issued_v2,
        "issuance_status": issuance_status,
        "source_verified": verified,
        "reference": {
            "scope": "exploratory_walk_forward_hypothetical_purchases",
            "first_round": 2, "last_round": AUDITED_LAST_ROUND,
            "last_draw_date": "2026-11-20",
            "draw_count": AUDITED_DRAW_COUNT,
            "public_data_sha256": AUDITED_SOURCE_SHA256,
            "same_dataset_as_latest": audit_current,
            "ticket_count_per_draw": TICKETS_PER_DRAW,
            "ticket_cost_yen": COST_PER_TICKET_YEN,
            "total_cost_yen_per_arm": cost,
            "roi_v2_payout_yen": AUDITED_CANDIDATE_PAYOUT_YEN,
            "previous_v1_payout_yen": AUDITED_PREVIOUS_PAYOUT_YEN,
            "rank_order_payout_yen": AUDITED_BASELINE_PAYOUT_YEN,
            "roi_v2_net_yen": AUDITED_CANDIDATE_PAYOUT_YEN - cost,
            "roi_v2_without_largest_single_win_yen": (
                AUDITED_CANDIDATE_PAYOUT_YEN-AUDITED_LARGEST_SINGLE_PAYOUT_YEN
            ),
            "largest_single_win_yen": AUDITED_LARGEST_SINGLE_PAYOUT_YEN,
            "largest_single_win_round": 118,
            "audit_url": AUDIT_RUN,
        },
        "actual_purchase_receipts_verified": False,
        "actual_purchase_cost_yen": None,
        "actual_personal_roi": None,
        "future_cash_roi_improvement_confirmed": False,
        "candidate_specific_verified_future_roi": None,
        "automatic_purchase_authorized": False,
        "approved_future_roi_promotion_gate_passed": False,
        "adoption_pr_url": ADOPTION_PR,
    }
