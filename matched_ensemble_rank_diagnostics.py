#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

import matched_permutation_ensemble as ensemble
import matched_permutation_oos as single
import strict_oos_governance as strict

VERSION = "matched-ensemble-rank-diagnostics-v1"
P_VALUE_METHOD = "monte_carlo_upper_tail_plus_one"
TIE_TOLERANCE = 1e-12

RANK_FIELDS = [
    "round", "draw_date", "candidate_version", "champion_version",
    "candidate_score", "ensemble_size", "null_below", "null_equal", "null_above",
    "candidate_midrank_from_top", "percentile_midrank", "permutation_p_upper",
    "trusted", "source_verification", "matched_ensemble_frozen_at_jst",
]

HOLDOUT_RANK_FIELDS = [
    "round", "draw_date", "holdout_version", "holdout_score", "ensemble_size",
    "null_below", "null_equal", "null_above", "candidate_midrank_from_top",
    "percentile_midrank", "permutation_p_upper", "trusted", "source_verification",
    "matched_ensemble_frozen_at_jst",
]


def rank_diagnostics(candidate_score: float, null_scores: Iterable[float]) -> Dict[str, float]:
    """Descriptive Monte-Carlo permutation rank against a pre-frozen null ensemble.

    The one-sided p-value uses the conservative +1 correction:
        p = (1 + #{null score >= observed score}) / (M + 1)

    Percentile uses a mid-rank treatment of ties within the M null scores.
    These diagnostics are intentionally NOT a Production promotion gate; the sequential
    e-process remains the inferential gate across future draws.
    """
    scores = [float(x) for x in null_scores]
    if not scores:
        raise ValueError("null_scores must be non-empty")
    c = float(candidate_score)
    below = sum(1 for s in scores if s < c and not math.isclose(s, c, abs_tol=TIE_TOLERANCE, rel_tol=0.0))
    equal = sum(1 for s in scores if math.isclose(s, c, abs_tol=TIE_TOLERANCE, rel_tol=0.0))
    above = len(scores) - below - equal
    m = len(scores)
    percentile = 100.0 * (below + 0.5 * equal) / m
    p_upper = (1.0 + above + equal) / (m + 1.0)
    midrank_from_top = 1.0 + above + 0.5 * equal
    return {
        "ensemble_size": float(m),
        "null_below": float(below),
        "null_equal": float(equal),
        "null_above": float(above),
        "candidate_midrank_from_top": float(midrank_from_top),
        "percentile_midrank": float(percentile),
        "permutation_p_upper": float(p_upper),
        "minimum_possible_p": float(1.0 / (m + 1.0)),
    }


def _member_scores(v4, members: Sequence[Sequence[Sequence[int]]], actual_set: set[int]) -> List[float]:
    return [float(v4.score_tickets(member, actual_set)["score"]) for member in members]


def _update_summary(state: Dict[str, object], diag: Dict[str, float], round_no: int, trusted: bool, prefix: str) -> None:
    state[f"last_{prefix}_rank_round"] = int(round_no)
    state[f"last_{prefix}_percentile_midrank"] = float(diag["percentile_midrank"])
    state[f"last_{prefix}_permutation_p_upper"] = float(diag["permutation_p_upper"])
    state[f"last_{prefix}_midrank_from_top"] = float(diag["candidate_midrank_from_top"])
    state[f"last_{prefix}_null_below"] = int(diag["null_below"])
    state[f"last_{prefix}_null_equal"] = int(diag["null_equal"])
    state[f"last_{prefix}_null_above"] = int(diag["null_above"])
    if not trusted:
        return
    state[f"{prefix}_trusted_draws"] = int(state.get(f"{prefix}_trusted_draws", 0) or 0) + 1
    state[f"{prefix}_percentile_sum"] = float(state.get(f"{prefix}_percentile_sum", 0.0) or 0.0) + float(diag["percentile_midrank"])
    state[f"{prefix}_permutation_p_sum"] = float(state.get(f"{prefix}_permutation_p_sum", 0.0) or 0.0) + float(diag["permutation_p_upper"])


def _valid_members(tickets, members, frozen_at) -> bool:
    return (
        bool(tickets)
        and isinstance(members, list)
        and len(members) == ensemble.ENSEMBLE_SIZE
        and bool(frozen_at)
        and all(single.geometry_preserved(tickets, member) for member in members)
    )


def _grade_holdout_rank(
    v4,
    out_dir: Path,
    latest_round: int,
    draw_date: str,
    actual_set: set[int],
    verification: str,
    trusted: bool,
) -> None:
    registry_path = out_dir / "future_holdout_registry.json"
    state_path = out_dir / "future_holdout_state.json"
    registry = strict.load_json(registry_path, {})
    state = strict.load_json(state_path, {})
    if not registry or not state or int(registry.get("target_round", -1)) != int(latest_round):
        return

    graded = state.setdefault("matched_ensemble_rank_graded_rounds", [])
    if latest_round in graded:
        return
    tickets = registry.get("holdout_tickets") or []
    members = registry.get("matched_ensemble_tickets")
    frozen_at = registry.get("matched_ensemble_frozen_at_jst")
    if not _valid_members(tickets, members, frozen_at):
        state["matched_ensemble_rank_diagnostics_status"] = "invalid_missing_prefrozen_matched_ensemble"
        strict.write_json(state_path, state)
        return

    observed = float(v4.score_tickets(tickets, actual_set)["score"])
    null_scores = _member_scores(v4, members, actual_set)
    diag = rank_diagnostics(observed, null_scores)
    _update_summary(state, diag, latest_round, trusted, "matched_ensemble_rank")
    graded.append(latest_round)
    state["matched_ensemble_rank_diagnostics_version"] = VERSION
    state["matched_ensemble_rank_p_value_method"] = P_VALUE_METHOD
    state["matched_ensemble_rank_minimum_possible_p"] = float(1.0 / (ensemble.ENSEMBLE_SIZE + 1.0))
    state["matched_ensemble_rank_diagnostics_status"] = "active"
    strict.write_json(state_path, state)

    strict.append_csv(out_dir / "future_holdout_matched_ensemble_rank_results.csv", [{
        "round": latest_round,
        "draw_date": draw_date,
        "holdout_version": state.get("locked_candidate_version", ""),
        "holdout_score": f"{observed:.6f}",
        "ensemble_size": ensemble.ENSEMBLE_SIZE,
        "null_below": int(diag["null_below"]),
        "null_equal": int(diag["null_equal"]),
        "null_above": int(diag["null_above"]),
        "candidate_midrank_from_top": f"{diag['candidate_midrank_from_top']:.6f}",
        "percentile_midrank": f"{diag['percentile_midrank']:.6f}",
        "permutation_p_upper": f"{diag['permutation_p_upper']:.8f}",
        "trusted": str(bool(trusted)).lower(),
        "source_verification": verification,
        "matched_ensemble_frozen_at_jst": frozen_at or "",
    }], HOLDOUT_RANK_FIELDS)


def _grade_rank(
    v4,
    registry: Dict[str, object],
    latest_round: int,
    draw_date: str,
    actual_set: set[int],
    verification: str,
    trusted: bool,
    oos_state: Dict[str, object],
    result_path: Path,
) -> None:
    refs = registry.get("matched_ensemble_by_candidate")
    refs = refs if isinstance(refs, dict) else {}
    frozen_at = registry.get("matched_ensemble_frozen_at_jst")
    champion_version = str(registry.get("champion_version", ""))
    evidence = oos_state.get("evidence") if isinstance(oos_state.get("evidence"), dict) else {}
    rows = []

    for item in registry.get("candidates", []) or []:
        if not isinstance(item, dict):
            continue
        version = str(item.get("version", ""))
        tickets = item.get("tickets") or []
        members = refs.get(version)
        if not version or not _valid_members(tickets, members, frozen_at):
            continue
        observed = float(v4.score_tickets(tickets, actual_set)["score"])
        null_scores = _member_scores(v4, members, actual_set)
        diag = rank_diagnostics(observed, null_scores)
        rec = evidence.get(v4.e_key(version, champion_version), {}) if isinstance(evidence, dict) else {}
        if isinstance(rec, dict):
            _update_summary(rec, diag, latest_round, trusted, "matched_ensemble_rank")
            rec["matched_ensemble_rank_diagnostics_version"] = VERSION
            rec["matched_ensemble_rank_p_value_method"] = P_VALUE_METHOD
            rec["matched_ensemble_rank_minimum_possible_p"] = float(1.0 / (ensemble.ENSEMBLE_SIZE + 1.0))
            if isinstance(evidence, dict):
                evidence[v4.e_key(version, champion_version)] = rec

        rows.append({
            "round": latest_round,
            "draw_date": draw_date,
            "candidate_version": version,
            "champion_version": champion_version,
            "candidate_score": f"{observed:.6f}",
            "ensemble_size": ensemble.ENSEMBLE_SIZE,
            "null_below": int(diag["null_below"]),
            "null_equal": int(diag["null_equal"]),
            "null_above": int(diag["null_above"]),
            "candidate_midrank_from_top": f"{diag['candidate_midrank_from_top']:.6f}",
            "percentile_midrank": f"{diag['percentile_midrank']:.6f}",
            "permutation_p_upper": f"{diag['permutation_p_upper']:.8f}",
            "trusted": str(bool(trusted)).lower(),
            "source_verification": verification,
            "matched_ensemble_frozen_at_jst": frozen_at or "",
        })

    strict.append_csv(result_path.parent / "matched_ensemble_rank_results.csv", rows, RANK_FIELDS)
    _grade_holdout_rank(v4, result_path.parent, latest_round, draw_date, actual_set, verification, trusted)
    oos_state["matched_ensemble_rank_diagnostics_version"] = VERSION
    oos_state["matched_ensemble_rank_p_value_method"] = P_VALUE_METHOD
    oos_state["matched_ensemble_rank_minimum_possible_p"] = float(1.0 / (ensemble.ENSEMBLE_SIZE + 1.0))
    oos_state["matched_ensemble_rank_promotion_role"] = "diagnostic_only"


def install(v4) -> None:
    if getattr(v4, "_matched_ensemble_rank_diagnostics_installed", False):
        return
    if not getattr(v4, "_matched_permutation_ensemble_installed", False):
        raise RuntimeError("matched_permutation_ensemble.install(v4) must run first")
    original_grade = v4.grade_registry

    def grade_wrapper(registry, latest_round, draw_date, actual_set, verification,
                      trusted, oos_state, result_path):
        graded = original_grade(
            registry, latest_round, draw_date, actual_set, verification,
            trusted, oos_state, result_path,
        )
        if not graded:
            return False
        _grade_rank(
            v4, registry, latest_round, draw_date, actual_set, verification,
            trusted, oos_state, result_path,
        )
        return True

    v4.grade_registry = grade_wrapper
    v4._matched_ensemble_rank_diagnostics_installed = True


def bootstrap_before_main(v4, argv: Optional[Sequence[str]] = None) -> Dict[str, object]:
    args = strict._cli_context(argv)
    oos_path = args.out_dir / "oos_candidate_state.json"
    holdout_path = args.out_dir / "future_holdout_state.json"
    oos = strict.load_json(oos_path, {})
    holdout = strict.load_json(holdout_path, {})
    minimum_p = float(1.0 / (ensemble.ENSEMBLE_SIZE + 1.0))
    oos["matched_ensemble_rank_diagnostics_version"] = VERSION
    oos["matched_ensemble_rank_p_value_method"] = P_VALUE_METHOD
    oos["matched_ensemble_rank_minimum_possible_p"] = minimum_p
    oos["matched_ensemble_rank_promotion_role"] = "diagnostic_only"
    strict.write_json(oos_path, oos)
    if holdout:
        holdout["matched_ensemble_rank_diagnostics_version"] = VERSION
        holdout["matched_ensemble_rank_p_value_method"] = P_VALUE_METHOD
        holdout["matched_ensemble_rank_minimum_possible_p"] = minimum_p
        holdout["matched_ensemble_rank_diagnostics_status"] = "active"
        strict.write_json(holdout_path, holdout)
    return {
        "version": VERSION,
        "ensemble_size": ensemble.ENSEMBLE_SIZE,
        "minimum_possible_p": minimum_p,
        "promotion_role": "diagnostic_only",
    }


def finalize_after_main(v4, argv: Optional[Sequence[str]] = None) -> Dict[str, object]:
    return bootstrap_before_main(v4, argv)
