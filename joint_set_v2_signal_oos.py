#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np

import loto7_v4_runner as v4
from joint_set_v2_model import (
    N_NUMBERS,
    PICKS,
    UNIFORM_INCLUSION,
    bernoulli_signal_metrics,
    candidate_configs,
    forecast,
)
from joint_set_v2_research import build_prequential_signal, select_config
from loto7_evolving_agent import fingerprint_file, make_history, read_csv_flexible

VERSION = "joint-set-v2-signal-oos-v1"
HORIZON_TRUSTED_DRAWS = 26
START_TARGET_ROUND = 701
EXCLUDED_ALREADY_FROZEN_TARGET = 700
MIN_TRAIN = 100
SELECTION_WINDOW = 120
PERMUTATION_REPS = 4096
CANONICAL_FLOAT_FORMAT = ".17g"
PROMOTION_ROLE = "diagnostic_only"
PRIMARY_ENDPOINT = "fixed_horizon_mean_bernoulli_log_edge_vs_uniform"
SECONDARY_ENDPOINT = "fixed_horizon_mean_top7_hits"
CLAIM_POLICY = (
    "fixed_26_trusted_draw_signal_diagnostic_no_interim_tuning_no_production_authority"
)

REGISTRATION_NAME = "joint_set_v2_signal_oos_registration.json"
REGISTRY_NAME = "joint_set_v2_signal_oos_registry.json"
STATE_NAME = "joint_set_v2_signal_oos_state.json"
RESULTS_NAME = "joint_set_v2_signal_oos_results.csv"
FREEZE_HISTORY_NAME = "joint_set_v2_signal_oos_freeze_history.jsonl"
SUMMARY_NAME = "joint_set_v2_signal_oos_summary.json"
REPORT_NAME = "joint_set_v2_signal_oos_report.md"

RESULT_FIELDS = [
    "round", "draw_date", "selected_config", "selected_config_prior_score",
    "top7_hits", "actual_inclusion_probability", "bernoulli_log_edge_vs_uniform",
    "bernoulli_brier_edge_vs_uniform", "inclusion_sum", "gate",
    "regime_stable", "regime_shift", "regime_volatile",
    "source_verification", "trusted", "frozen_at_jst", "inclusion_p_sha256",
    "algorithm_manifest_sha256", "protocol_version",
]


def load_json(path: Path, default: Optional[Mapping[str, object]] = None) -> Dict[str, object]:
    if not path.exists():
        return dict(default or {})
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else dict(default or {})
    except Exception:
        return dict(default or {})


def write_json(path: Path, obj: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(obj), ensure_ascii=False, indent=2), encoding="utf-8")


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_vector(values: Sequence[float]) -> List[str]:
    arr = np.asarray(values, dtype=float)
    if arr.shape != (N_NUMBERS,) or not np.all(np.isfinite(arr)):
        raise ValueError("inclusion vector must be finite with length 37")
    return [format(float(v), CANONICAL_FLOAT_FORMAT) for v in arr]


def vector_sha256(values: object) -> str:
    if not isinstance(values, list) or len(values) != N_NUMBERS or not all(isinstance(x, str) for x in values):
        raise ValueError("canonical inclusion vector malformed")
    raw = json.dumps(values, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def parse_inclusion(values: object) -> np.ndarray:
    if not isinstance(values, list) or len(values) != N_NUMBERS:
        raise ValueError("inclusion vector missing or malformed")
    p = np.asarray([float(x) for x in values], dtype=float)
    if not np.all(np.isfinite(p)) or np.any(p <= 0.0) or np.any(p >= 1.0):
        raise ValueError("inclusion probabilities must be strictly between 0 and 1")
    if abs(float(p.sum()) - PICKS) > 2e-10:
        raise ValueError("inclusion probabilities must sum to 7")
    return p


def algorithm_manifest(
    protocol_file: Path,
    model_file: Path,
    research_file: Path,
    min_train: int = MIN_TRAIN,
    selection_window: int = SELECTION_WINDOW,
) -> Dict[str, object]:
    configs = candidate_configs()
    manifest: Dict[str, object] = {
        "protocol_version": VERSION,
        "protocol_file_sha256": file_sha256(protocol_file),
        "model_file_sha256": file_sha256(model_file),
        "research_file_sha256": file_sha256(research_file),
        "config_versions": [cfg.version() for cfg in configs],
        "config_count": len(configs),
        "min_train": int(min_train),
        "selection_window": int(selection_window),
        "start_target_round": START_TARGET_ROUND,
        "horizon_trusted_draws": HORIZON_TRUSTED_DRAWS,
        "primary_endpoint": PRIMARY_ENDPOINT,
        "secondary_endpoint": SECONDARY_ENDPOINT,
        "permutation_reps": PERMUTATION_REPS,
    }
    raw = json.dumps(manifest, sort_keys=True, separators=(",", ":"))
    manifest["manifest_sha256"] = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return manifest


def validate_manifest(registration: Mapping[str, object], current: Mapping[str, object]) -> None:
    locked = registration.get("algorithm_manifest")
    if not isinstance(locked, dict):
        raise ValueError("locked algorithm manifest missing")
    if str(locked.get("manifest_sha256", "")) != str(current.get("manifest_sha256", "")):
        raise ValueError("locked algorithm manifest changed")
    if locked != dict(current):
        raise ValueError("locked algorithm manifest content changed")


def create_registration(
    latest_round: int,
    latest_data_sha: str,
    manifest: Mapping[str, object],
) -> Dict[str, object]:
    if int(latest_round) >= START_TARGET_ROUND:
        raise RuntimeError("protocol cannot be initialized after the first prospective target has resolved")
    return {
        "protocol_version": VERSION,
        "registered_at_jst": v4.now_jst(),
        "registered_latest_resolved_round": int(latest_round),
        "registered_data_sha256": latest_data_sha,
        "start_target_round": START_TARGET_ROUND,
        "excluded_already_frozen_target_round": EXCLUDED_ALREADY_FROZEN_TARGET,
        "horizon_trusted_draws": HORIZON_TRUSTED_DRAWS,
        "promotion_role": PROMOTION_ROLE,
        "claim_policy": CLAIM_POLICY,
        "primary_endpoint": PRIMARY_ENDPOINT,
        "secondary_endpoint": SECONDARY_ENDPOINT,
        "inference_plan": {
            "fixed_horizon_only": True,
            "global_number_label_permutations": PERMUTATION_REPS,
            "permutation_map_reused_across_all_26_draws_within_each_replicate": True,
            "upper_tail_p_correction": "(1 + exceedances) / (reps + 1)",
            "interim_p_values_authoritative": False,
        },
        "algorithm_manifest": dict(manifest),
        "interpretation": (
            "Research-only prospective signal shadow. Round 700 is excluded because it was already frozen under existing governance before this protocol was registered. "
            "The first eligible vector is round 701 and may be frozen only after round 700 is verified by two result sources."
        ),
    }


def default_state(registration: Mapping[str, object]) -> Dict[str, object]:
    return {
        "protocol_version": VERSION,
        "status": "waiting_for_verified_round_700_prefix",
        "start_target_round": int(registration["start_target_round"]),
        "current_target_round": None,
        "trusted_draws": 0,
        "graded_rounds": [],
        "last_graded_round": None,
        "horizon_trusted_draws": HORIZON_TRUSTED_DRAWS,
        "promotion_role": PROMOTION_ROLE,
        "claim_policy": CLAIM_POLICY,
        "interim_model_changes_allowed": False,
        "interim_endpoint_based_tuning_allowed": False,
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


def append_freeze_history(path: Path, registry: Mapping[str, object]) -> None:
    target = int(registry["target_round"])
    if history_has_target(path, target):
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(dict(registry), ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")


def read_freeze_history(path: Path) -> Dict[int, Dict[str, object]]:
    out: Dict[int, Dict[str, object]] = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        target = int(rec["target_round"])
        if target in out and out[target] != rec:
            raise ValueError(f"conflicting freeze history for round {target}")
        out[target] = rec
    return out


def build_signal_forecast(
    x: np.ndarray,
    min_train: int = MIN_TRAIN,
    selection_window: int = SELECTION_WINDOW,
) -> Dict[str, object]:
    if len(x) < int(min_train) + 30:
        raise ValueError("insufficient history for strict v2 config selection")
    configs = candidate_configs()
    preq = {cfg.version(): build_prequential_signal(x, cfg, min_train) for cfg in configs}
    prior_count = len(x) - int(min_train)
    cfg, cfg_score = select_config(configs, preq, prior_count, selection_window)
    bundle = forecast(x, cfg, preq[cfg.version()][:prior_count])
    p = np.asarray(bundle.inclusion_p, dtype=float)
    if p.shape != (N_NUMBERS,) or abs(float(p.sum()) - PICKS) > 2e-10:
        raise RuntimeError("v2 forecast did not produce a valid inclusion vector")
    top7 = [int(i + 1) for i in np.argsort(-p, kind="mergesort")[:PICKS]]
    return {
        "selected_config": cfg.version(),
        "selected_config_prior_score": float(cfg_score),
        "inclusion_p": p,
        "top7_numbers": top7,
        "gate": float(bundle.gate),
        "gate_diagnostics": dict(bundle.gate_diagnostics),
        "regime": [float(v) for v in bundle.regime],
    }


def freeze_reference(
    out_dir: Path,
    x: np.ndarray,
    latest_round: int,
    data_sha: str,
    source_verification: str,
    registration: Mapping[str, object],
    min_train: int = MIN_TRAIN,
    selection_window: int = SELECTION_WINDOW,
) -> Dict[str, object]:
    target_round = int(latest_round) + 1
    start_round = int(registration["start_target_round"])
    if target_round < start_round:
        raise RuntimeError("attempted to freeze before registered start target")
    locked_manifest = registration.get("algorithm_manifest") or {}
    signal = build_signal_forecast(x, min_train=min_train, selection_window=selection_window)
    canonical = canonical_vector(signal["inclusion_p"])
    p_sha = vector_sha256(canonical)
    regime = list(signal["regime"])
    registry: Dict[str, object] = {
        "protocol_version": VERSION,
        "target_round": target_round,
        "latest_resolved_round_at_freeze": int(latest_round),
        "base_data_sha256": data_sha,
        "frozen_at_jst": v4.now_jst(),
        "source_verification_at_freeze": source_verification,
        "selected_config": signal["selected_config"],
        "selected_config_prior_score": signal["selected_config_prior_score"],
        "inclusion_p_canonical": canonical,
        "inclusion_p_sha256": p_sha,
        "inclusion_sum": float(np.asarray(signal["inclusion_p"]).sum()),
        "top7_numbers": signal["top7_numbers"],
        "gate": signal["gate"],
        "gate_diagnostics": signal["gate_diagnostics"],
        "regime": {
            "stable": float(regime[0]),
            "shift": float(regime[1]),
            "volatile": float(regime[2]),
        },
        "algorithm_manifest_sha256": str(locked_manifest.get("manifest_sha256", "")),
        "primary_endpoint": PRIMARY_ENDPOINT,
        "secondary_endpoint": SECONDARY_ENDPOINT,
        "promotion_role": PROMOTION_ROLE,
        "claim_policy": CLAIM_POLICY,
        "canonical_float_format": CANONICAL_FLOAT_FORMAT,
    }
    write_json(out_dir / REGISTRY_NAME, registry)
    append_freeze_history(out_dir / FREEZE_HISTORY_NAME, registry)
    return registry


def validate_registry(registry: Mapping[str, object], registration: Mapping[str, object]) -> np.ndarray:
    if str(registry.get("protocol_version", "")) != VERSION:
        raise ValueError("registry protocol version mismatch")
    locked_manifest = registration.get("algorithm_manifest") or {}
    if str(registry.get("algorithm_manifest_sha256", "")) != str(locked_manifest.get("manifest_sha256", "")):
        raise ValueError("registry algorithm manifest hash mismatch")
    raw = registry.get("inclusion_p_canonical")
    if vector_sha256(raw) != str(registry.get("inclusion_p_sha256", "")):
        raise ValueError("inclusion probability hash mismatch")
    p = parse_inclusion(raw)
    expected_top7 = [int(i + 1) for i in np.argsort(-p, kind="mergesort")[:PICKS]]
    stored_top7 = [int(v) for v in list(registry.get("top7_numbers") or [])]
    if stored_top7 != expected_top7:
        raise ValueError("stored Top7 does not match frozen inclusion vector")
    return p


def read_result_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def append_result(path: Path, row: Mapping[str, object]) -> None:
    existing = read_result_rows(path)
    target = int(row["round"])
    if any(int(r["round"]) == target for r in existing):
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists() and path.stat().st_size > 0
    with path.open("a", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=RESULT_FIELDS)
        if not exists:
            w.writeheader()
        w.writerow({k: row.get(k, "") for k in RESULT_FIELDS})


def grade_if_ready(
    out_dir: Path,
    registry: Mapping[str, object],
    registration: Mapping[str, object],
    state: Dict[str, object],
    latest_round: int,
    draw_date: str,
    actual_idx: np.ndarray,
    source_verification: str,
    trusted: bool,
) -> str:
    target = int(registry.get("target_round", -1))
    graded = [int(v) for v in list(state.setdefault("graded_rounds", []))]
    state["graded_rounds"] = graded
    if latest_round > target:
        state["status"] = "invalid_missed_prefrozen_target_or_next_freeze"
        state["missed_target_round"] = target
        state["missed_seen_latest_round"] = int(latest_round)
        return "missed_target_fail_closed"
    if latest_round < target:
        state["status"] = "active_target_prefrozen_waiting_result"
        return "waiting_for_result"
    if target in graded:
        return "already_graded"
    if not trusted:
        state["status"] = "awaiting_trusted_result_verification"
        state["pending_target_round"] = target
        state["pending_source_verification"] = source_verification
        return "awaiting_trusted_verification"
    try:
        p = validate_registry(registry, registration)
    except Exception as exc:
        state["status"] = "invalid_prefrozen_reference"
        state["invalid_reason"] = str(exc)
        return "invalid_reference_fail_closed"

    metrics = bernoulli_signal_metrics(p, actual_idx)
    regime = registry.get("regime") or {}
    row = {
        "round": target,
        "draw_date": draw_date,
        "selected_config": registry.get("selected_config", ""),
        "selected_config_prior_score": registry.get("selected_config_prior_score", ""),
        "top7_hits": metrics["top7_hits"],
        "actual_inclusion_probability": metrics["actual_mass"],
        "bernoulli_log_edge_vs_uniform": metrics["log_edge"],
        "bernoulli_brier_edge_vs_uniform": metrics["brier_edge"],
        "inclusion_sum": metrics["inclusion_sum"],
        "gate": registry.get("gate", ""),
        "regime_stable": regime.get("stable", "") if isinstance(regime, dict) else "",
        "regime_shift": regime.get("shift", "") if isinstance(regime, dict) else "",
        "regime_volatile": regime.get("volatile", "") if isinstance(regime, dict) else "",
        "source_verification": source_verification,
        "trusted": True,
        "frozen_at_jst": registry.get("frozen_at_jst", ""),
        "inclusion_p_sha256": registry.get("inclusion_p_sha256", ""),
        "algorithm_manifest_sha256": registry.get("algorithm_manifest_sha256", ""),
        "protocol_version": VERSION,
    }
    append_result(out_dir / RESULTS_NAME, row)
    graded.append(target)
    state["graded_rounds"] = graded
    state["trusted_draws"] = int(state.get("trusted_draws", 0) or 0) + 1
    state["last_graded_round"] = target
    state["last_grade_metrics"] = {
        "top7_hits": float(metrics["top7_hits"]),
        "log_edge": float(metrics["log_edge"]),
        "brier_edge": float(metrics["brier_edge"]),
        "actual_inclusion_probability": float(metrics["actual_mass"]),
    }
    state.pop("pending_target_round", None)
    state.pop("pending_source_verification", None)
    if int(state["trusted_draws"]) >= HORIZON_TRUSTED_DRAWS:
        state["status"] = "complete_fixed_horizon"
    else:
        state["status"] = "active_ready_to_freeze_next"
    return "graded_trusted"


def _permute_probability_vector(p: np.ndarray, permutation: np.ndarray) -> np.ndarray:
    out = np.empty_like(p)
    out[np.asarray(permutation, dtype=int)] = p
    return out


def _permutation_seed(registration: Mapping[str, object], replicate: int) -> int:
    manifest = registration.get("algorithm_manifest") or {}
    payload = (
        f"{VERSION}|{manifest.get('manifest_sha256','')}|global-label-permutation|{int(replicate)}"
    ).encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big") & 0x7FFFFFFF


def fixed_horizon_permutation_inference(
    out_dir: Path,
    registration: Mapping[str, object],
    result_rows: Sequence[Mapping[str, str]],
    reps: int = PERMUTATION_REPS,
) -> Dict[str, object]:
    if len(result_rows) != HORIZON_TRUSTED_DRAWS:
        return {"available": False, "reason": "fixed_horizon_not_complete"}
    history = read_freeze_history(out_dir / FREEZE_HISTORY_NAME)
    rounds = [int(r["round"]) for r in result_rows]
    if any(r not in history for r in rounds):
        raise RuntimeError("freeze history missing a graded round")

    vectors: List[np.ndarray] = []
    actual_indices: List[np.ndarray] = []
    for row in result_rows:
        target = int(row["round"])
        p = validate_registry(history[target], registration)
        vectors.append(p)
        actual_numbers = [int(v) for v in str(row.get("actual_numbers", "")).split() if v.strip()]
        if len(actual_numbers) != PICKS:
            # Older result rows intentionally do not expose actual_numbers; reconstructing from
            # loto7.csv here would weaken audit locality. The caller enriches rows before this function.
            raise RuntimeError("actual numbers missing from fixed-horizon inference input")
        actual_indices.append(np.asarray([v - 1 for v in actual_numbers], dtype=int))

    observed_log = float(np.mean([float(r["bernoulli_log_edge_vs_uniform"]) for r in result_rows]))
    observed_top7 = float(np.mean([float(r["top7_hits"]) for r in result_rows]))
    observed_brier = float(np.mean([float(r["bernoulli_brier_edge_vs_uniform"]) for r in result_rows]))
    null_log = np.empty(int(reps), dtype=float)
    null_top7 = np.empty(int(reps), dtype=float)
    null_brier = np.empty(int(reps), dtype=float)
    for replicate in range(int(reps)):
        rng = np.random.default_rng(_permutation_seed(registration, replicate))
        permutation = rng.permutation(N_NUMBERS)
        logs: List[float] = []
        top7s: List[float] = []
        briers: List[float] = []
        for p, actual_idx in zip(vectors, actual_indices):
            metrics = bernoulli_signal_metrics(_permute_probability_vector(p, permutation), actual_idx)
            logs.append(float(metrics["log_edge"]))
            top7s.append(float(metrics["top7_hits"]))
            briers.append(float(metrics["brier_edge"]))
        null_log[replicate] = float(np.mean(logs))
        null_top7[replicate] = float(np.mean(top7s))
        null_brier[replicate] = float(np.mean(briers))

    def upper_p(null: np.ndarray, observed: float) -> float:
        return float((1 + int(np.sum(null >= observed - 1e-15))) / (len(null) + 1))

    return {
        "available": True,
        "reps": int(reps),
        "primary": {
            "endpoint": PRIMARY_ENDPOINT,
            "observed": observed_log,
            "null_mean": float(null_log.mean()),
            "upper_tail_p": upper_p(null_log, observed_log),
            "null_p95": float(np.quantile(null_log, 0.95)),
            "null_p99": float(np.quantile(null_log, 0.99)),
        },
        "secondary_top7": {
            "endpoint": SECONDARY_ENDPOINT,
            "observed": observed_top7,
            "null_mean": float(null_top7.mean()),
            "upper_tail_p": upper_p(null_top7, observed_top7),
            "null_p95": float(np.quantile(null_top7, 0.95)),
            "null_p99": float(np.quantile(null_top7, 0.99)),
        },
        "supportive_brier": {
            "observed": observed_brier,
            "null_mean": float(null_brier.mean()),
            "upper_tail_p": upper_p(null_brier, observed_brier),
        },
    }


def _actual_by_round(csv_path: Path) -> Dict[int, List[int]]:
    df = read_csv_flexible(csv_path)
    x, clean = make_history(df)
    rounds = [v4.parse_round(v) or (i + 1) for i, v in enumerate(clean.get("回別", range(1, len(clean) + 1)))]
    return {
        int(rounds[i]): [int(v + 1) for v in np.flatnonzero(x[i]).tolist()]
        for i in range(len(x))
    }


def build_summary(
    csv_path: Path,
    out_dir: Path,
    registration: Mapping[str, object],
    state: Mapping[str, object],
) -> Dict[str, object]:
    rows = read_result_rows(out_dir / RESULTS_NAME)
    trusted_rows = [r for r in rows if str(r.get("trusted", "")).lower() == "true"]
    logs = [float(r["bernoulli_log_edge_vs_uniform"]) for r in trusted_rows]
    briers = [float(r["bernoulli_brier_edge_vs_uniform"]) for r in trusted_rows]
    top7 = [float(r["top7_hits"]) for r in trusted_rows]
    masses = [float(r["actual_inclusion_probability"]) for r in trusted_rows]
    enriched: List[Dict[str, str]] = [dict(r) for r in trusted_rows]
    if len(enriched) == HORIZON_TRUSTED_DRAWS:
        actual_map = _actual_by_round(csv_path)
        for row in enriched:
            target = int(row["round"])
            nums = actual_map.get(target)
            if nums is None or len(nums) != PICKS:
                raise RuntimeError(f"actual result missing for completed round {target}")
            row["actual_numbers"] = " ".join(str(v) for v in nums)
    inference = fixed_horizon_permutation_inference(out_dir, registration, enriched, reps=PERMUTATION_REPS)
    return {
        "report_version": VERSION,
        "status": state.get("status"),
        "start_target_round": registration.get("start_target_round"),
        "excluded_already_frozen_target_round": registration.get("excluded_already_frozen_target_round"),
        "trusted_draws": len(trusted_rows),
        "horizon_trusted_draws": HORIZON_TRUSTED_DRAWS,
        "current_target_round": state.get("current_target_round"),
        "interim_descriptive": {
            "mean_top7_hits": float(np.mean(top7)) if top7 else None,
            "mean_actual_inclusion_probability": float(np.mean(masses)) if masses else None,
            "mean_bernoulli_log_edge_vs_uniform": float(np.mean(logs)) if logs else None,
            "mean_bernoulli_brier_edge_vs_uniform": float(np.mean(briers)) if briers else None,
        },
        "fixed_horizon_inference": inference,
        "primary_endpoint": PRIMARY_ENDPOINT,
        "secondary_endpoint": SECONDARY_ENDPOINT,
        "promotion_role": PROMOTION_ROLE,
        "promotion_eligible": False,
        "interim_tuning_allowed": False,
    }


def render_report(summary: Mapping[str, object], registration: Mapping[str, object], registry: Mapping[str, object]) -> str:
    interim = summary.get("interim_descriptive") or {}
    inference = summary.get("fixed_horizon_inference") or {}
    lines = [
        "# Joint Set v2 Signal — Prospective Future-OOS",
        "",
        f"- status: **{summary.get('status')}**",
        f"- protocol start target: **{summary.get('start_target_round')}**",
        f"- deliberately excluded target: **{summary.get('excluded_already_frozen_target_round')}**",
        f"- trusted progress: **{summary.get('trusted_draws')} / {summary.get('horizon_trusted_draws')}**",
        f"- current prefrozen target: **{summary.get('current_target_round')}**",
        f"- primary endpoint: **{PRIMARY_ENDPOINT}**",
        "- Production promotion eligible: **NO**",
        "- interim tuning allowed: **NO**",
        "",
        "## Interim descriptive signal metrics",
        f"- mean Top7 hits: **{interim.get('mean_top7_hits')}**",
        f"- mean actual inclusion probability: **{interim.get('mean_actual_inclusion_probability')}**",
        f"- mean Bernoulli log edge vs uniform: **{interim.get('mean_bernoulli_log_edge_vs_uniform')}**",
        f"- mean Bernoulli Brier edge vs uniform: **{interim.get('mean_bernoulli_brier_edge_vs_uniform')}**",
        "",
        "## Current freeze",
    ]
    if registry:
        lines += [
            f"- target: **{registry.get('target_round')}**",
            f"- selected config: **{registry.get('selected_config')}**",
            f"- Top7: **{registry.get('top7_numbers')}**",
            f"- gate: **{registry.get('gate')}**",
            f"- inclusion vector SHA256: `{registry.get('inclusion_p_sha256')}`",
            f"- frozen at JST: **{registry.get('frozen_at_jst')}**",
        ]
    else:
        lines.append("- **No v2 vector is frozen yet. Waiting for verified round 700 before freezing round 701.**")
    lines += ["", "## Fixed-horizon inference"]
    if isinstance(inference, dict) and inference.get("available"):
        primary = inference.get("primary") or {}
        secondary = inference.get("secondary_top7") or {}
        lines += [
            f"- primary observed: **{primary.get('observed')}** / null mean **{primary.get('null_mean')}** / p **{primary.get('upper_tail_p')}**",
            f"- Top7 observed: **{secondary.get('observed')}** / null mean **{secondary.get('null_mean')}** / p **{secondary.get('upper_tail_p')}**",
        ]
    else:
        lines.append("- unavailable until **26/26 trusted future draws** are complete")
    lines += [
        "",
        "> Round 700 is never retroactively counted. The first eligible prediction vector is round 701 and can only be generated from a verified round-700 prefix.",
        "> This shadow measures the v2 inclusion-probability signal only. Portfolio/ticket tuning is outside this protocol.",
        "> Interim observations cannot change the algorithm, config family, selection rule, endpoints, or horizon.",
        "",
    ]
    return "\n".join(lines)


def run(
    csv_path: Path = Path("loto7.csv"),
    out_dir: Path = Path("loto7_agent_output"),
    source_report: Path = Path("loto7_agent_output/source_validation.json"),
    protocol_file: Optional[Path] = None,
    model_file: Path = Path("joint_set_v2_model.py"),
    research_file: Path = Path("joint_set_v2_research.py"),
    min_train: int = MIN_TRAIN,
    selection_window: int = SELECTION_WINDOW,
) -> Dict[str, object]:
    out_dir.mkdir(parents=True, exist_ok=True)
    protocol_file = (protocol_file or Path(__file__)).resolve()
    df = read_csv_flexible(csv_path)
    x, clean = make_history(df)
    data_sha = fingerprint_file(csv_path)
    latest_round = v4.parse_round(clean["回別"].iloc[-1] if "回別" in clean.columns else len(clean)) or len(clean)
    latest_date = clean["抽せん日"].iloc[-1].date().isoformat()
    verification, trusted = v4.source_info(source_report, latest_round)
    current_manifest = algorithm_manifest(protocol_file, model_file, research_file, min_train, selection_window)

    registration_path = out_dir / REGISTRATION_NAME
    state_path = out_dir / STATE_NAME
    registry_path = out_dir / REGISTRY_NAME
    registration = load_json(registration_path, {})
    if not registration:
        registration = create_registration(latest_round, data_sha, current_manifest)
        write_json(registration_path, registration)
    try:
        validate_manifest(registration, current_manifest)
    except Exception as exc:
        state = load_json(state_path, default_state(registration))
        state["status"] = "invalid_locked_algorithm_changed"
        state["invalid_reason"] = str(exc)
        state["last_run_jst"] = v4.now_jst()
        write_json(state_path, state)
        registry = load_json(registry_path, {})
        summary = build_summary(csv_path, out_dir, registration, state)
        write_json(out_dir / SUMMARY_NAME, summary)
        (out_dir / REPORT_NAME).write_text(render_report(summary, registration, registry), encoding="utf-8")
        return {"status": state["status"], "latest_round": latest_round, "trusted_draws": state.get("trusted_draws", 0)}

    state = load_json(state_path, default_state(registration))
    registry = load_json(registry_path, {})
    terminal = {
        "complete_fixed_horizon",
        "invalid_locked_algorithm_changed",
        "invalid_missed_prefrozen_target_or_next_freeze",
        "invalid_prefrozen_reference",
        "invalid_missing_registry_after_start",
    }
    grade_action = "none"

    if str(state.get("status")) not in terminal:
        if registry:
            target = int(registry.get("target_round", -1))
            actual_idx = np.flatnonzero(x[-1]) if latest_round == target else np.array([], dtype=int)
            grade_action = grade_if_ready(
                out_dir, registry, registration, state, latest_round, latest_date,
                actual_idx, verification, trusted,
            )
            if (
                grade_action in {"graded_trusted", "already_graded"}
                and int(state.get("trusted_draws", 0)) < HORIZON_TRUSTED_DRAWS
                and latest_round == target
                and trusted
            ):
                registry = freeze_reference(
                    out_dir, x, latest_round, data_sha, verification, registration,
                    min_train=min_train, selection_window=selection_window,
                )
                state["current_target_round"] = int(registry["target_round"])
                state["status"] = "active_target_prefrozen_waiting_result"
        else:
            start = int(registration["start_target_round"])
            required_prefix = start - 1
            if int(state.get("trusted_draws", 0)) > 0:
                state["status"] = "invalid_missing_registry_after_start"
            elif latest_round < required_prefix:
                state["status"] = f"waiting_for_verified_round_{required_prefix}_prefix"
            elif latest_round == required_prefix:
                if trusted:
                    registry = freeze_reference(
                        out_dir, x, latest_round, data_sha, verification, registration,
                        min_train=min_train, selection_window=selection_window,
                    )
                    state["current_target_round"] = int(registry["target_round"])
                    state["status"] = "active_target_prefrozen_waiting_result"
                else:
                    state["status"] = f"waiting_for_verified_round_{required_prefix}_prefix"
                    state["pending_prefix_source_verification"] = verification
            else:
                state["status"] = "invalid_missed_prefrozen_target_or_next_freeze"
                state["missed_target_round"] = start
                state["missed_seen_latest_round"] = int(latest_round)

    state["latest_seen_round"] = int(latest_round)
    state["latest_data_sha256"] = data_sha
    state["latest_source_verification"] = verification
    state["latest_source_trusted"] = bool(trusted)
    state["last_grade_action"] = grade_action
    state["last_run_jst"] = v4.now_jst()
    state["promotion_role"] = PROMOTION_ROLE
    state["claim_policy"] = CLAIM_POLICY
    write_json(state_path, state)

    summary = build_summary(csv_path, out_dir, registration, state)
    write_json(out_dir / SUMMARY_NAME, summary)
    (out_dir / REPORT_NAME).write_text(render_report(summary, registration, registry), encoding="utf-8")
    return {
        "status": state.get("status"),
        "latest_round": latest_round,
        "current_target_round": state.get("current_target_round"),
        "trusted_draws": state.get("trusted_draws", 0),
        "horizon_trusted_draws": HORIZON_TRUSTED_DRAWS,
        "grade_action": grade_action,
        "promotion_role": PROMOTION_ROLE,
        "registration_manifest_sha256": (registration.get("algorithm_manifest") or {}).get("manifest_sha256"),
        "registry_inclusion_p_sha256": registry.get("inclusion_p_sha256") if registry else None,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Research-only prospective Future-OOS signal shadow for Joint Set v2")
    ap.add_argument("--csv", type=Path, default=Path("loto7.csv"))
    ap.add_argument("--out-dir", type=Path, default=Path("loto7_agent_output"))
    ap.add_argument("--source-report", type=Path, default=Path("loto7_agent_output/source_validation.json"))
    ap.add_argument("--model-file", type=Path, default=Path("joint_set_v2_model.py"))
    ap.add_argument("--research-file", type=Path, default=Path("joint_set_v2_research.py"))
    ap.add_argument("--min-train", type=int, default=MIN_TRAIN)
    ap.add_argument("--selection-window", type=int, default=SELECTION_WINDOW)
    args = ap.parse_args()
    result = run(
        args.csv, args.out_dir, args.source_report, Path(__file__),
        args.model_file, args.research_file, args.min_train, args.selection_window,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
