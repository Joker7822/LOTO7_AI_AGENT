#!/usr/bin/env python3
"""Conservative ROI-first promotion gate for a candidate-specific future study.

Historical ROI never authorizes promotion, even if a single third-prize hit
makes it look huge. Future candidate-specific evidence must have been frozen
before each draw. The gate is read-only; Production release is separate.
"""
from __future__ import annotations

from typing import Mapping, Sequence
import math
import re

from research.roi_cash_agent_v2 import VERSION as CANDIDATE_VERSION

VERSION="roi-cash-model-promotion-gate-v1"
TRUST="verified_two_result_sources"
MIN_FUTURE_TRUSTED=26
COST_PER_ARM_PER_ROUND=1500


def _payout(value:object)->int:
    if type(value) is not int or value<0:
        raise ValueError("payout must be exact nonnegative integer yen")
    return value


def evaluate_promotion(
    retrospective:Mapping[str,object],
    future_evidence:Mapping[str,object]|None=None,
) -> dict:
    """Report an independent release-review eligibility, never switch Production.

    Future source verification and immutable GitHub snapshot proofs must be
    checked by a separate trusted verification workflow. Self-reported records
    alone are NOT sufficient to release the model automatically.
    """
    reasons=[]
    if retrospective.get("candidate_version")!=CANDIDATE_VERSION:
        reasons.append("wrong_model_version")
    if retrospective.get("source_trust")!=TRUST:
        reasons.append("unverified_historical_source")
    if retrospective.get("production_promotion") is not False:
        reasons.append("production_was_modified_by_exploration")
    # Retrospective weakness is a warning, not a permanent veto.
    # Genuinely new candidate-specific future data may supersede old replay.
    retrospective_warning = retrospective.get("retrospective_roi_all_checks_passed") is not True
    future = future_evidence if isinstance(future_evidence,dict) else {}
    if future.get("candidate_version")!=CANDIDATE_VERSION:
        reasons.append("no_matching_future_candidate_registration")
    if future.get("source_verification")!=TRUST or future.get("protocol_frozen_before_first_draw") is not True:
        reasons.append("missing_independently_verified_future_protocol")
    # Unlike historical replay, candidate-specific future paired payouts must
    # be bound to proof generated before the draw, and independently verified.
    if future.get("independent_snapshot_audit_passed") is not True:
        reasons.append("no_independent_candidate_snapshot_audit")
    observations=future.get("paired_rounds")
    if not isinstance(observations,list):
        observations=[]
    if len(observations)<MIN_FUTURE_TRUSTED:
        reasons.append("incomplete_candidate_specific_26_round_future_oos")
    candidate=0
    incumbent=0
    deltas=[]
    seen=set()
    prev_round=None
    valid=len(observations)>0
    for row in observations:
        if not isinstance(row,dict):
            valid=False
            break
        r=row.get("round")
        if (type(r) is not int or r<=retrospective.get("last_round",10**9)
                or r in seen or (prev_round is not None and r!=prev_round+1)):
            valid=False
            break
        seen.add(r)
        prev_round=r
        if (row.get("source_verification")!=TRUST
                or row.get("prediction_frozen_before_draw") is not True
                or row.get("candidate_version")!=CANDIDATE_VERSION
                or row.get("same_35_numbers_validated") is not True
                or row.get("public_payout_complete") is not True
                or row.get("cost_yen_per_arm")!=COST_PER_ARM_PER_ROUND
                or not isinstance(row.get("pre_draw_candidate_sha256"),str)
                or re.fullmatch(r"[a-f0-9]{64}",row.get("pre_draw_candidate_sha256","")) is None
                or not isinstance(row.get("pre_draw_production_sha256"),str)
                or re.fullmatch(r"[a-f0-9]{64}",row.get("pre_draw_production_sha256","")) is None):
            valid=False
            break
        try:
            a=_payout(row["candidate_payout_yen"])
            b=_payout(row["production_payout_yen"])
        except (KeyError,ValueError):
            valid=False
            break
        candidate+=a
        incumbent+=b
        deltas.append(a-b)
    if not valid:
        reasons.append("future_payouts_or_freezes_invalid")
    if valid and len(deltas)>=MIN_FUTURE_TRUSTED:
        positive=sorted((d for d in deltas if d>0),reverse=True)
        if not candidate>incumbent:
            reasons.append("future_roi_not_greater_than_incumbent")
        if sum(deltas)-sum(positive[:4])<=0:
            reasons.append("future_roi_gain_depends_on_top_four_wins")
        if sum(deltas[-13:])<=0:
            reasons.append("recent_future_13_round_cashflow_declines")
    # A true-ready model still must be separately released by code review,
    # never from a mutable report or a GitHub Action without human approval.
    review_ready=not reasons
    return {
        "version":VERSION,
        "candidate_version":CANDIDATE_VERSION,
        "minimum_future_verified_draws":MIN_FUTURE_TRUSTED,
        "trusted_future_draws":len(deltas) if valid else 0,
        "candidate_future_payout_yen":candidate if valid and deltas else None,
        "production_future_payout_yen":incumbent if valid and deltas else None,
        "candidate_future_roi":candidate/(len(deltas)*COST_PER_ARM_PER_ROUND) if valid and deltas else None,
        "production_future_roi":incumbent/(len(deltas)*COST_PER_ARM_PER_ROUND) if valid and deltas else None,
        "retrospective_robust_roi_warning":retrospective_warning,
        "candidate_specific_future_review_ready":review_ready,
        "eligible_for_independent_release_review":review_ready,
        "auto_production_promotion":False,
        "production_ledger_modified":False,
        "reasons":reasons,
    }
