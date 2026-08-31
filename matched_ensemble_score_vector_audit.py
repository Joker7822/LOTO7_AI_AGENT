#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

import matched_ensemble_rank_diagnostics as rank
import matched_permutation_ensemble as ensemble
import matched_permutation_oos as single
import strict_oos_governance as strict

VERSION = "matched-ensemble-score-vector-audit-v1"
CANONICAL_FLOAT_FORMAT = ".17g"
HASH_ALGORITHM = "sha256"
PROMOTION_ROLE = "diagnostic_only"

AUDIT_FIELDS = [
    "round", "draw_date", "candidate_version", "champion_version",
    "candidate_score_canonical", "ensemble_size", "null_score_vector_json",
    "null_score_vector_sha256", "matched_ensemble_reference_sha256",
    "audit_record_sha256", "ensemble_mean_score_recomputed",
    "percentile_midrank_recomputed", "permutation_p_upper_recomputed",
    "replay_verified", "trusted", "source_verification",
    "matched_ensemble_frozen_at_jst", "audit_version",
]

HOLDOUT_AUDIT_FIELDS = [
    "round", "draw_date", "holdout_version", "holdout_score_canonical",
    "ensemble_size", "null_score_vector_json", "null_score_vector_sha256",
    "matched_ensemble_reference_sha256", "audit_record_sha256",
    "ensemble_mean_score_recomputed", "percentile_midrank_recomputed",
    "permutation_p_upper_recomputed", "replay_verified", "trusted",
    "source_verification", "matched_ensemble_frozen_at_jst", "audit_version",
]


def _canonical_json(obj: object) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical_score(value: float) -> str:
    """Round-trip-safe binary64 decimal representation."""
    return format(float(value), CANONICAL_FLOAT_FORMAT)


def canonical_score_vector(scores: Iterable[float]) -> List[str]:
    return [canonical_score(x) for x in scores]


def score_vector_json(scores: Iterable[float]) -> str:
    return _canonical_json(canonical_score_vector(scores))


def score_vector_sha256(scores: Iterable[float]) -> str:
    return _sha256_text(score_vector_json(scores))


def _normalize_member(member: Sequence[Sequence[int]]) -> List[List[int]]:
    return [sorted(int(n) for n in ticket) for ticket in member]


def reference_sha256(members: Sequence[Sequence[Sequence[int]]]) -> str:
    """Hash the exact ensemble member order and ticket contents."""
    normalized = [_normalize_member(member) for member in members]
    return _sha256_text(_canonical_json(normalized))


def _audit_record_sha256(
    *,
    round_no: int,
    subject_version: str,
    subject_score: str,
    vector_sha: str,
    reference_sha: str,
    frozen_at: str,
) -> str:
    payload = {
        "audit_version": VERSION,
        "ensemble_size": ensemble.ENSEMBLE_SIZE,
        "matched_ensemble_frozen_at_jst": str(frozen_at),
        "matched_ensemble_reference_sha256": str(reference_sha),
        "null_score_vector_sha256": str(vector_sha),
        "round": int(round_no),
        "subject_score_canonical": str(subject_score),
        "subject_version": str(subject_version),
    }
    return _sha256_text(_canonical_json(payload))


def _valid_members(tickets, members, frozen_at) -> bool:
    return (
        bool(tickets)
        and isinstance(members, list)
        and len(members) == ensemble.ENSEMBLE_SIZE
        and bool(frozen_at)
        and all(single.geometry_preserved(tickets, member) for member in members)
    )


def _member_scores(v4, members: Sequence[Sequence[Sequence[int]]], actual_set: set[int]) -> List[float]:
    return [float(v4.score_tickets(member, actual_set)["score"]) for member in members]


def _replay_metrics(candidate_score: float, null_scores: Sequence[float]) -> Dict[str, float]:
    canonical_vector = canonical_score_vector(null_scores)
    replay_scores = [float(x) for x in canonical_vector]
    replay_candidate = float(canonical_score(candidate_score))
    diag = rank.rank_diagnostics(replay_candidate, replay_scores)
    return {
        "mean_score": sum(replay_scores) / len(replay_scores),
        "percentile_midrank": float(diag["percentile_midrank"]),
        "permutation_p_upper": float(diag["permutation_p_upper"]),
    }


def _matches_rank_state(state: Dict[str, object], replay: Dict[str, float], prefix: str) -> bool:
    p = state.get(f"last_{prefix}_percentile_midrank")
    q = state.get(f"last_{prefix}_permutation_p_upper")
    if p is None or q is None:
        return True
    return (
        abs(float(p) - float(replay["percentile_midrank"])) <= 1e-12
        and abs(float(q) - float(replay["permutation_p_upper"])) <= 1e-12
    )


def _store_registry_reference_hashes(registry: Dict[str, object]) -> bool:
    refs = registry.get("matched_ensemble_by_candidate")
    refs = refs if isinstance(refs, dict) else {}
    candidates = [
        x for x in (registry.get("candidates") or [])
        if isinstance(x, dict) and x.get("version") and x.get("tickets")
    ]
    expected = [str(x["version"]) for x in candidates]
    if not expected:
        return False
    frozen_at = registry.get("matched_ensemble_frozen_at_jst")
    if not frozen_at:
        return False
    hashes: Dict[str, str] = {}
    for item in candidates:
        version = str(item["version"])
        tickets = item.get("tickets") or []
        members = refs.get(version)
        if not _valid_members(tickets, members, frozen_at):
            return False
        hashes[version] = reference_sha256(members)
    registry["matched_ensemble_reference_sha256_by_candidate"] = hashes
    registry["matched_ensemble_score_vector_audit_version"] = VERSION
    registry["matched_ensemble_score_vector_hash_algorithm"] = HASH_ALGORITHM
    registry["matched_ensemble_score_vector_canonical_float"] = CANONICAL_FLOAT_FORMAT
    registry["matched_ensemble_score_vector_audit_promotion_role"] = PROMOTION_ROLE
    return set(hashes) == set(expected)


def ensure_registry_reference_hashes(v4, registry_path: Path) -> bool:
    registry = strict.load_json(registry_path, {})
    if not registry:
        return False
    before = _canonical_json(registry)
    ready = _store_registry_reference_hashes(registry)
    if ready and _canonical_json(registry) != before:
        strict.write_json(registry_path, registry)
    return ready


def ensure_holdout_reference_hash(v4, registry_path: Path, state_path: Path) -> bool:
    registry = strict.load_json(registry_path, {})
    state = strict.load_json(state_path, {})
    if not registry or not state:
        return False
    tickets = registry.get("holdout_tickets") or []
    members = registry.get("matched_ensemble_tickets")
    frozen_at = registry.get("matched_ensemble_frozen_at_jst")
    if not _valid_members(tickets, members, frozen_at):
        return False
    ref_hash = reference_sha256(members)
    registry["matched_ensemble_reference_sha256"] = ref_hash
    registry["matched_ensemble_score_vector_audit_version"] = VERSION
    registry["matched_ensemble_score_vector_hash_algorithm"] = HASH_ALGORITHM
    registry["matched_ensemble_score_vector_canonical_float"] = CANONICAL_FLOAT_FORMAT
    registry["matched_ensemble_score_vector_audit_promotion_role"] = PROMOTION_ROLE
    strict.write_json(registry_path, registry)

    state["matched_ensemble_score_vector_audit_version"] = VERSION
    state["matched_ensemble_score_vector_hash_algorithm"] = HASH_ALGORITHM
    state["matched_ensemble_score_vector_canonical_float"] = CANONICAL_FLOAT_FORMAT
    state["matched_ensemble_score_vector_audit_status"] = "active"
    state["matched_ensemble_score_vector_audit_promotion_role"] = PROMOTION_ROLE
    strict.write_json(state_path, state)
    return True


def _grade_holdout_audit(
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
    graded = state.setdefault("matched_ensemble_score_vector_audit_graded_rounds", [])
    if latest_round in graded:
        return

    tickets = registry.get("holdout_tickets") or []
    members = registry.get("matched_ensemble_tickets")
    frozen_at = str(registry.get("matched_ensemble_frozen_at_jst") or "")
    expected_ref = str(registry.get("matched_ensemble_reference_sha256") or "")
    if not _valid_members(tickets, members, frozen_at) or not expected_ref:
        state["matched_ensemble_score_vector_audit_status"] = "invalid_missing_prefrozen_reference_hash"
        strict.write_json(state_path, state)
        return
    actual_ref = reference_sha256(members)
    if actual_ref != expected_ref:
        state["matched_ensemble_score_vector_audit_status"] = "invalid_reference_hash_mismatch"
        strict.write_json(state_path, state)
        return

    observed = float(v4.score_tickets(tickets, actual_set)["score"])
    null_scores = _member_scores(v4, members, actual_set)
    vector_json = score_vector_json(null_scores)
    vector_sha = _sha256_text(vector_json)
    replay = _replay_metrics(observed, null_scores)
    replay_verified = _matches_rank_state(state, replay, "matched_ensemble_rank")
    record_sha = _audit_record_sha256(
        round_no=latest_round,
        subject_version=str(state.get("locked_candidate_version", "")),
        subject_score=canonical_score(observed),
        vector_sha=vector_sha,
        reference_sha=actual_ref,
        frozen_at=frozen_at,
    )

    state["last_matched_ensemble_score_vector_audit_round"] = latest_round
    state["last_matched_ensemble_score_vector_sha256"] = vector_sha
    state["last_matched_ensemble_audit_record_sha256"] = record_sha
    state["last_matched_ensemble_reference_sha256"] = actual_ref
    state["last_matched_ensemble_score_vector_replay_verified"] = bool(replay_verified)
    state["matched_ensemble_score_vector_audit_status"] = "active" if replay_verified else "invalid_replay_mismatch"
    if trusted:
        state["matched_ensemble_score_vector_audit_trusted_draws"] = int(
            state.get("matched_ensemble_score_vector_audit_trusted_draws", 0) or 0
        ) + 1
    graded.append(latest_round)
    strict.write_json(state_path, state)

    strict.append_csv(out_dir / "future_holdout_matched_ensemble_score_vector_audit.csv", [{
        "round": latest_round,
        "draw_date": draw_date,
        "holdout_version": state.get("locked_candidate_version", ""),
        "holdout_score_canonical": canonical_score(observed),
        "ensemble_size": ensemble.ENSEMBLE_SIZE,
        "null_score_vector_json": vector_json,
        "null_score_vector_sha256": vector_sha,
        "matched_ensemble_reference_sha256": actual_ref,
        "audit_record_sha256": record_sha,
        "ensemble_mean_score_recomputed": canonical_score(replay["mean_score"]),
        "percentile_midrank_recomputed": f"{replay['percentile_midrank']:.12f}",
        "permutation_p_upper_recomputed": f"{replay['permutation_p_upper']:.12f}",
        "replay_verified": str(bool(replay_verified)).lower(),
        "trusted": str(bool(trusted)).lower(),
        "source_verification": verification,
        "matched_ensemble_frozen_at_jst": frozen_at,
        "audit_version": VERSION,
    }], HOLDOUT_AUDIT_FIELDS)


def _grade_audit(
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
    ref_hashes = registry.get("matched_ensemble_reference_sha256_by_candidate")
    ref_hashes = ref_hashes if isinstance(ref_hashes, dict) else {}
    frozen_at = str(registry.get("matched_ensemble_frozen_at_jst") or "")
    champion_version = str(registry.get("champion_version", ""))
    evidence = oos_state.get("evidence") if isinstance(oos_state.get("evidence"), dict) else {}
    rows = []

    for item in registry.get("candidates", []) or []:
        if not isinstance(item, dict):
            continue
        version = str(item.get("version", ""))
        tickets = item.get("tickets") or []
        members = refs.get(version)
        expected_ref = str(ref_hashes.get(version) or "")
        if not version or not _valid_members(tickets, members, frozen_at) or not expected_ref:
            continue
        actual_ref = reference_sha256(members)
        rec = evidence.get(v4.e_key(version, champion_version), {}) if isinstance(evidence, dict) else {}
        if not isinstance(rec, dict):
            continue
        rec["matched_ensemble_score_vector_audit_version"] = VERSION
        if actual_ref != expected_ref:
            rec["matched_ensemble_score_vector_audit_status"] = "invalid_reference_hash_mismatch"
            if isinstance(evidence, dict):
                evidence[v4.e_key(version, champion_version)] = rec
            continue

        observed = float(v4.score_tickets(tickets, actual_set)["score"])
        null_scores = _member_scores(v4, members, actual_set)
        vector_json = score_vector_json(null_scores)
        vector_sha = _sha256_text(vector_json)
        replay = _replay_metrics(observed, null_scores)
        replay_verified = _matches_rank_state(rec, replay, "matched_ensemble_rank")
        record_sha = _audit_record_sha256(
            round_no=latest_round,
            subject_version=version,
            subject_score=canonical_score(observed),
            vector_sha=vector_sha,
            reference_sha=actual_ref,
            frozen_at=frozen_at,
        )
        rec["last_matched_ensemble_score_vector_audit_round"] = latest_round
        rec["last_matched_ensemble_score_vector_sha256"] = vector_sha
        rec["last_matched_ensemble_audit_record_sha256"] = record_sha
        rec["last_matched_ensemble_reference_sha256"] = actual_ref
        rec["last_matched_ensemble_score_vector_replay_verified"] = bool(replay_verified)
        rec["matched_ensemble_score_vector_audit_status"] = "active" if replay_verified else "invalid_replay_mismatch"
        if trusted:
            rec["matched_ensemble_score_vector_audit_trusted_draws"] = int(
                rec.get("matched_ensemble_score_vector_audit_trusted_draws", 0) or 0
            ) + 1
        if isinstance(evidence, dict):
            evidence[v4.e_key(version, champion_version)] = rec

        rows.append({
            "round": latest_round,
            "draw_date": draw_date,
            "candidate_version": version,
            "champion_version": champion_version,
            "candidate_score_canonical": canonical_score(observed),
            "ensemble_size": ensemble.ENSEMBLE_SIZE,
            "null_score_vector_json": vector_json,
            "null_score_vector_sha256": vector_sha,
            "matched_ensemble_reference_sha256": actual_ref,
            "audit_record_sha256": record_sha,
            "ensemble_mean_score_recomputed": canonical_score(replay["mean_score"]),
            "percentile_midrank_recomputed": f"{replay['percentile_midrank']:.12f}",
            "permutation_p_upper_recomputed": f"{replay['permutation_p_upper']:.12f}",
            "replay_verified": str(bool(replay_verified)).lower(),
            "trusted": str(bool(trusted)).lower(),
            "source_verification": verification,
            "matched_ensemble_frozen_at_jst": frozen_at,
            "audit_version": VERSION,
        })

    strict.append_csv(result_path.parent / "matched_ensemble_score_vector_audit.csv", rows, AUDIT_FIELDS)
    _grade_holdout_audit(v4, result_path.parent, latest_round, draw_date, actual_set, verification, trusted)
    oos_state["matched_ensemble_score_vector_audit_version"] = VERSION
    oos_state["matched_ensemble_score_vector_hash_algorithm"] = HASH_ALGORITHM
    oos_state["matched_ensemble_score_vector_canonical_float"] = CANONICAL_FLOAT_FORMAT
    oos_state["matched_ensemble_score_vector_audit_promotion_role"] = PROMOTION_ROLE


def install(v4) -> None:
    if getattr(v4, "_matched_ensemble_score_vector_audit_installed", False):
        return
    if not getattr(v4, "_matched_ensemble_rank_diagnostics_installed", False):
        raise RuntimeError("matched_ensemble_rank_diagnostics.install(v4) must run first")
    original_freeze = v4.freeze_registry
    original_grade = v4.grade_registry

    def freeze_wrapper(path, target_round, base_data_sha, champion, champion_eval,
                       shadow_configs, eval_by_version, x, min_train, pool_size,
                       source_verification):
        registry = original_freeze(
            path, target_round, base_data_sha, champion, champion_eval,
            shadow_configs, eval_by_version, x, min_train, pool_size,
            source_verification,
        )
        if not _store_registry_reference_hashes(registry):
            raise RuntimeError("could not precommit matched ensemble reference hashes")
        v4.write_json(path, registry)
        return registry

    def grade_wrapper(registry, latest_round, draw_date, actual_set, verification,
                      trusted, oos_state, result_path):
        graded = original_grade(
            registry, latest_round, draw_date, actual_set, verification,
            trusted, oos_state, result_path,
        )
        if not graded:
            return False
        _grade_audit(
            v4, registry, latest_round, draw_date, actual_set, verification,
            trusted, oos_state, result_path,
        )
        return True

    v4.freeze_registry = freeze_wrapper
    v4.grade_registry = grade_wrapper
    v4._matched_ensemble_score_vector_audit_installed = True


def bootstrap_before_main(v4, argv: Optional[Sequence[str]] = None) -> Dict[str, object]:
    args = strict._cli_context(argv)
    registry_ready = ensure_registry_reference_hashes(v4, args.shadow_registry)
    holdout_ready = ensure_holdout_reference_hash(
        v4,
        args.out_dir / "future_holdout_registry.json",
        args.out_dir / "future_holdout_state.json",
    )
    oos_path = args.out_dir / "oos_candidate_state.json"
    oos = strict.load_json(oos_path, {})
    oos["matched_ensemble_score_vector_audit_version"] = VERSION
    oos["matched_ensemble_score_vector_hash_algorithm"] = HASH_ALGORITHM
    oos["matched_ensemble_score_vector_canonical_float"] = CANONICAL_FLOAT_FORMAT
    oos["matched_ensemble_score_vector_audit_status"] = "active" if registry_ready else "waiting_for_prefrozen_reference_hash"
    oos["matched_ensemble_score_vector_audit_promotion_role"] = PROMOTION_ROLE
    strict.write_json(oos_path, oos)
    return {
        "version": VERSION,
        "registry_reference_hash_ready": bool(registry_ready),
        "holdout_reference_hash_ready": bool(holdout_ready),
        "hash_algorithm": HASH_ALGORITHM,
        "canonical_float": CANONICAL_FLOAT_FORMAT,
        "promotion_role": PROMOTION_ROLE,
    }


def finalize_after_main(v4, argv: Optional[Sequence[str]] = None) -> Dict[str, object]:
    return bootstrap_before_main(v4, argv)
