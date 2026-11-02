#!/usr/bin/env python3
"""Read-only Production AI adoption evidence audit.

A historical replay, a repaired arithmetic routine, or a successful CI run
does not establish predictive skill. This report NEVER changes Champion,
the 702+ disjoint35 policy, issued tickets, or registered future evidence.

Even passing evidence only requests *separate* human/model release review.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

VERSION = "production-ai-adoption-evidence-audit-v1"
# Proposal ID, not an implemented or registered predictive model version.
PROPOSAL = "calibration-shrinkage-proposal-v1"


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, dict) else {}


def _exact_nonnegative_int(value: object) -> int:
    return value if type(value) is int and value >= 0 else -1


def _good_comparator(record: object, horizon: int) -> bool:
    row = _mapping(record)
    if _exact_nonnegative_int(row.get("trusted_draws")) < horizon:
        return False
    # Boolean flags alone are insufficient. Independently check actual values
    # against the predeclared minimums, not against mutable reported thresholds.
    try:
        delta = float(row["mean_score_delta"])
        wins = float(row["win_rate"])
        e_value = float(row["e_value"])
    except (ValueError, TypeError, KeyError, OverflowError):
        return False
    import math
    return (math.isfinite(delta) and math.isfinite(wins)
            and math.isfinite(e_value) and delta >= 0.05
            and 0.55 <= wins <= 1.0 and e_value >= 20.0
            and row.get("passes_all") is True)


def audit(
    *,
    champion: object,
    holdout: object,
    issued: object,
    proposal: str = PROPOSAL,
) -> dict[str, Any]:
    champion = _mapping(champion)
    holdout = _mapping(holdout)
    issued = _mapping(issued)
    progress = _mapping(holdout.get("progress"))
    lock = _mapping(holdout.get("protocol_lock"))
    comparators = _mapping(holdout.get("comparators"))
    policy = _mapping(holdout.get("confirmation_policy"))
    reasons: list[str] = []

    champion_id = champion.get("model_version")
    if not isinstance(champion_id, str) or not champion_id:
        reasons.append("missing_champion_identity")
    if proposal == champion_id or not proposal:
        reasons.append("invalid_separate_candidate_identity")

    # There is no registered/frozen model for the proposed calibration rule.
    # Existing holdout evidence belongs to its own locked candidate, not this
    # proposed rule; prohibit borrowing its numbers for a different AI model.
    if holdout.get("locked_candidate_version") != proposal:
        reasons.append("missing_candidate_specific_future_evidence")

    horizon = _exact_nonnegative_int(progress.get("horizon_trusted_draws"))
    trusted = _exact_nonnegative_int(progress.get("trusted_draws"))
    matched = _exact_nonnegative_int(progress.get("matched_ensemble_trusted_draws"))
    if horizon < 26 or trusted < horizon or matched < horizon:
        reasons.append("incomplete_26_draw_future_holdout")

    if (lock.get("verified") is not True
            or not lock.get("stored_sha256")
            or lock.get("stored_sha256") != lock.get("observed_sha256")):
        reasons.append("unverified_protocol_lock")

    registration_draws = holdout.get("confirmation_policy_registered_at_trusted_draws")
    if type(registration_draws) is not int or registration_draws != 0:
        reasons.append("confirmation_rule_not_prefrozen_before_first_outcome")

    if (policy.get("claim_requires_full_horizon") is not True
            or policy.get("horizon_trusted_draws") != horizon):
        reasons.append("invalid_fixed_horizon_confirmation_policy")

    if not (holdout.get("confirmed") is True
            and holdout.get("claim_status") == "confirmed_operational_future_oos_edge"
            and progress.get("full_horizon_complete") is True):
        reasons.append("no_confirmed_prospective_predictive_edge")

    if horizon < 26 or not _good_comparator(comparators.get("uniform_random"), horizon):
        reasons.append("random_baseline_promotion_gate_not_met")
    if horizon < 26 or not _good_comparator(comparators.get("matched_ensemble32"), horizon):
        reasons.append("matched_ensemble_promotion_gate_not_met")

    # A ready-to-review outcome is NOT a Production switch. A separate
    # prospective registration, implementation review and explicit promotion
    # are always necessary, outside this audit's read-only authority.
    ready = not reasons
    return {
        "version": VERSION,
        "proposal": proposal,
        "proposal_is_implemented_model": False,
        "champion_version": champion_id,
        "issued_target_round": issued.get("target_round"),
        "issued_model_version": issued.get("model_version"),
        "issued_ticket_policy": issued.get("ticket_policy"),
        "trusted_future_draws": max(trusted, 0),
        "required_future_draws": max(horizon, 26),
        "status": "human_release_review_required" if ready else "blocked_no_independent_evidence",
        "candidate_review_ready": ready,
        "candidate_automatically_adopted": False,
        "production_changed": False,
        "registered_future_evidence_changed": False,
        "reasons": reasons,
        "next_action": (
            "Review implementation, independent registration and promotion separately"
            if ready else "Register a new candidate before an unknown future draw and collect independent evidence"
        ),
    }


def _read_json(path: Path) -> object:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}


def main() -> int:
    p = argparse.ArgumentParser(description="Audit proposed AI Production adoption without changing tickets")
    p.add_argument("--champion", type=Path, default=Path("loto7_agent_output/model_champion.json"))
    p.add_argument("--holdout", type=Path, default=Path("loto7_agent_output/future_holdout_evidence.json"))
    p.add_argument("--issued", type=Path, default=Path("loto7_agent_output/weekly_production_prediction_state.json"))
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    result = audit(
        champion=_read_json(args.champion),
        holdout=_read_json(args.holdout),
        issued=_read_json(args.issued),
    )
    rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
