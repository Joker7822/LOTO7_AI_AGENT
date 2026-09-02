#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

import loto7_v2_runner as v2
import loto7_v4_runner as v4
import separated_optimizer as so
from loto7_evolving_agent import N_NUMBERS, PICKS, expert_probabilities, fingerprint_file, make_history, read_csv_flexible

VERSION = "signal-expert-attribution-oos-v1"
HORIZON_TRUSTED_DRAWS = 26
MIN_TRAIN = 100
CANONICAL_FLOAT_FORMAT = ".17g"
HASH_ALGORITHM = "sha256"
PROMOTION_ROLE = "diagnostic_only"
CLAIM_POLICY = "descriptive_attribution_only_no_expert_selection_or_weight_change_within_fixed_26_draw_horizon"

REGISTRY_NAME = "signal_expert_attribution_registry.json"
STATE_NAME = "signal_expert_attribution_state.json"
RESULTS_NAME = "signal_expert_attribution_results.csv"
SUMMARY_NAME = "signal_expert_attribution_summary.csv"
FREEZE_HISTORY_NAME = "signal_expert_attribution_freeze_history.jsonl"
REPORT_NAME = "signal_expert_attribution_report.md"
CALIBRATION_REGISTRY_NAME = "champion_calibration_oos_registry.json"

RESULT_FIELDS = [
    "round", "draw_date", "expert", "effective_weight",
    "standalone_top7_hits", "standalone_actual_mass", "standalone_log_score", "standalone_brier",
    "standalone_mass_edge_vs_uniform", "standalone_log_edge_vs_uniform", "standalone_brier_improvement_vs_uniform",
    "exact_weighted_mass_contribution_vs_uniform",
    "loo_top7_hits", "loo_actual_mass", "loo_log_score", "loo_brier",
    "loo_top7_hit_penalty", "loo_mass_penalty", "loo_log_penalty", "loo_brier_penalty",
    "loo_top7_members_changed", "loo_top7_jaccard",
    "full_top7_hits", "full_actual_mass", "full_log_score", "full_brier",
    "full_mass_edge_vs_uniform", "full_log_edge_vs_uniform", "full_brier_improvement_vs_uniform",
    "trusted", "source_verification", "frozen_at_jst", "expert_q_sha256", "loo_q_sha256",
    "final_q_sha256", "protocol_version",
]

SUMMARY_FIELDS = [
    "expert", "trusted_draws", "mean_effective_weight", "mean_exact_weighted_mass_contribution_vs_uniform",
    "mean_standalone_top7_hits", "mean_standalone_mass_edge_vs_uniform", "mean_standalone_log_edge_vs_uniform",
    "mean_standalone_brier_improvement_vs_uniform", "mean_loo_top7_hit_penalty", "mean_loo_mass_penalty",
    "mean_loo_log_penalty", "mean_loo_brier_penalty", "mean_loo_top7_members_changed", "mean_loo_top7_jaccard",
]


def load_json(path: Path, default: Dict[str, object]) -> Dict[str, object]:
    if not path.exists():
        return dict(default)
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else dict(default)
    except Exception:
        return dict(default)


def write_json(path: Path, obj: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def canonical_vector(values: Sequence[float], *, positive: bool = False, normalize: bool = False) -> List[str]:
    arr = np.asarray(values, dtype=float)
    if arr.ndim != 1 or not np.all(np.isfinite(arr)):
        raise ValueError("vector must be finite and one-dimensional")
    if positive and np.any(arr <= 0.0):
        raise ValueError("vector must be strictly positive")
    if normalize:
        total = float(arr.sum())
        if total <= 0.0:
            raise ValueError("cannot normalize nonpositive-sum vector")
        arr = arr / total
    return [format(float(v), CANONICAL_FLOAT_FORMAT) for v in arr]


def vector_sha256(values: object, expected_len: Optional[int] = None) -> str:
    if not isinstance(values, list) or not all(isinstance(x, str) for x in values):
        raise ValueError("canonical vector must be a list of strings")
    if expected_len is not None and len(values) != expected_len:
        raise ValueError("canonical vector length mismatch")
    raw = json.dumps(values, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def parse_q(values: object) -> np.ndarray:
    if not isinstance(values, list) or len(values) != N_NUMBERS:
        raise ValueError("q vector missing or malformed")
    arr = np.array([float(x) for x in values], dtype=float)
    if not np.all(np.isfinite(arr)) or np.any(arr <= 0.0):
        raise ValueError("invalid q vector")
    return arr / arr.sum()


def parse_vector(values: object, expected_len: int) -> np.ndarray:
    if not isinstance(values, list) or len(values) != expected_len:
        raise ValueError("vector missing or malformed")
    arr = np.array([float(x) for x in values], dtype=float)
    if not np.all(np.isfinite(arr)):
        raise ValueError("invalid vector")
    return arr


def cfg_from_obj(obj: object) -> Optional[v2.ModelConfig]:
    return v4.cfg_from_obj(obj)


def champion_snapshot(x: np.ndarray, cfg: v2.ModelConfig, min_train: int = MIN_TRAIN) -> Dict[str, object]:
    if len(x) < min_train:
        raise ValueError("insufficient history")
    keys = list(expert_probabilities(x[:min_train]).keys())
    logw = np.zeros(len(keys), dtype=float)
    for t in range(min_train, len(x)):
        actual = np.flatnonzero(x[t])
        logw = v2._update_log_weights(x[:t], actual, keys, logw, cfg)

    ex = expert_probabilities(x)
    weights = v2._weights_from_log(logw, cfg.expert_uniform_mix)
    uniform = np.ones(N_NUMBERS, dtype=float) / N_NUMBERS
    mixture = np.zeros(N_NUMBERS, dtype=float)
    for i, key in enumerate(keys):
        mixture += float(weights[i]) * np.asarray(ex[key], dtype=float)
    mixture /= mixture.sum()
    final_q = (1.0 - cfg.final_uniform_mix) * mixture + cfg.final_uniform_mix * uniform
    final_q /= final_q.sum()

    direct = v2._score_distribution(x, keys, logw, cfg)
    if not np.allclose(final_q, direct, atol=2e-15, rtol=0.0):
        raise RuntimeError("snapshot does not reproduce v2 Champion q")

    contributions: Dict[str, np.ndarray] = {}
    for i, key in enumerate(keys):
        contributions[key] = (1.0 - cfg.final_uniform_mix) * float(weights[i]) * (np.asarray(ex[key]) - uniform)
    reconstructed = uniform + np.sum(np.stack([contributions[k] for k in keys], axis=0), axis=0)
    decomposition_error = float(np.max(np.abs(reconstructed - final_q)))
    if decomposition_error > 2e-15:
        raise RuntimeError("expert contribution decomposition failed")

    loo_q: Dict[str, np.ndarray] = {}
    for i, key in enumerate(keys):
        keep = 1.0 - float(weights[i])
        if keep <= 1e-12:
            raise RuntimeError("cannot construct leave-one-out mixture")
        core = np.zeros(N_NUMBERS, dtype=float)
        for j, other in enumerate(keys):
            if j == i:
                continue
            core += float(weights[j] / keep) * np.asarray(ex[other], dtype=float)
        core /= core.sum()
        q = (1.0 - cfg.final_uniform_mix) * core + cfg.final_uniform_mix * uniform
        loo_q[key] = q / q.sum()

    return {
        "keys": keys,
        "log_weights": logw,
        "effective_weights": weights,
        "expert_q": {k: np.asarray(ex[k], dtype=float) for k in keys},
        "final_q": final_q,
        "contributions": contributions,
        "loo_q": loo_q,
        "decomposition_max_abs_error": decomposition_error,
    }


def history_has_target(path: Path, target_round: int) -> bool:
    if not path.exists():
        return False
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except Exception:
            continue
        if int(rec.get("target_round", -1)) == int(target_round):
            return True
    return False


def append_freeze_history(path: Path, registry: Dict[str, object]) -> None:
    target = int(registry["target_round"])
    if history_has_target(path, target):
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(registry, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")


def calibration_crosscheck(out_dir: Path, target_round: int, final_q_sha: str) -> Dict[str, object]:
    obj = load_json(out_dir / CALIBRATION_REGISTRY_NAME, {})
    if not obj:
        return {"status": "not_available"}
    try:
        other_target = int(obj.get("target_round", -1))
    except Exception:
        return {"status": "malformed_calibration_registry"}
    if other_target != target_round:
        return {"status": "different_target", "calibration_target_round": other_target}
    other_sha = str(obj.get("base_q_sha256", ""))
    return {
        "status": "matched" if other_sha == final_q_sha else "mismatch",
        "calibration_target_round": other_target,
        "calibration_base_q_sha256": other_sha,
    }


def default_state(cfg: v2.ModelConfig, start_round: int) -> Dict[str, object]:
    return {
        "protocol_version": VERSION,
        "status": "active",
        "promotion_role": PROMOTION_ROLE,
        "claim_policy": CLAIM_POLICY,
        "horizon_trusted_draws": HORIZON_TRUSTED_DRAWS,
        "protocol_started_target_round": int(start_round),
        "locked_base_version": cfg.version(),
        "locked_base_config": asdict(cfg),
        "trusted_draws": 0,
        "graded_rounds": [],
        "current_target_round": int(start_round),
        "last_graded_round": None,
        "interim_model_changes_allowed": False,
        "interpretation": "descriptive expert attribution; not evidence to alter Production or the locked shadow during the horizon",
    }


def freeze_reference(out_dir: Path, x: np.ndarray, latest_round: int, data_sha: str,
                     cfg: v2.ModelConfig, source_verification: str, min_train: int = MIN_TRAIN) -> Dict[str, object]:
    target_round = int(latest_round) + 1
    snap = champion_snapshot(x, cfg, min_train=min_train)
    keys = list(snap["keys"])
    weights = np.asarray(snap["effective_weights"], dtype=float)
    logw = np.asarray(snap["log_weights"], dtype=float)
    final_q = np.asarray(snap["final_q"], dtype=float)

    final_can = canonical_vector(final_q, positive=True, normalize=True)
    final_sha = vector_sha256(final_can, N_NUMBERS)
    expert_q_can: Dict[str, List[str]] = {}
    expert_q_sha: Dict[str, str] = {}
    contribution_can: Dict[str, List[str]] = {}
    contribution_sha: Dict[str, str] = {}
    loo_q_can: Dict[str, List[str]] = {}
    loo_q_sha: Dict[str, str] = {}
    loo_top7: Dict[str, List[int]] = {}

    for key in keys:
        qcan = canonical_vector(snap["expert_q"][key], positive=True, normalize=True)
        ccan = canonical_vector(snap["contributions"][key])
        lcan = canonical_vector(snap["loo_q"][key], positive=True, normalize=True)
        expert_q_can[key] = qcan
        expert_q_sha[key] = vector_sha256(qcan, N_NUMBERS)
        contribution_can[key] = ccan
        contribution_sha[key] = vector_sha256(ccan, N_NUMBERS)
        loo_q_can[key] = lcan
        loo_q_sha[key] = vector_sha256(lcan, N_NUMBERS)
        loo_top7[key] = [int(i + 1) for i in np.argsort(-np.asarray(snap["loo_q"][key]), kind="mergesort")[:PICKS]]

    top7_idx = np.argsort(-final_q, kind="mergesort")[:PICKS]
    top7_numbers = [int(i + 1) for i in top7_idx]
    top7_attribution = []
    for idx in top7_idx:
        per = {key: float(np.asarray(snap["contributions"][key])[idx]) for key in keys}
        top7_attribution.append({
            "number": int(idx + 1),
            "final_q": float(final_q[idx]),
            "delta_vs_uniform": float(final_q[idx] - 1.0 / N_NUMBERS),
            "expert_contributions": per,
            "largest_positive_expert": max(keys, key=lambda k: per[k]),
            "largest_negative_expert": min(keys, key=lambda k: per[k]),
        })

    cross = calibration_crosscheck(out_dir, target_round, final_sha)
    if cross.get("status") == "mismatch":
        raise RuntimeError("same-target calibration base q hash mismatch")

    registry: Dict[str, object] = {
        "protocol_version": VERSION,
        "target_round": target_round,
        "base_data_sha256": data_sha,
        "latest_resolved_round_at_freeze": int(latest_round),
        "frozen_at_jst": v4.now_jst(),
        "source_verification_at_freeze": source_verification,
        "locked_base_version": cfg.version(),
        "locked_base_config": asdict(cfg),
        "expert_keys": keys,
        "expert_count": len(keys),
        "log_weights_canonical": canonical_vector(logw),
        "effective_weights_canonical": canonical_vector(weights),
        "effective_weights_sum": float(weights.sum()),
        "expert_q_canonical": expert_q_can,
        "expert_q_sha256": expert_q_sha,
        "exact_uniform_deviation_contribution_canonical": contribution_can,
        "exact_uniform_deviation_contribution_sha256": contribution_sha,
        "final_q_canonical": final_can,
        "final_q_sha256": final_sha,
        "decomposition_max_abs_error": float(snap["decomposition_max_abs_error"]),
        "leave_one_out_method": "renormalize_prefrozen_effective_weights_over_remaining_experts_then_apply_locked_final_uniform_mix",
        "leave_one_out_q_canonical": loo_q_can,
        "leave_one_out_q_sha256": loo_q_sha,
        "leave_one_out_top7": loo_top7,
        "top7_numbers": top7_numbers,
        "top7_attribution": top7_attribution,
        "calibration_shadow_crosscheck": cross,
        "canonical_float_format": CANONICAL_FLOAT_FORMAT,
        "hash_algorithm": HASH_ALGORITHM,
        "horizon_trusted_draws": HORIZON_TRUSTED_DRAWS,
        "promotion_role": PROMOTION_ROLE,
        "claim_policy": CLAIM_POLICY,
    }
    write_json(out_dir / REGISTRY_NAME, registry)
    append_freeze_history(out_dir / FREEZE_HISTORY_NAME, registry)
    return registry


def validate_registry(registry: Dict[str, object]) -> Dict[str, object]:
    if str(registry.get("protocol_version")) != VERSION:
        raise ValueError("protocol version mismatch")
    keys = registry.get("expert_keys")
    if not isinstance(keys, list) or not keys or not all(isinstance(k, str) for k in keys):
        raise ValueError("expert keys malformed")
    n = len(keys)
    weights_raw = registry.get("effective_weights_canonical")
    if not isinstance(weights_raw, list) or len(weights_raw) != n:
        raise ValueError("weights malformed")
    weights = parse_vector(weights_raw, n)
    if np.any(weights <= 0.0) or abs(float(weights.sum()) - 1.0) > 2e-12:
        raise ValueError("weights invalid")

    final_raw = registry.get("final_q_canonical")
    if vector_sha256(final_raw, N_NUMBERS) != str(registry.get("final_q_sha256", "")):
        raise ValueError("final q hash mismatch")
    final_q = parse_q(final_raw)

    expert_q: Dict[str, np.ndarray] = {}
    contributions: Dict[str, np.ndarray] = {}
    loo_q: Dict[str, np.ndarray] = {}
    q_raw = registry.get("expert_q_canonical")
    q_hashes = registry.get("expert_q_sha256")
    c_raw = registry.get("exact_uniform_deviation_contribution_canonical")
    c_hashes = registry.get("exact_uniform_deviation_contribution_sha256")
    l_raw = registry.get("leave_one_out_q_canonical")
    l_hashes = registry.get("leave_one_out_q_sha256")
    if not all(isinstance(v, dict) for v in (q_raw, q_hashes, c_raw, c_hashes, l_raw, l_hashes)):
        raise ValueError("per-expert maps malformed")
    for key in keys:
        if vector_sha256(q_raw.get(key), N_NUMBERS) != str(q_hashes.get(key, "")):
            raise ValueError(f"expert q hash mismatch: {key}")
        if vector_sha256(c_raw.get(key), N_NUMBERS) != str(c_hashes.get(key, "")):
            raise ValueError(f"contribution hash mismatch: {key}")
        if vector_sha256(l_raw.get(key), N_NUMBERS) != str(l_hashes.get(key, "")):
            raise ValueError(f"leave-one-out q hash mismatch: {key}")
        expert_q[key] = parse_q(q_raw.get(key))
        contributions[key] = parse_vector(c_raw.get(key), N_NUMBERS)
        loo_q[key] = parse_q(l_raw.get(key))

    reconstructed = np.ones(N_NUMBERS, dtype=float) / N_NUMBERS
    reconstructed += np.sum(np.stack([contributions[k] for k in keys], axis=0), axis=0)
    if float(np.max(np.abs(reconstructed - final_q))) > 5e-15:
        raise ValueError("stored expert contributions do not reconstruct final q")
    return {"keys": keys, "weights": weights, "final_q": final_q, "expert_q": expert_q, "contributions": contributions, "loo_q": loo_q}


def append_result_rows(path: Path, rows: List[Dict[str, object]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists() and path.stat().st_size > 0
    with path.open("a", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=RESULT_FIELDS)
        if not exists:
            w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in RESULT_FIELDS})


def top7_set(q: np.ndarray) -> set[int]:
    return set((np.argsort(-q, kind="mergesort")[:PICKS] + 1).tolist())


def grade_if_ready(out_dir: Path, registry: Dict[str, object], state: Dict[str, object],
                   latest_round: int, draw_date: str, actual_idx: np.ndarray,
                   source_verification: str, trusted: bool) -> str:
    target = int(registry.get("target_round", -1))
    graded = state.setdefault("graded_rounds", [])
    if target in graded:
        return "already_graded"
    if latest_round < target:
        return "waiting_for_result"
    if latest_round > target:
        state["status"] = "invalid_missed_prefrozen_target"
        state["missed_target_round"] = target
        state["missed_seen_latest_round"] = int(latest_round)
        return "missed_target_fail_closed"
    if not trusted:
        state["status"] = "awaiting_trusted_result_verification"
        state["pending_target_round"] = target
        state["pending_source_verification"] = source_verification
        return "awaiting_trusted_verification"

    try:
        snap = validate_registry(registry)
    except Exception as exc:
        state["status"] = "invalid_prefrozen_reference"
        state["invalid_reason"] = str(exc)
        return "invalid_reference_fail_closed"

    keys = snap["keys"]
    weights = np.asarray(snap["weights"], dtype=float)
    final_q = np.asarray(snap["final_q"], dtype=float)
    full = so.signal_row(final_q, actual_idx)
    uniform = so.signal_row(so.UNIFORM_Q, actual_idx)
    full_top7 = top7_set(final_q)
    rows: List[Dict[str, object]] = []
    exact_mass_sum = 0.0

    for i, key in enumerate(keys):
        qk = np.asarray(snap["expert_q"][key], dtype=float)
        loo = np.asarray(snap["loo_q"][key], dtype=float)
        comp = np.asarray(snap["contributions"][key], dtype=float)
        standalone = so.signal_row(qk, actual_idx)
        loo_score = so.signal_row(loo, actual_idx)
        loo_top7 = top7_set(loo)
        exact_mass = float(comp[actual_idx].sum())
        exact_mass_sum += exact_mass
        inter = len(full_top7 & loo_top7)
        union = len(full_top7 | loo_top7)
        rows.append({
            "round": target,
            "draw_date": draw_date,
            "expert": key,
            "effective_weight": float(weights[i]),
            "standalone_top7_hits": standalone["top7_hits"],
            "standalone_actual_mass": standalone["actual_mass"],
            "standalone_log_score": standalone["mean_log_prob_actual"],
            "standalone_brier": standalone["brier"],
            "standalone_mass_edge_vs_uniform": float(standalone["actual_mass"] - uniform["actual_mass"]),
            "standalone_log_edge_vs_uniform": float(standalone["mean_log_prob_actual"] - uniform["mean_log_prob_actual"]),
            "standalone_brier_improvement_vs_uniform": float(uniform["brier"] - standalone["brier"]),
            "exact_weighted_mass_contribution_vs_uniform": exact_mass,
            "loo_top7_hits": loo_score["top7_hits"],
            "loo_actual_mass": loo_score["actual_mass"],
            "loo_log_score": loo_score["mean_log_prob_actual"],
            "loo_brier": loo_score["brier"],
            "loo_top7_hit_penalty": float(full["top7_hits"] - loo_score["top7_hits"]),
            "loo_mass_penalty": float(full["actual_mass"] - loo_score["actual_mass"]),
            "loo_log_penalty": float(full["mean_log_prob_actual"] - loo_score["mean_log_prob_actual"]),
            "loo_brier_penalty": float(loo_score["brier"] - full["brier"]),
            "loo_top7_members_changed": int(PICKS - inter),
            "loo_top7_jaccard": float(inter / union) if union else 1.0,
            "full_top7_hits": full["top7_hits"],
            "full_actual_mass": full["actual_mass"],
            "full_log_score": full["mean_log_prob_actual"],
            "full_brier": full["brier"],
            "full_mass_edge_vs_uniform": float(full["actual_mass"] - uniform["actual_mass"]),
            "full_log_edge_vs_uniform": float(full["mean_log_prob_actual"] - uniform["mean_log_prob_actual"]),
            "full_brier_improvement_vs_uniform": float(uniform["brier"] - full["brier"]),
            "trusted": True,
            "source_verification": source_verification,
            "frozen_at_jst": registry.get("frozen_at_jst", ""),
            "expert_q_sha256": (registry.get("expert_q_sha256") or {}).get(key, ""),
            "loo_q_sha256": (registry.get("leave_one_out_q_sha256") or {}).get(key, ""),
            "final_q_sha256": registry.get("final_q_sha256", ""),
            "protocol_version": VERSION,
        })

    expected_mass_edge = float(full["actual_mass"] - uniform["actual_mass"])
    if abs(exact_mass_sum - expected_mass_edge) > 1e-12:
        state["status"] = "invalid_mass_attribution_identity_failure"
        state["mass_identity_error"] = float(exact_mass_sum - expected_mass_edge)
        return "mass_identity_fail_closed"

    append_result_rows(out_dir / RESULTS_NAME, rows)
    graded.append(target)
    state["trusted_draws"] = int(state.get("trusted_draws", 0) or 0) + 1
    state["last_graded_round"] = target
    state["last_grade_exact_mass_contribution_sum"] = exact_mass_sum
    state["last_grade_full_mass_edge_vs_uniform"] = expected_mass_edge
    state["status"] = "active"
    state.pop("pending_target_round", None)
    state.pop("pending_source_verification", None)
    if int(state["trusted_draws"]) >= int(state.get("horizon_trusted_draws", HORIZON_TRUSTED_DRAWS)):
        state["status"] = "complete_fixed_horizon"
    return "graded_trusted"


def read_result_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_summary(out_dir: Path, keys: Sequence[str]) -> None:
    rows = read_result_rows(out_dir / RESULTS_NAME)
    out: List[Dict[str, object]] = []
    numeric = [
        "effective_weight", "exact_weighted_mass_contribution_vs_uniform", "standalone_top7_hits",
        "standalone_mass_edge_vs_uniform", "standalone_log_edge_vs_uniform", "standalone_brier_improvement_vs_uniform",
        "loo_top7_hit_penalty", "loo_mass_penalty", "loo_log_penalty", "loo_brier_penalty",
        "loo_top7_members_changed", "loo_top7_jaccard",
    ]
    for key in keys:
        rr = [r for r in rows if r.get("expert") == key and str(r.get("trusted", "")).lower() == "true"]
        rec: Dict[str, object] = {"expert": key, "trusted_draws": len(rr)}
        for field in numeric:
            vals = [float(r[field]) for r in rr if r.get(field, "") != ""]
            name = "mean_" + field
            rec[name] = float(np.mean(vals)) if vals else ""
        out.append(rec)
    out.sort(key=lambda r: float(r.get("mean_exact_weighted_mass_contribution_vs_uniform") or -1e99), reverse=True)
    path = out_dir / SUMMARY_NAME
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=SUMMARY_FIELDS)
        w.writeheader()
        for row in out:
            w.writerow({k: row.get(k, "") for k in SUMMARY_FIELDS})


def write_report(out_dir: Path, state: Dict[str, object], registry: Dict[str, object]) -> None:
    trusted = int(state.get("trusted_draws", 0) or 0)
    horizon = int(state.get("horizon_trusted_draws", HORIZON_TRUSTED_DRAWS) or HORIZON_TRUSTED_DRAWS)
    lines = [
        "# Signal Expert Attribution Future-OOS",
        "",
        f"- protocol: **{VERSION}**",
        "- role: **Research diagnostic only; no Production authority**",
        f"- locked base: **{state.get('locked_base_version', '')}**",
        f"- fixed observation horizon: **{trusted}/{horizon} trusted draws**",
        f"- status: **{state.get('status', 'unknown')}**",
        f"- current target: **round {registry.get('target_round', 'none')}**",
        f"- pre-frozen: **{'YES' if registry else 'NO'}**",
        f"- interim model changes allowed: **{str(bool(state.get('interim_model_changes_allowed', False))).lower()}**",
    ]
    if registry:
        keys = list(registry.get("expert_keys") or [])
        weights = [float(x) for x in (registry.get("effective_weights_canonical") or [])]
        pairs = sorted(zip(keys, weights), key=lambda kv: kv[1], reverse=True)
        lines += [
            f"- frozen at JST: **{registry.get('frozen_at_jst', '')}**",
            f"- expert count: **{len(keys)}**",
            f"- final q SHA-256: `{registry.get('final_q_sha256', '')}`",
            f"- decomposition max abs error: **{float(registry.get('decomposition_max_abs_error', 0.0)):.3e}**",
            f"- calibration-shadow crosscheck: **{(registry.get('calibration_shadow_crosscheck') or {}).get('status', 'unknown')}**",
            "",
            "## Current pre-frozen effective weights",
            "",
        ]
        for key, weight in pairs:
            lines.append(f"- {key}: **{weight:.6f}**")
    lines += [
        "",
        "## Interpretation boundary",
        "",
        "- `final_q - Uniform` is exactly decomposed into weighted expert contributions before the result.",
        "- Actual-mass attribution is exactly additive after the result; its expert contributions must sum to the full Champion mass edge vs Uniform.",
        "- Log/Brier attribution is not additive; leave-one-expert-out values are counterfactual diagnostics only.",
        f"- **{CLAIM_POLICY}**",
        "- Interim attribution must not be used to change the locked shadow mixture during the 26-draw observation horizon.",
    ]
    (out_dir / REPORT_NAME).write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(csv_path: Path, out_dir: Path, champion_file: Path, source_report: Path,
        min_train: int = MIN_TRAIN) -> Dict[str, object]:
    out_dir.mkdir(parents=True, exist_ok=True)
    df = read_csv_flexible(csv_path)
    x, clean = make_history(df)
    data_sha = fingerprint_file(csv_path)
    latest_round = v4.parse_round(clean["回別"].iloc[-1] if "回別" in clean.columns else len(clean)) or len(clean)
    latest_date = clean["抽せん日"].iloc[-1].date().isoformat()
    verification, trusted = v4.source_info(source_report, latest_round)

    state_path = out_dir / STATE_NAME
    registry_path = out_dir / REGISTRY_NAME
    state = load_json(state_path, {})
    registry = load_json(registry_path, {})

    if state:
        cfg = cfg_from_obj(state.get("locked_base_config"))
        if cfg is None:
            state["status"] = "invalid_locked_base_config"
            write_json(state_path, state)
            write_report(out_dir, state, registry)
            return {"status": state["status"], "latest_round": latest_round}
    else:
        cfg = v2.load_champion(champion_file)
        state = default_state(cfg, latest_round + 1)
        state["production_champion_version_at_protocol_start"] = cfg.version()
        state["protocol_started_at_jst"] = v4.now_jst()

    grade_action = "none"
    if registry:
        target = int(registry.get("target_round", -1))
        if latest_round >= target:
            actual_idx = np.flatnonzero(x[-1]) if latest_round == target else np.array([], dtype=int)
            grade_action = grade_if_ready(out_dir, registry, state, latest_round, latest_date, actual_idx, verification, trusted)

    if str(state.get("status")) not in ("complete_fixed_horizon", "invalid_missed_prefrozen_target", "invalid_prefrozen_reference", "invalid_mass_attribution_identity_failure"):
        current_target = int(registry.get("target_round", -1)) if registry else -1
        if not registry:
            registry = freeze_reference(out_dir, x, latest_round, data_sha, cfg, verification, min_train)
            state["current_target_round"] = int(registry["target_round"])
        elif current_target == latest_round and grade_action == "awaiting_trusted_verification":
            pass
        elif grade_action in ("graded_trusted", "already_graded") and current_target <= latest_round:
            registry = freeze_reference(out_dir, x, latest_round, data_sha, cfg, verification, min_train)
            state["current_target_round"] = int(registry["target_round"])

    state["last_run_jst"] = v4.now_jst()
    state["latest_seen_round"] = int(latest_round)
    state["latest_data_sha256"] = data_sha
    state["latest_source_verification"] = verification
    state["latest_source_trusted"] = bool(trusted)
    state["last_grade_action"] = grade_action
    state["promotion_role"] = PROMOTION_ROLE
    state["claim_policy"] = CLAIM_POLICY
    write_json(state_path, state)
    keys = list(registry.get("expert_keys") or []) if registry else []
    if keys:
        write_summary(out_dir, keys)
    write_report(out_dir, state, registry)
    return {
        "status": state.get("status"),
        "latest_round": latest_round,
        "target_round": registry.get("target_round") if registry else None,
        "trusted_draws": state.get("trusted_draws", 0),
        "horizon_trusted_draws": state.get("horizon_trusted_draws", HORIZON_TRUSTED_DRAWS),
        "expert_count": len(keys),
        "grade_action": grade_action,
        "final_q_sha256": registry.get("final_q_sha256") if registry else None,
        "calibration_shadow_crosscheck": (registry.get("calibration_shadow_crosscheck") or {}).get("status") if registry else None,
        "frozen_at_jst": registry.get("frozen_at_jst") if registry else None,
        "promotion_role": PROMOTION_ROLE,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Pre-frozen Future-OOS attribution for Champion signal experts")
    ap.add_argument("--csv", type=Path, default=Path("loto7.csv"))
    ap.add_argument("--out-dir", type=Path, default=Path("loto7_agent_output"))
    ap.add_argument("--champion-file", type=Path, default=Path("loto7_agent_output/model_champion.json"))
    ap.add_argument("--source-report", type=Path, default=Path("loto7_agent_output/source_validation.json"))
    ap.add_argument("--min-train", type=int, default=MIN_TRAIN)
    args = ap.parse_args()
    result = run(args.csv, args.out_dir, args.champion_file, args.source_report, args.min_train)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
