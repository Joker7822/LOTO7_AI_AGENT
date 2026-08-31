#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

import numpy as np

import strict_oos_governance as strict

VERSION = "matched-permutation-null-v1"
SEED_BASE = 23_000_000
SEED_MULTIPLIER = 1013

MATCHED_FIELDS = [
    "round", "draw_date", "candidate_version", "champion_version", "formal_block_index",
    "candidate_score", "matched_score", "delta_vs_matched",
    "candidate_max_hits", "matched_max_hits", "matched_e_value_raw",
    "family_weight", "family_adjusted_e_value", "required_raw_e_value",
    "trusted_for_promotion", "source_verification", "matched_reference_frozen_at_jst",
]

HOLDOUT_MATCHED_FIELDS = [
    "round", "draw_date", "holdout_version", "holdout_score", "matched_score",
    "delta_vs_matched", "holdout_max_hits", "matched_max_hits", "matched_e_value",
    "trusted", "source_verification", "frozen_at_jst",
]


def permutation_for_round(target_round: int) -> List[int]:
    """Return a deterministic predeclared permutation of labels 1..37."""
    rng = np.random.default_rng(SEED_BASE + int(target_round) * SEED_MULTIPLIER)
    return [int(x) for x in rng.permutation(np.arange(1, 38))]


def permute_tickets(tickets: Iterable[Iterable[int]], target_round: int) -> List[List[int]]:
    permutation = permutation_for_round(target_round)
    mapping = {i + 1: permutation[i] for i in range(37)}
    out: List[List[int]] = []
    for ticket in tickets:
        mapped = sorted(mapping[int(n)] for n in ticket)
        out.append(mapped)
    return out


def geometry_signature(tickets: Iterable[Iterable[int]]) -> Dict[str, object]:
    sets = [set(int(n) for n in ticket) for ticket in tickets]
    pairwise = []
    for i in range(len(sets)):
        for j in range(i + 1, len(sets)):
            pairwise.append(len(sets[i] & sets[j]))
    return {
        "ticket_sizes": [len(s) for s in sets],
        "union_size": len(set().union(*sets)) if sets else 0,
        "pairwise_overlaps": pairwise,
    }


def geometry_preserved(original: Iterable[Iterable[int]], matched: Iterable[Iterable[int]]) -> bool:
    return geometry_signature(original) == geometry_signature(matched)


def _build_reference_map(registry: Dict[str, object], target_round: int) -> Dict[str, List[List[int]]]:
    refs: Dict[str, List[List[int]]] = {}
    for item in registry.get("candidates", []) or []:
        if not isinstance(item, dict):
            continue
        version = str(item.get("version", ""))
        tickets = item.get("tickets") or []
        if not version or not tickets:
            continue
        matched = permute_tickets(tickets, target_round)
        if not geometry_preserved(tickets, matched):
            raise RuntimeError("matched permutation changed portfolio geometry")
        refs[version] = matched
    return refs


def ensure_matched_reference(v4, registry_path: Path, latest_round: Optional[int] = None) -> bool:
    registry = strict.load_json(registry_path, {})
    if not registry:
        return False
    target_round = int(registry.get("target_round", -1))
    candidates = [x for x in (registry.get("candidates") or []) if isinstance(x, dict) and x.get("version")]
    expected = {str(x.get("version")) for x in candidates}
    existing = registry.get("matched_reference_by_candidate")
    ready = isinstance(existing, dict) and expected and expected.issubset(set(existing.keys()))

    # Fail closed: never create a supposedly pre-frozen matched null after the draw is known.
    if latest_round is not None and target_round <= int(latest_round):
        return bool(ready and registry.get("matched_reference_frozen_at_jst"))
    if ready and registry.get("matched_reference_frozen_at_jst"):
        return True
    if target_round < 1 or not expected:
        return False

    refs = _build_reference_map(registry, target_round)
    if set(refs) != expected:
        return False
    registry["matched_reference_by_candidate"] = refs
    registry["matched_reference_method"] = "common_label_permutation_preserving_portfolio_geometry"
    registry["matched_reference_seed_policy"] = f"{SEED_BASE} + target_round * {SEED_MULTIPLIER}"
    registry["matched_reference_permutation"] = permutation_for_round(target_round)
    registry["matched_reference_frozen_at_jst"] = v4.now_jst()
    registry["matched_reference_version"] = VERSION
    strict.write_json(registry_path, registry)
    return True


def ensure_holdout_matched_reference(v4, registry_path: Path, state_path: Path,
                                     latest_round: Optional[int] = None) -> bool:
    registry = strict.load_json(registry_path, {})
    state = strict.load_json(state_path, {})
    if not registry or not state:
        return False
    target_round = int(registry.get("target_round", -1))
    tickets = registry.get("holdout_tickets") or []
    existing = registry.get("matched_reference_tickets") or []
    ready = bool(existing and registry.get("matched_reference_frozen_at_jst"))
    if latest_round is not None and target_round <= int(latest_round):
        return ready
    if ready:
        return True
    if target_round < 1 or not tickets:
        return False

    matched = permute_tickets(tickets, target_round)
    if not geometry_preserved(tickets, matched):
        return False
    registry["matched_reference_tickets"] = matched
    registry["matched_reference_method"] = "common_label_permutation_preserving_holdout_geometry"
    registry["matched_reference_seed_policy"] = f"{SEED_BASE} + target_round * {SEED_MULTIPLIER}"
    registry["matched_reference_permutation"] = permutation_for_round(target_round)
    registry["matched_reference_frozen_at_jst"] = v4.now_jst()
    registry["matched_reference_version"] = VERSION
    strict.write_json(registry_path, registry)

    state.setdefault("matched_trusted_draws", 0)
    state.setdefault("sum_delta_vs_matched", 0.0)
    state.setdefault("wins_vs_matched", 0)
    state.setdefault("matched_e_components", {str(l): 1.0 for l in v4.E_LAMBDAS})
    state.setdefault("matched_e_value", 1.0)
    state.setdefault("matched_graded_rounds", [])
    state["matched_reference_version"] = VERSION
    strict.write_json(state_path, state)
    return True


def _update_matched_evidence(v4, rec: Dict[str, object], delta: float, trusted: bool) -> None:
    if not trusted:
        return
    rec["matched_trusted_draws"] = int(rec.get("matched_trusted_draws", 0) or 0) + 1
    rec["matched_sum_delta"] = float(rec.get("matched_sum_delta", 0.0) or 0.0) + float(delta)
    if delta > 0:
        rec["matched_wins"] = int(rec.get("matched_wins", 0) or 0) + 1
    normalized = max(-1.0, min(1.0, float(delta) / float(v4.MAX_PORTFOLIO_SCORE)))
    comps = strict.update_e_components(rec.get("matched_e_components"), normalized, v4.E_LAMBDAS)
    rec["matched_e_components"] = comps
    rec["matched_e_value_raw"] = strict.e_value_from_components(comps, v4.E_LAMBDAS)


def _grade_holdout_matched(v4, out_dir: Path, latest_round: int, draw_date: str,
                           actual_set: set[int], verification: str, trusted: bool) -> None:
    registry_path = out_dir / "future_holdout_registry.json"
    state_path = out_dir / "future_holdout_state.json"
    registry = strict.load_json(registry_path, {})
    state = strict.load_json(state_path, {})
    if not registry or not state or int(registry.get("target_round", -1)) != int(latest_round):
        return
    graded = state.setdefault("matched_graded_rounds", [])
    if latest_round in graded:
        return
    holdout_tickets = registry.get("holdout_tickets") or []
    matched_tickets = registry.get("matched_reference_tickets") or []
    matched_valid = bool(matched_tickets) and bool(registry.get("matched_reference_frozen_at_jst"))
    if not holdout_tickets or not matched_valid:
        state["status"] = "invalid_missing_prefrozen_matched_reference"
        strict.write_json(state_path, state)
        return

    hm = v4.score_tickets(holdout_tickets, actual_set)
    mm = v4.score_tickets(matched_tickets, actual_set)
    dm = float(hm["score"] - mm["score"])
    if trusted:
        state["matched_trusted_draws"] = int(state.get("matched_trusted_draws", 0) or 0) + 1
        state["sum_delta_vs_matched"] = float(state.get("sum_delta_vs_matched", 0.0) or 0.0) + dm
        if dm > 0:
            state["wins_vs_matched"] = int(state.get("wins_vs_matched", 0) or 0) + 1
        normalized = max(-1.0, min(1.0, dm / float(v4.MAX_PORTFOLIO_SCORE)))
        comps = strict.update_e_components(state.get("matched_e_components"), normalized, v4.E_LAMBDAS)
        state["matched_e_components"] = comps
        state["matched_e_value"] = strict.e_value_from_components(comps, v4.E_LAMBDAS)
    graded.append(latest_round)
    state["matched_reference_version"] = VERSION
    strict.write_json(state_path, state)
    strict.append_csv(out_dir / "future_holdout_matched_results.csv", [{
        "round": latest_round,
        "draw_date": draw_date,
        "holdout_version": state.get("locked_candidate_version", ""),
        "holdout_score": f"{hm['score']:.6f}",
        "matched_score": f"{mm['score']:.6f}",
        "delta_vs_matched": f"{dm:.6f}",
        "holdout_max_hits": f"{hm['max_hits']:.0f}",
        "matched_max_hits": f"{mm['max_hits']:.0f}",
        "matched_e_value": f"{float(state.get('matched_e_value', 1.0)):.8f}",
        "trusted": str(bool(trusted)).lower(),
        "source_verification": verification,
        "frozen_at_jst": registry.get("matched_reference_frozen_at_jst", ""),
    }], HOLDOUT_MATCHED_FIELDS)


def _grade_registry(v4, original, registry: Dict[str, object], latest_round: int,
                    draw_date: str, actual_set: set[int], verification: str,
                    trusted: bool, oos_state: Dict[str, object], result_path: Path) -> bool:
    graded = original(registry, latest_round, draw_date, actual_set, verification,
                      trusted, oos_state, result_path)
    if not graded:
        return False

    refs = registry.get("matched_reference_by_candidate")
    refs = refs if isinstance(refs, dict) else {}
    frozen_at = registry.get("matched_reference_frozen_at_jst")
    out_dir = result_path.parent
    champion_version = str(registry.get("champion_version", ""))
    evidence = oos_state.get("evidence") if isinstance(oos_state.get("evidence"), dict) else {}
    rows = []

    for item in registry.get("candidates", []) or []:
        if not isinstance(item, dict):
            continue
        version = str(item.get("version", ""))
        tickets = item.get("tickets") or []
        matched_tickets = refs.get(version) or []
        if not version or not tickets:
            continue
        rec = evidence.get(v4.e_key(version, champion_version), {}) if isinstance(evidence, dict) else {}
        if not isinstance(rec, dict):
            continue
        matched_valid = bool(matched_tickets) and bool(frozen_at) and geometry_preserved(tickets, matched_tickets)
        rec["strict_matched_valid"] = matched_valid
        rec["matched_reference_version"] = VERSION
        candidate_metrics = v4.score_tickets(tickets, actual_set)
        matched_metrics = v4.score_tickets(matched_tickets, actual_set) if matched_valid else None
        matched_delta = None
        if matched_metrics is not None:
            matched_delta = float(candidate_metrics["score"] - matched_metrics["score"])
            _update_matched_evidence(v4, rec, matched_delta, trusted)
            matched_raw = float(rec.get("matched_e_value_raw", 1.0) or 1.0)
        else:
            matched_raw = 0.0
        rec["matched_e_value_raw"] = matched_raw
        champion_raw = float(rec.get("champion_e_value_raw", 0.0) or 0.0)
        random_raw = float(rec.get("random_e_value_raw", 0.0) or 0.0)
        weight = float(rec.get("family_weight", registry.get("family_weight", 1.0)) or 1.0)
        adjusted = min(champion_raw, random_raw, matched_raw) * weight if matched_valid else 0.0
        rec["family_adjusted_e_value"] = adjusted
        rec["e_value"] = adjusted
        rec["e_value_semantics"] = "family_adjusted_min_champion_random_matched_permutation"
        if isinstance(evidence, dict):
            evidence[v4.e_key(version, champion_version)] = rec

        rows.append({
            "round": latest_round,
            "draw_date": draw_date,
            "candidate_version": version,
            "champion_version": champion_version,
            "formal_block_index": rec.get("formal_block_index", registry.get("formal_block_index", 1)),
            "candidate_score": f"{candidate_metrics['score']:.6f}",
            "matched_score": f"{matched_metrics['score']:.6f}" if matched_metrics else "",
            "delta_vs_matched": f"{matched_delta:.6f}" if matched_delta is not None else "",
            "candidate_max_hits": f"{candidate_metrics['max_hits']:.0f}",
            "matched_max_hits": f"{matched_metrics['max_hits']:.0f}" if matched_metrics else "",
            "matched_e_value_raw": f"{matched_raw:.8f}",
            "family_weight": f"{weight:.10f}",
            "family_adjusted_e_value": f"{adjusted:.8f}",
            "required_raw_e_value": f"{float(rec.get('required_raw_e_value', 0.0)):.8f}",
            "trusted_for_promotion": str(bool(trusted)).lower(),
            "source_verification": verification,
            "matched_reference_frozen_at_jst": frozen_at or "",
        })

    strict.append_csv(out_dir / "matched_oos_results.csv", rows, MATCHED_FIELDS)
    _grade_holdout_matched(v4, out_dir, latest_round, draw_date, actual_set, verification, trusted)
    oos_state["matched_reference_version"] = VERSION
    oos_state["promotion_intersection"] = "champion_and_uniform_random_and_matched_permutation"
    return True


def _promotion_candidates(v4, original, oos_state: Dict[str, object], champion_version: str):
    base = original(oos_state, champion_version)
    eligible = []
    for rank, rec in base:
        matched_draws = int(rec.get("matched_trusted_draws", 0) or 0)
        if matched_draws < v4.MIN_TRUSTED_OOS_DRAWS or not rec.get("strict_matched_valid"):
            continue
        mean_matched = float(rec.get("matched_sum_delta", 0.0) or 0.0) / max(1, matched_draws)
        win_matched = float(rec.get("matched_wins", 0) or 0) / max(1, matched_draws)
        if mean_matched < v4.MIN_MEAN_SCORE_DELTA or win_matched < v4.MIN_OOS_WIN_RATE:
            continue
        eligible.append((rank + min(0.25, max(-0.25, mean_matched)), rec))
    return sorted(eligible, key=lambda x: x[0], reverse=True)


def _promote_if_eligible(v4, original, *args, **kwargs):
    champion, promotion = original(*args, **kwargs)
    if not promotion:
        return champion, promotion
    champion_file = args[1] if len(args) > 1 else kwargs.get("champion_file")
    oos_state = args[2] if len(args) > 2 else kwargs.get("oos_state", {})
    candidate_version = str(promotion.get("to", ""))
    rec = None
    if isinstance(oos_state, dict):
        for item in (oos_state.get("evidence") or {}).values():
            if isinstance(item, dict) and item.get("candidate_version") == candidate_version:
                rec = item
                break
    if isinstance(rec, dict):
        draws = max(1, int(rec.get("matched_trusted_draws", 0) or 0))
        extra = {
            "matched_reference_version": VERSION,
            "matched_e_value_raw": float(rec.get("matched_e_value_raw", 0.0) or 0.0),
            "matched_mean_score_delta": float(rec.get("matched_sum_delta", 0.0) or 0.0) / draws,
            "matched_win_rate": float(rec.get("matched_wins", 0) or 0) / draws,
            "matched_reference": "pre_frozen_common_number_label_permutation",
            "promotion_intersection": "champion_and_uniform_random_and_matched_permutation",
        }
        promotion.update(extra)
        if champion_file:
            path = Path(champion_file)
            obj = strict.load_json(path, {})
            evidence = obj.get("promotion_evidence")
            if isinstance(evidence, dict):
                evidence.update(extra)
                obj["promotion_evidence"] = evidence
                strict.write_json(path, obj)
    return champion, promotion


def install(v4) -> None:
    if getattr(v4, "_matched_permutation_oos_installed", False):
        return
    if not getattr(v4, "_strict_oos_governance_installed", False):
        raise RuntimeError("strict_oos_governance.install(v4) must run first")
    original_freeze = v4.freeze_registry
    original_grade = v4.grade_registry
    original_candidates = v4.promotion_candidates
    original_promote = v4.promote_if_eligible

    def freeze_wrapper(path, target_round, base_data_sha, champion, champion_eval,
                       shadow_configs, eval_by_version, x, min_train, pool_size,
                       source_verification):
        registry = original_freeze(
            path, target_round, base_data_sha, champion, champion_eval,
            shadow_configs, eval_by_version, x, min_train, pool_size,
            source_verification,
        )
        refs = _build_reference_map(registry, target_round)
        registry["matched_reference_by_candidate"] = refs
        registry["matched_reference_method"] = "common_label_permutation_preserving_portfolio_geometry"
        registry["matched_reference_seed_policy"] = f"{SEED_BASE} + target_round * {SEED_MULTIPLIER}"
        registry["matched_reference_permutation"] = permutation_for_round(target_round)
        registry["matched_reference_frozen_at_jst"] = v4.now_jst()
        registry["matched_reference_version"] = VERSION
        v4.write_json(path, registry)
        return registry

    def grade_wrapper(registry, latest_round, draw_date, actual_set, verification,
                      trusted, oos_state, result_path):
        return _grade_registry(
            v4, original_grade, registry, latest_round, draw_date, actual_set,
            verification, trusted, oos_state, result_path,
        )

    def candidates_wrapper(oos_state, champion_version):
        return _promotion_candidates(v4, original_candidates, oos_state, champion_version)

    def promote_wrapper(*args, **kwargs):
        return _promote_if_eligible(v4, original_promote, *args, **kwargs)

    v4.freeze_registry = freeze_wrapper
    v4.grade_registry = grade_wrapper
    v4.promotion_candidates = candidates_wrapper
    v4.promote_if_eligible = promote_wrapper
    v4._matched_permutation_oos_installed = True


def bootstrap_before_main(v4, argv: Optional[Sequence[str]] = None) -> Dict[str, object]:
    args = strict._cli_context(argv)
    latest_round, _ = strict._latest_round(v4, args.csv)
    matched_ready = ensure_matched_reference(v4, args.shadow_registry, latest_round=latest_round)
    holdout_matched_ready = ensure_holdout_matched_reference(
        v4,
        args.out_dir / "future_holdout_registry.json",
        args.out_dir / "future_holdout_state.json",
        latest_round=latest_round,
    )
    oos_path = args.out_dir / "oos_candidate_state.json"
    oos = strict.load_json(oos_path, {})
    oos["matched_reference_version"] = VERSION
    oos["promotion_intersection"] = "champion_and_uniform_random_and_matched_permutation"
    strict.write_json(oos_path, oos)
    return {
        "latest_round": latest_round,
        "matched_ready": matched_ready,
        "holdout_matched_ready": holdout_matched_ready,
    }


def finalize_after_main(v4, argv: Optional[Sequence[str]] = None) -> Dict[str, object]:
    return bootstrap_before_main(v4, argv)
