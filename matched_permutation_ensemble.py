#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

import matched_permutation_oos as single
import strict_oos_governance as strict

VERSION = "matched-permutation-ensemble-v1"
ENSEMBLE_SIZE = 32
SEED_BASE = 31_000_000
SEED_MULTIPLIER = 1019

ENSEMBLE_FIELDS = [
    "round", "draw_date", "candidate_version", "champion_version", "formal_block_index",
    "candidate_score", "ensemble_mean_score", "ensemble_score_std", "delta_vs_matched_ensemble",
    "candidate_max_hits", "ensemble_mean_max_hits", "ensemble_size", "matched_ensemble_e_value_raw",
    "family_weight", "family_adjusted_e_value", "required_raw_e_value",
    "trusted_for_promotion", "source_verification", "matched_ensemble_frozen_at_jst",
]

HOLDOUT_ENSEMBLE_FIELDS = [
    "round", "draw_date", "holdout_version", "holdout_score",
    "ensemble_mean_score", "ensemble_score_std", "delta_vs_matched_ensemble",
    "holdout_max_hits", "ensemble_mean_max_hits", "ensemble_size", "matched_ensemble_e_value",
    "trusted", "source_verification", "frozen_at_jst",
]


def _normalize_permutation(obj: object) -> Optional[List[int]]:
    if not isinstance(obj, list) or len(obj) != 37:
        return None
    try:
        vals = [int(x) for x in obj]
    except Exception:
        return None
    return vals if sorted(vals) == list(range(1, 38)) else None


def permutations_for_round(target_round: int, size: int = ENSEMBLE_SIZE) -> List[List[int]]:
    """Deterministic matched-null permutations; member 0 preserves the v1 comparator."""
    n = max(1, int(size))
    permutations: List[List[int]] = [single.permutation_for_round(target_round)]
    seen = {tuple(permutations[0])}
    rng = np.random.default_rng(SEED_BASE + int(target_round) * SEED_MULTIPLIER)
    identity = tuple(range(1, 38))
    while len(permutations) < n:
        p = tuple(int(x) for x in rng.permutation(np.arange(1, 38)))
        if p == identity or p in seen:
            continue
        seen.add(p)
        permutations.append(list(p))
    return permutations


def permute_with_permutation(
    tickets: Iterable[Iterable[int]], permutation: Sequence[int]
) -> List[List[int]]:
    p = _normalize_permutation(list(permutation))
    if p is None:
        raise ValueError("invalid 1..37 permutation")
    mapping = {i + 1: p[i] for i in range(37)}
    return [sorted(mapping[int(n)] for n in ticket) for ticket in tickets]


def _ensemble_for_tickets(
    tickets: Iterable[Iterable[int]], permutations: Sequence[Sequence[int]]
) -> List[List[List[int]]]:
    original = [list(map(int, t)) for t in tickets]
    out: List[List[List[int]]] = []
    seen = set()
    for p in permutations:
        transformed = permute_with_permutation(original, p)
        if not single.geometry_preserved(original, transformed):
            raise RuntimeError("matched ensemble member changed portfolio geometry")
        key = tuple(tuple(t) for t in transformed)
        if key in seen:
            continue
        seen.add(key)
        out.append(transformed)
    if len(out) != len(permutations):
        raise RuntimeError("matched ensemble produced duplicate transformed portfolios")
    return out


def _reference_ready(
    registry: Dict[str, object],
    expected_versions: Sequence[str],
    key: str = "matched_ensemble_by_candidate",
) -> bool:
    refs = registry.get(key)
    if not isinstance(refs, dict):
        return False
    size = int(registry.get("matched_ensemble_size", 0) or 0)
    if size != ENSEMBLE_SIZE:
        return False
    for version in expected_versions:
        members = refs.get(version)
        if not isinstance(members, list) or len(members) != ENSEMBLE_SIZE:
            return False
    return bool(expected_versions and registry.get("matched_ensemble_frozen_at_jst"))


def _build_reference_map(
    registry: Dict[str, object], target_round: int
) -> Tuple[Dict[str, List[List[List[int]]]], List[List[int]]]:
    permutations = permutations_for_round(target_round)
    old_refs = registry.get("matched_reference_by_candidate")
    old_refs = old_refs if isinstance(old_refs, dict) else {}
    refs: Dict[str, List[List[List[int]]]] = {}
    for item in registry.get("candidates", []) or []:
        if not isinstance(item, dict):
            continue
        version = str(item.get("version", ""))
        tickets = item.get("tickets") or []
        if not version or not tickets:
            continue
        members = _ensemble_for_tickets(tickets, permutations)
        legacy = old_refs.get(version)
        if legacy and members[0] != legacy:
            raise RuntimeError("ensemble member 0 does not preserve the previously frozen matched reference")
        refs[version] = members
    return refs, permutations


def ensure_matched_ensemble_reference(
    v4, registry_path: Path, latest_round: Optional[int] = None
) -> bool:
    registry = strict.load_json(registry_path, {})
    if not registry:
        return False
    target_round = int(registry.get("target_round", -1))
    candidates = [
        x for x in (registry.get("candidates") or [])
        if isinstance(x, dict) and x.get("version") and x.get("tickets")
    ]
    expected = [str(x.get("version")) for x in candidates]
    ready = _reference_ready(registry, expected)

    # Never add or repair an ensemble after the target result is already known.
    if latest_round is not None and target_round <= int(latest_round):
        return ready
    if ready:
        return True
    if target_round < 1 or not expected:
        return False

    # The single comparator must already exist; member 0 is an immutable audit anchor.
    if not registry.get("matched_reference_frozen_at_jst"):
        return False
    old_refs = registry.get("matched_reference_by_candidate")
    if not isinstance(old_refs, dict) or not set(expected).issubset(set(old_refs.keys())):
        return False

    refs, permutations = _build_reference_map(registry, target_round)
    if set(refs) != set(expected):
        return False
    registry["matched_ensemble_by_candidate"] = refs
    registry["matched_ensemble_permutations"] = permutations
    registry["matched_ensemble_size"] = ENSEMBLE_SIZE
    registry["matched_ensemble_method"] = (
        "mean_score_of_prefrozen_common_label_permutations_preserving_portfolio_geometry"
    )
    registry["matched_ensemble_seed_policy"] = (
        "member0=matched-permutation-null-v1; "
        f"members1..31=default_rng({SEED_BASE} + target_round * {SEED_MULTIPLIER})"
    )
    registry["matched_ensemble_frozen_at_jst"] = v4.now_jst()
    registry["matched_ensemble_version"] = VERSION
    strict.write_json(registry_path, registry)
    return True


def ensure_holdout_matched_ensemble_reference(
    v4,
    registry_path: Path,
    state_path: Path,
    latest_round: Optional[int] = None,
) -> bool:
    registry = strict.load_json(registry_path, {})
    state = strict.load_json(state_path, {})
    if not registry or not state:
        return False
    target_round = int(registry.get("target_round", -1))
    tickets = registry.get("holdout_tickets") or []
    members = registry.get("matched_ensemble_tickets")
    ready = (
        isinstance(members, list)
        and len(members) == ENSEMBLE_SIZE
        and int(registry.get("matched_ensemble_size", 0) or 0) == ENSEMBLE_SIZE
        and bool(registry.get("matched_ensemble_frozen_at_jst"))
    )
    if latest_round is not None and target_round <= int(latest_round):
        return bool(ready)
    if ready:
        return True
    if target_round < 1 or not tickets:
        return False

    # Preserve the already frozen single matched holdout as member 0.
    legacy = registry.get("matched_reference_tickets") or []
    if not legacy or not registry.get("matched_reference_frozen_at_jst"):
        return False
    permutations = permutations_for_round(target_round)
    ensemble = _ensemble_for_tickets(tickets, permutations)
    if ensemble[0] != legacy:
        return False

    registry["matched_ensemble_tickets"] = ensemble
    registry["matched_ensemble_permutations"] = permutations
    registry["matched_ensemble_size"] = ENSEMBLE_SIZE
    registry["matched_ensemble_method"] = (
        "mean_score_of_prefrozen_common_label_permutations_preserving_holdout_geometry"
    )
    registry["matched_ensemble_seed_policy"] = (
        "member0=matched-permutation-null-v1; "
        f"members1..31=default_rng({SEED_BASE} + target_round * {SEED_MULTIPLIER})"
    )
    registry["matched_ensemble_frozen_at_jst"] = v4.now_jst()
    registry["matched_ensemble_version"] = VERSION
    strict.write_json(registry_path, registry)

    state.setdefault("matched_ensemble_trusted_draws", 0)
    state.setdefault("sum_delta_vs_matched_ensemble", 0.0)
    state.setdefault("wins_vs_matched_ensemble", 0)
    state.setdefault("matched_ensemble_e_components", {str(l): 1.0 for l in v4.E_LAMBDAS})
    state.setdefault("matched_ensemble_e_value", 1.0)
    state.setdefault("matched_ensemble_graded_rounds", [])
    state["matched_ensemble_size"] = ENSEMBLE_SIZE
    state["matched_ensemble_version"] = VERSION
    strict.write_json(state_path, state)
    return True


def _score_ensemble(v4, members: Sequence[Sequence[Sequence[int]]], actual_set: set[int]) -> Dict[str, float]:
    metrics = [v4.score_tickets(member, actual_set) for member in members]
    scores = np.asarray([float(m["score"]) for m in metrics], dtype=float)
    max_hits = np.asarray([float(m["max_hits"]) for m in metrics], dtype=float)
    return {
        "mean_score": float(np.mean(scores)),
        "score_std": float(np.std(scores, ddof=0)),
        "min_score": float(np.min(scores)),
        "max_score": float(np.max(scores)),
        "mean_max_hits": float(np.mean(max_hits)),
    }


def _update_ensemble_evidence(v4, rec: Dict[str, object], delta: float, trusted: bool) -> None:
    if not trusted:
        return
    rec["matched_ensemble_trusted_draws"] = int(rec.get("matched_ensemble_trusted_draws", 0) or 0) + 1
    rec["matched_ensemble_sum_delta"] = float(rec.get("matched_ensemble_sum_delta", 0.0) or 0.0) + float(delta)
    if delta > 0:
        rec["matched_ensemble_wins"] = int(rec.get("matched_ensemble_wins", 0) or 0) + 1
    normalized = max(-1.0, min(1.0, float(delta) / float(v4.MAX_PORTFOLIO_SCORE)))
    comps = strict.update_e_components(rec.get("matched_ensemble_e_components"), normalized, v4.E_LAMBDAS)
    rec["matched_ensemble_e_components"] = comps
    rec["matched_ensemble_e_value_raw"] = strict.e_value_from_components(comps, v4.E_LAMBDAS)


def _grade_holdout_ensemble(
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
    graded = state.setdefault("matched_ensemble_graded_rounds", [])
    if latest_round in graded:
        return
    holdout_tickets = registry.get("holdout_tickets") or []
    members = registry.get("matched_ensemble_tickets")
    valid = (
        bool(holdout_tickets)
        and isinstance(members, list)
        and len(members) == ENSEMBLE_SIZE
        and bool(registry.get("matched_ensemble_frozen_at_jst"))
        and all(single.geometry_preserved(holdout_tickets, m) for m in members)
    )
    if not valid:
        state["status"] = "invalid_missing_prefrozen_matched_ensemble"
        strict.write_json(state_path, state)
        return

    hm = v4.score_tickets(holdout_tickets, actual_set)
    em = _score_ensemble(v4, members, actual_set)
    delta = float(hm["score"] - em["mean_score"])
    if trusted:
        state["matched_ensemble_trusted_draws"] = int(state.get("matched_ensemble_trusted_draws", 0) or 0) + 1
        state["sum_delta_vs_matched_ensemble"] = (
            float(state.get("sum_delta_vs_matched_ensemble", 0.0) or 0.0) + delta
        )
        if delta > 0:
            state["wins_vs_matched_ensemble"] = int(state.get("wins_vs_matched_ensemble", 0) or 0) + 1
        normalized = max(-1.0, min(1.0, delta / float(v4.MAX_PORTFOLIO_SCORE)))
        comps = strict.update_e_components(
            state.get("matched_ensemble_e_components"), normalized, v4.E_LAMBDAS
        )
        state["matched_ensemble_e_components"] = comps
        state["matched_ensemble_e_value"] = strict.e_value_from_components(comps, v4.E_LAMBDAS)

    graded.append(latest_round)
    state["matched_ensemble_size"] = ENSEMBLE_SIZE
    state["matched_ensemble_version"] = VERSION
    strict.write_json(state_path, state)
    strict.append_csv(out_dir / "future_holdout_matched_ensemble_results.csv", [{
        "round": latest_round,
        "draw_date": draw_date,
        "holdout_version": state.get("locked_candidate_version", ""),
        "holdout_score": f"{hm['score']:.6f}",
        "ensemble_mean_score": f"{em['mean_score']:.6f}",
        "ensemble_score_std": f"{em['score_std']:.6f}",
        "delta_vs_matched_ensemble": f"{delta:.6f}",
        "holdout_max_hits": f"{hm['max_hits']:.0f}",
        "ensemble_mean_max_hits": f"{em['mean_max_hits']:.6f}",
        "ensemble_size": ENSEMBLE_SIZE,
        "matched_ensemble_e_value": f"{float(state.get('matched_ensemble_e_value', 1.0)):.8f}",
        "trusted": str(bool(trusted)).lower(),
        "source_verification": verification,
        "frozen_at_jst": registry.get("matched_ensemble_frozen_at_jst", ""),
    }], HOLDOUT_ENSEMBLE_FIELDS)


def _grade_registry(
    v4,
    original,
    registry: Dict[str, object],
    latest_round: int,
    draw_date: str,
    actual_set: set[int],
    verification: str,
    trusted: bool,
    oos_state: Dict[str, object],
    result_path: Path,
) -> bool:
    graded = original(
        registry, latest_round, draw_date, actual_set, verification,
        trusted, oos_state, result_path,
    )
    if not graded:
        return False

    refs = registry.get("matched_ensemble_by_candidate")
    refs = refs if isinstance(refs, dict) else {}
    frozen_at = registry.get("matched_ensemble_frozen_at_jst")
    out_dir = result_path.parent
    champion_version = str(registry.get("champion_version", ""))
    evidence = oos_state.get("evidence") if isinstance(oos_state.get("evidence"), dict) else {}
    rows = []

    for item in registry.get("candidates", []) or []:
        if not isinstance(item, dict):
            continue
        version = str(item.get("version", ""))
        tickets = item.get("tickets") or []
        members = refs.get(version)
        if not version or not tickets:
            continue
        rec = evidence.get(v4.e_key(version, champion_version), {}) if isinstance(evidence, dict) else {}
        if not isinstance(rec, dict):
            continue

        valid = (
            isinstance(members, list)
            and len(members) == ENSEMBLE_SIZE
            and bool(frozen_at)
            and all(single.geometry_preserved(tickets, m) for m in members)
        )
        rec["strict_matched_ensemble_valid"] = bool(valid)
        rec["matched_ensemble_version"] = VERSION
        rec["matched_ensemble_size"] = ENSEMBLE_SIZE

        candidate_metrics = v4.score_tickets(tickets, actual_set)
        ensemble_metrics = _score_ensemble(v4, members, actual_set) if valid else None
        delta = None
        if ensemble_metrics is not None:
            delta = float(candidate_metrics["score"] - ensemble_metrics["mean_score"])
            _update_ensemble_evidence(v4, rec, delta, trusted)
            ensemble_raw = float(rec.get("matched_ensemble_e_value_raw", 1.0) or 1.0)
        else:
            ensemble_raw = 0.0
        rec["matched_ensemble_e_value_raw"] = ensemble_raw

        champion_raw = float(rec.get("champion_e_value_raw", 0.0) or 0.0)
        random_raw = float(rec.get("random_e_value_raw", 0.0) or 0.0)
        weight = float(rec.get("family_weight", registry.get("family_weight", 1.0)) or 1.0)
        adjusted = min(champion_raw, random_raw, ensemble_raw) * weight if valid else 0.0
        rec["family_adjusted_e_value"] = adjusted
        rec["e_value"] = adjusted
        rec["e_value_semantics"] = "family_adjusted_min_champion_random_matched_ensemble32"
        if isinstance(evidence, dict):
            evidence[v4.e_key(version, champion_version)] = rec

        rows.append({
            "round": latest_round,
            "draw_date": draw_date,
            "candidate_version": version,
            "champion_version": champion_version,
            "formal_block_index": rec.get("formal_block_index", registry.get("formal_block_index", 1)),
            "candidate_score": f"{candidate_metrics['score']:.6f}",
            "ensemble_mean_score": f"{ensemble_metrics['mean_score']:.6f}" if ensemble_metrics else "",
            "ensemble_score_std": f"{ensemble_metrics['score_std']:.6f}" if ensemble_metrics else "",
            "delta_vs_matched_ensemble": f"{delta:.6f}" if delta is not None else "",
            "candidate_max_hits": f"{candidate_metrics['max_hits']:.0f}",
            "ensemble_mean_max_hits": f"{ensemble_metrics['mean_max_hits']:.6f}" if ensemble_metrics else "",
            "ensemble_size": ENSEMBLE_SIZE,
            "matched_ensemble_e_value_raw": f"{ensemble_raw:.8f}",
            "family_weight": f"{weight:.10f}",
            "family_adjusted_e_value": f"{adjusted:.8f}",
            "required_raw_e_value": f"{float(rec.get('required_raw_e_value', 0.0)):.8f}",
            "trusted_for_promotion": str(bool(trusted)).lower(),
            "source_verification": verification,
            "matched_ensemble_frozen_at_jst": frozen_at or "",
        })

    strict.append_csv(out_dir / "matched_ensemble_oos_results.csv", rows, ENSEMBLE_FIELDS)
    _grade_holdout_ensemble(v4, out_dir, latest_round, draw_date, actual_set, verification, trusted)
    oos_state["matched_ensemble_version"] = VERSION
    oos_state["matched_ensemble_size"] = ENSEMBLE_SIZE
    oos_state["promotion_intersection"] = "champion_and_uniform_random_and_matched_ensemble32"
    return True


def promotion_candidates(v4, oos_state: Dict[str, object], champion_version: str):
    # Start from the strict Champion + Uniform Random gate. The legacy single-matched
    # comparator remains telemetry/audit only once the 32-member ensemble is frozen.
    base = strict.strict_promotion_candidates(v4, oos_state, champion_version)
    eligible = []
    for rank, rec in base:
        draws = int(rec.get("matched_ensemble_trusted_draws", 0) or 0)
        if draws < v4.MIN_TRUSTED_OOS_DRAWS or not rec.get("strict_matched_ensemble_valid"):
            continue
        mean_delta = float(rec.get("matched_ensemble_sum_delta", 0.0) or 0.0) / max(1, draws)
        win_rate = float(rec.get("matched_ensemble_wins", 0) or 0) / max(1, draws)
        if mean_delta < v4.MIN_MEAN_SCORE_DELTA or win_rate < v4.MIN_OOS_WIN_RATE:
            continue
        adjusted = float(rec.get("family_adjusted_e_value", 0.0) or 0.0)
        if adjusted < v4.E_VALUE_THRESHOLD:
            continue
        rank2 = math.log(max(adjusted, 1.0)) + min(
            float(rec.get("sum_delta", 0.0) or 0.0) / max(1, int(rec.get("trusted_draws", 0) or 0)),
            float(rec.get("random_sum_delta", 0.0) or 0.0) / max(1, int(rec.get("random_trusted_draws", 0) or 0)),
            mean_delta,
        ) + 0.25 * min(
            float(rec.get("wins", 0) or 0) / max(1, int(rec.get("trusted_draws", 0) or 0)),
            float(rec.get("random_wins", 0) or 0) / max(1, int(rec.get("random_trusted_draws", 0) or 0)),
            win_rate,
        )
        eligible.append((rank2, rec))
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
        draws = max(1, int(rec.get("matched_ensemble_trusted_draws", 0) or 0))
        extra = {
            "matched_ensemble_version": VERSION,
            "matched_ensemble_size": ENSEMBLE_SIZE,
            "matched_ensemble_e_value_raw": float(rec.get("matched_ensemble_e_value_raw", 0.0) or 0.0),
            "matched_ensemble_mean_score_delta": (
                float(rec.get("matched_ensemble_sum_delta", 0.0) or 0.0) / draws
            ),
            "matched_ensemble_win_rate": float(rec.get("matched_ensemble_wins", 0) or 0) / draws,
            "matched_ensemble_reference": "32_prefrozen_geometry_preserving_label_permutations",
            "promotion_intersection": "champion_and_uniform_random_and_matched_ensemble32",
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
    if getattr(v4, "_matched_permutation_ensemble_installed", False):
        return
    if not getattr(v4, "_matched_permutation_oos_installed", False):
        raise RuntimeError("matched_permutation_oos.install(v4) must run first")
    original_freeze = v4.freeze_registry
    original_grade = v4.grade_registry
    original_promote = v4.promote_if_eligible

    def freeze_wrapper(path, target_round, base_data_sha, champion, champion_eval,
                       shadow_configs, eval_by_version, x, min_train, pool_size,
                       source_verification):
        registry = original_freeze(
            path, target_round, base_data_sha, champion, champion_eval,
            shadow_configs, eval_by_version, x, min_train, pool_size,
            source_verification,
        )
        refs, permutations = _build_reference_map(registry, target_round)
        registry["matched_ensemble_by_candidate"] = refs
        registry["matched_ensemble_permutations"] = permutations
        registry["matched_ensemble_size"] = ENSEMBLE_SIZE
        registry["matched_ensemble_method"] = (
            "mean_score_of_prefrozen_common_label_permutations_preserving_portfolio_geometry"
        )
        registry["matched_ensemble_seed_policy"] = (
            "member0=matched-permutation-null-v1; "
            f"members1..31=default_rng({SEED_BASE} + target_round * {SEED_MULTIPLIER})"
        )
        registry["matched_ensemble_frozen_at_jst"] = v4.now_jst()
        registry["matched_ensemble_version"] = VERSION
        v4.write_json(path, registry)
        return registry

    def grade_wrapper(registry, latest_round, draw_date, actual_set, verification,
                      trusted, oos_state, result_path):
        return _grade_registry(
            v4, original_grade, registry, latest_round, draw_date, actual_set,
            verification, trusted, oos_state, result_path,
        )

    def candidates_wrapper(oos_state, champion_version):
        return promotion_candidates(v4, oos_state, champion_version)

    def promote_wrapper(*args, **kwargs):
        return _promote_if_eligible(v4, original_promote, *args, **kwargs)

    v4.freeze_registry = freeze_wrapper
    v4.grade_registry = grade_wrapper
    v4.promotion_candidates = candidates_wrapper
    v4.promote_if_eligible = promote_wrapper
    v4._matched_permutation_ensemble_installed = True


def bootstrap_before_main(v4, argv: Optional[Sequence[str]] = None) -> Dict[str, object]:
    args = strict._cli_context(argv)
    latest_round, _ = strict._latest_round(v4, args.csv)
    ready = ensure_matched_ensemble_reference(
        v4, args.shadow_registry, latest_round=latest_round
    )
    holdout_ready = ensure_holdout_matched_ensemble_reference(
        v4,
        args.out_dir / "future_holdout_registry.json",
        args.out_dir / "future_holdout_state.json",
        latest_round=latest_round,
    )
    oos_path = args.out_dir / "oos_candidate_state.json"
    oos = strict.load_json(oos_path, {})
    oos["matched_ensemble_version"] = VERSION
    oos["matched_ensemble_size"] = ENSEMBLE_SIZE
    oos["promotion_intersection"] = "champion_and_uniform_random_and_matched_ensemble32"
    strict.write_json(oos_path, oos)
    return {
        "latest_round": latest_round,
        "matched_ensemble_ready": ready,
        "holdout_matched_ensemble_ready": holdout_ready,
        "matched_ensemble_size": ENSEMBLE_SIZE,
    }


def finalize_after_main(v4, argv: Optional[Sequence[str]] = None) -> Dict[str, object]:
    return bootstrap_before_main(v4, argv)
