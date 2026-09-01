#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

import numpy as np

import champion_ranking_calibration as calibration
import loto7_v2_runner as v2
import loto7_v4_runner as v4
import separated_optimizer as so
from loto7_evolving_agent import expert_probabilities, fingerprint_file, make_history, read_csv_flexible

VERSION = "champion-calibration-oos-shadow-v1"
HORIZON_TRUSTED_DRAWS = 26
MIN_TRAIN = 100
CANONICAL_FLOAT_FORMAT = ".17g"
HASH_ALGORITHM = "sha256"
PROMOTION_ROLE = "diagnostic_only"
CLAIM_POLICY = "no_uniform_edge_claim_before_fixed_26_trusted_draw_horizon_complete"

REGISTRY_NAME = "champion_calibration_oos_registry.json"
STATE_NAME = "champion_calibration_oos_state.json"
RESULTS_NAME = "champion_calibration_oos_results.csv"
FREEZE_HISTORY_NAME = "champion_calibration_oos_freeze_history.jsonl"
REPORT_NAME = "champion_calibration_oos_report.md"

RESULT_FIELDS = [
    "round", "draw_date", "locked_base_version", "calibration_config_version",
    "temperature", "uniform_mix", "rank_preserved", "top7_delta_vs_base",
    "calibrated_top7_hits", "base_top7_hits",
    "calibrated_actual_mass", "base_actual_mass", "uniform_actual_mass",
    "actual_mass_delta_vs_base", "actual_mass_delta_vs_uniform",
    "calibrated_mean_log_prob_actual", "base_mean_log_prob_actual", "uniform_mean_log_prob_actual",
    "log_delta_vs_base", "log_delta_vs_uniform",
    "calibrated_brier", "base_brier", "uniform_brier",
    "brier_improvement_vs_base", "brier_improvement_vs_uniform",
    "trusted", "source_verification", "frozen_at_jst",
    "base_q_sha256", "calibrated_q_sha256", "shadow_version",
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


def append_csv(path: Path, row: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists() and path.stat().st_size > 0
    with path.open("a", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=RESULT_FIELDS)
        if not exists:
            w.writeheader()
        w.writerow({k: row.get(k, "") for k in RESULT_FIELDS})


def canonical_q(q: Sequence[float]) -> List[str]:
    arr = np.asarray(q, dtype=float)
    if arr.shape != (37,) or not np.all(np.isfinite(arr)) or np.any(arr <= 0.0):
        raise ValueError("q must be finite, strictly positive, and shape (37,)")
    arr = arr / arr.sum()
    return [format(float(v), CANONICAL_FLOAT_FORMAT) for v in arr]


def q_sha256(q_canonical: Sequence[str]) -> str:
    raw = json.dumps(list(q_canonical), ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def parse_q(values: object) -> np.ndarray:
    if not isinstance(values, list) or len(values) != 37:
        raise ValueError("canonical q vector missing or malformed")
    arr = np.array([float(x) for x in values], dtype=float)
    if not np.all(np.isfinite(arr)) or np.any(arr <= 0.0):
        raise ValueError("canonical q vector contains invalid values")
    return arr / arr.sum()


def cfg_from_obj(obj: object) -> Optional[v2.ModelConfig]:
    return v4.cfg_from_obj(obj)


def current_q_for_cfg(x: np.ndarray, cfg: v2.ModelConfig, min_train: int = MIN_TRAIN) -> np.ndarray:
    if len(x) < min_train:
        raise ValueError("insufficient history")
    keys = list(expert_probabilities(x[:min_train]).keys())
    logw = np.zeros(len(keys), dtype=float)
    for t in range(min_train, len(x)):
        logw = v2._update_log_weights(x[:t], np.flatnonzero(x[t]), keys, logw, cfg)
    return v2._score_distribution(x, keys, logw, cfg)


def choose_next_calibration(x: np.ndarray, locked_cfg: v2.ModelConfig,
                            min_train: int = MIN_TRAIN) -> calibration.CalibrationConfig:
    _, qs = so.replay_signal(x, locked_cfg, min_train=min_train, keep_q=True)
    config_rows = calibration.precompute_rows(qs, x, min_train)
    return calibration.choose_config(config_rows, len(qs))


def _history_has_target(path: Path, target_round: int) -> bool:
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
    target_round = int(registry["target_round"])
    if _history_has_target(path, target_round):
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(registry, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")


def default_state(locked_cfg: v2.ModelConfig, start_round: int) -> Dict[str, object]:
    return {
        "shadow_version": VERSION,
        "status": "active",
        "promotion_role": PROMOTION_ROLE,
        "claim_policy": CLAIM_POLICY,
        "horizon_trusted_draws": HORIZON_TRUSTED_DRAWS,
        "protocol_started_target_round": int(start_round),
        "locked_base_version": locked_cfg.version(),
        "locked_base_config": asdict(locked_cfg),
        "calibration_algorithm_version": calibration.CALIBRATION_VERSION,
        "calibration_family_versions": [c.version() for c in calibration.PREDECLARED_CONFIGS],
        "calibration_window": calibration.CALIBRATION_WINDOW,
        "minimum_calibration_history": calibration.MIN_CALIBRATION_HISTORY,
        "selector": f"log_edge_vs_uniform + {calibration.BRIER_WEIGHT:.1f} * brier_edge_vs_uniform",
        "all_graded_draws": 0,
        "trusted_draws": 0,
        "graded_rounds": [],
        "sum_log_delta_vs_base": 0.0,
        "sum_log_delta_vs_uniform": 0.0,
        "sum_brier_improvement_vs_base": 0.0,
        "sum_brier_improvement_vs_uniform": 0.0,
        "sum_actual_mass_delta_vs_base": 0.0,
        "sum_actual_mass_delta_vs_uniform": 0.0,
        "sum_top7_delta_vs_base": 0.0,
        "rank_preserved_trusted_draws": 0,
        "last_graded_round": None,
        "current_target_round": int(start_round),
        "fixed_horizon_claim_status": "not_evaluated_until_horizon_complete",
    }


def freeze_reference(out_dir: Path, x: np.ndarray, latest_round: int, data_sha: str,
                     locked_cfg: v2.ModelConfig, source_verification: str,
                     min_train: int = MIN_TRAIN) -> Dict[str, object]:
    target_round = int(latest_round) + 1
    if target_round <= int(latest_round):
        raise RuntimeError("cannot freeze a reference for a known result")
    cfg = choose_next_calibration(x, locked_cfg, min_train=min_train)
    base_q = current_q_for_cfg(x, locked_cfg, min_train=min_train)
    calibrated_q = calibration.calibrate_q(base_q, cfg)
    if not calibration.rank_preserved(base_q, calibrated_q):
        raise RuntimeError("rank-preserving calibration invariant failed at freeze")

    base_canonical = canonical_q(base_q)
    calibrated_canonical = canonical_q(calibrated_q)
    top7 = [int(i + 1) for i in calibration.rank_order(base_q)[:7]]
    registry: Dict[str, object] = {
        "shadow_version": VERSION,
        "target_round": target_round,
        "base_data_sha256": data_sha,
        "latest_resolved_round_at_freeze": int(latest_round),
        "frozen_at_jst": v4.now_jst(),
        "source_verification_at_freeze": source_verification,
        "locked_base_version": locked_cfg.version(),
        "locked_base_config": asdict(locked_cfg),
        "calibration_algorithm_version": calibration.CALIBRATION_VERSION,
        "calibration_config_version": cfg.version(),
        "calibration_config": asdict(cfg),
        "selection_window": calibration.CALIBRATION_WINDOW,
        "minimum_selection_history": calibration.MIN_CALIBRATION_HISTORY,
        "selector": f"log_edge_vs_uniform + {calibration.BRIER_WEIGHT:.1f} * brier_edge_vs_uniform",
        "rank_preserved": True,
        "top7_numbers": top7,
        "canonical_float_format": CANONICAL_FLOAT_FORMAT,
        "hash_algorithm": HASH_ALGORITHM,
        "base_q_canonical": base_canonical,
        "base_q_sha256": q_sha256(base_canonical),
        "calibrated_q_canonical": calibrated_canonical,
        "calibrated_q_sha256": q_sha256(calibrated_canonical),
        "promotion_role": PROMOTION_ROLE,
        "claim_policy": CLAIM_POLICY,
        "horizon_trusted_draws": HORIZON_TRUSTED_DRAWS,
    }
    write_json(out_dir / REGISTRY_NAME, registry)
    append_freeze_history(out_dir / FREEZE_HISTORY_NAME, registry)
    return registry


def validate_registry(registry: Dict[str, object]) -> tuple[np.ndarray, np.ndarray]:
    if str(registry.get("shadow_version")) != VERSION:
        raise ValueError("shadow version mismatch")
    base_q = parse_q(registry.get("base_q_canonical"))
    calibrated_q = parse_q(registry.get("calibrated_q_canonical"))
    if q_sha256(canonical_q(base_q)) != str(registry.get("base_q_sha256", "")):
        raise ValueError("base q hash mismatch")
    if q_sha256(canonical_q(calibrated_q)) != str(registry.get("calibrated_q_sha256", "")):
        raise ValueError("calibrated q hash mismatch")
    if not calibration.rank_preserved(base_q, calibrated_q):
        raise ValueError("stored ranking is not preserved")
    return base_q, calibrated_q


def _record_trusted_evidence(state: Dict[str, object], row: Dict[str, object]) -> None:
    state["trusted_draws"] = int(state.get("trusted_draws", 0) or 0) + 1
    for state_key, row_key in (
        ("sum_log_delta_vs_base", "log_delta_vs_base"),
        ("sum_log_delta_vs_uniform", "log_delta_vs_uniform"),
        ("sum_brier_improvement_vs_base", "brier_improvement_vs_base"),
        ("sum_brier_improvement_vs_uniform", "brier_improvement_vs_uniform"),
        ("sum_actual_mass_delta_vs_base", "actual_mass_delta_vs_base"),
        ("sum_actual_mass_delta_vs_uniform", "actual_mass_delta_vs_uniform"),
        ("sum_top7_delta_vs_base", "top7_delta_vs_base"),
    ):
        state[state_key] = float(state.get(state_key, 0.0) or 0.0) + float(row[row_key])
    if bool(row["rank_preserved"]):
        state["rank_preserved_trusted_draws"] = int(state.get("rank_preserved_trusted_draws", 0) or 0) + 1


def grade_if_ready(out_dir: Path, registry: Dict[str, object], state: Dict[str, object],
                   latest_round: int, draw_date: str, actual_idx: np.ndarray,
                   source_verification: str, trusted: bool) -> str:
    target_round = int(registry.get("target_round", -1))
    graded_rounds = state.setdefault("graded_rounds", [])
    if target_round in graded_rounds:
        return "already_graded"
    if latest_round < target_round:
        return "waiting_for_result"
    if latest_round > target_round:
        state["status"] = "invalid_missed_prefrozen_target"
        state["missed_target_round"] = target_round
        state["missed_seen_latest_round"] = int(latest_round)
        return "missed_target_fail_closed"
    if not trusted:
        state["status"] = "awaiting_trusted_result_verification"
        state["pending_target_round"] = target_round
        state["pending_source_verification"] = source_verification
        return "awaiting_trusted_verification"

    try:
        base_q, calibrated_q = validate_registry(registry)
    except Exception as exc:
        state["status"] = "invalid_prefrozen_reference"
        state["invalid_reason"] = str(exc)
        return "invalid_reference_fail_closed"

    base = so.signal_row(base_q, actual_idx)
    calibrated = so.signal_row(calibrated_q, actual_idx)
    uniform = so.signal_row(so.UNIFORM_Q, actual_idx)
    rank_ok = calibration.rank_preserved(base_q, calibrated_q)
    row: Dict[str, object] = {
        "round": target_round,
        "draw_date": draw_date,
        "locked_base_version": registry.get("locked_base_version", ""),
        "calibration_config_version": registry.get("calibration_config_version", ""),
        "temperature": float((registry.get("calibration_config") or {}).get("temperature", 0.0)),
        "uniform_mix": float((registry.get("calibration_config") or {}).get("uniform_mix", 0.0)),
        "rank_preserved": rank_ok,
        "top7_delta_vs_base": float(calibrated["top7_hits"] - base["top7_hits"]),
        "calibrated_top7_hits": calibrated["top7_hits"],
        "base_top7_hits": base["top7_hits"],
        "calibrated_actual_mass": calibrated["actual_mass"],
        "base_actual_mass": base["actual_mass"],
        "uniform_actual_mass": uniform["actual_mass"],
        "actual_mass_delta_vs_base": float(calibrated["actual_mass"] - base["actual_mass"]),
        "actual_mass_delta_vs_uniform": float(calibrated["actual_mass"] - uniform["actual_mass"]),
        "calibrated_mean_log_prob_actual": calibrated["mean_log_prob_actual"],
        "base_mean_log_prob_actual": base["mean_log_prob_actual"],
        "uniform_mean_log_prob_actual": uniform["mean_log_prob_actual"],
        "log_delta_vs_base": float(calibrated["mean_log_prob_actual"] - base["mean_log_prob_actual"]),
        "log_delta_vs_uniform": float(calibrated["mean_log_prob_actual"] - uniform["mean_log_prob_actual"]),
        "calibrated_brier": calibrated["brier"],
        "base_brier": base["brier"],
        "uniform_brier": uniform["brier"],
        "brier_improvement_vs_base": float(base["brier"] - calibrated["brier"]),
        "brier_improvement_vs_uniform": float(uniform["brier"] - calibrated["brier"]),
        "trusted": True,
        "source_verification": source_verification,
        "frozen_at_jst": registry.get("frozen_at_jst", ""),
        "base_q_sha256": registry.get("base_q_sha256", ""),
        "calibrated_q_sha256": registry.get("calibrated_q_sha256", ""),
        "shadow_version": VERSION,
    }
    if abs(float(row["top7_delta_vs_base"])) > 1e-12 or not rank_ok:
        state["status"] = "invalid_rank_invariant_failure"
        return "rank_invariant_fail_closed"

    append_csv(out_dir / RESULTS_NAME, row)
    state["all_graded_draws"] = int(state.get("all_graded_draws", 0) or 0) + 1
    _record_trusted_evidence(state, row)
    graded_rounds.append(target_round)
    state["last_graded_round"] = target_round
    state["last_result"] = row
    state.pop("pending_target_round", None)
    state.pop("pending_source_verification", None)
    state["status"] = "active"
    if int(state.get("trusted_draws", 0) or 0) >= int(state.get("horizon_trusted_draws", HORIZON_TRUSTED_DRAWS)):
        state["status"] = "complete_fixed_horizon"
        state["fixed_horizon_claim_status"] = "requires_final_fixed_horizon_analysis"
    return "graded_trusted"


def mean_or_none(total: object, n: int) -> Optional[float]:
    if n <= 0:
        return None
    return float(total or 0.0) / float(n)


def write_report(out_dir: Path, state: Dict[str, object], registry: Dict[str, object]) -> None:
    trusted = int(state.get("trusted_draws", 0) or 0)
    horizon = int(state.get("horizon_trusted_draws", HORIZON_TRUSTED_DRAWS) or HORIZON_TRUSTED_DRAWS)
    lines = [
        "# Champion Calibration Future-OOS Shadow",
        "",
        f"- shadow: **{VERSION}**",
        f"- role: **Research diagnostic only; no Production authority**",
        f"- locked base model: **{state.get('locked_base_version', '')}**",
        f"- fixed prospective horizon: **{trusted}/{horizon} trusted draws**",
        f"- status: **{state.get('status', 'unknown')}**",
        f"- current target: **round {registry.get('target_round', 'none')}**",
        f"- pre-frozen: **{'YES' if registry else 'NO'}**",
    ]
    if registry:
        cfg = registry.get("calibration_config") or {}
        lines += [
            f"- current calibration: **{registry.get('calibration_config_version', '')}** (T={float(cfg.get('temperature', 0.0)):.2f}, uniform_mix={float(cfg.get('uniform_mix', 0.0)):.2f})",
            f"- frozen at JST: **{registry.get('frozen_at_jst', '')}**",
            f"- base q SHA-256: `{registry.get('base_q_sha256', '')}`",
            f"- calibrated q SHA-256: `{registry.get('calibrated_q_sha256', '')}`",
            f"- rank preserved: **{str(bool(registry.get('rank_preserved'))).lower()}**",
        ]
    lines += ["", "## Trusted cumulative diagnostics", ""]
    if trusted:
        lines += [
            f"- mean log delta vs locked base: **{mean_or_none(state.get('sum_log_delta_vs_base'), trusted):+.8f}**",
            f"- mean Brier improvement vs locked base: **{mean_or_none(state.get('sum_brier_improvement_vs_base'), trusted):+.8f}**",
            f"- mean log delta vs Uniform: **{mean_or_none(state.get('sum_log_delta_vs_uniform'), trusted):+.8f}**",
            f"- mean Brier improvement vs Uniform: **{mean_or_none(state.get('sum_brier_improvement_vs_uniform'), trusted):+.8f}**",
            f"- mean actual-mass delta vs Uniform: **{mean_or_none(state.get('sum_actual_mass_delta_vs_uniform'), trusted):+.8f}**",
            f"- mean Top-7 delta vs locked base: **{mean_or_none(state.get('sum_top7_delta_vs_base'), trusted):+.8f}**",
            f"- rank preserved trusted draws: **{state.get('rank_preserved_trusted_draws', 0)}/{trusted}**",
        ]
    else:
        lines.append("- 未採点")
    lines += [
        "",
        "## Claim policy",
        "",
        f"- **{CLAIM_POLICY}**",
        f"- current claim status: **{state.get('fixed_horizon_claim_status', 'not_evaluated_until_horizon_complete')}**",
        "- Interim means are descriptive only. No robust Uniform-edge claim is made before the fixed horizon is complete.",
        "- A missing or post-result reference is never reconstructed; the affected draw is fail-closed.",
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
        locked_cfg = cfg_from_obj(state.get("locked_base_config"))
        if locked_cfg is None:
            state["status"] = "invalid_locked_base_config"
            write_json(state_path, state)
            write_report(out_dir, state, registry)
            return {"status": state["status"], "latest_round": latest_round}
    else:
        locked_cfg = v2.load_champion(champion_file)
        state = default_state(locked_cfg, latest_round + 1)
        state["production_champion_version_at_protocol_start"] = locked_cfg.version()
        state["protocol_started_at_jst"] = v4.now_jst()

    grade_action = "none"
    if registry:
        target = int(registry.get("target_round", -1))
        if latest_round >= target:
            actual_idx = np.flatnonzero(x[-1]) if latest_round == target else np.array([], dtype=int)
            grade_action = grade_if_ready(
                out_dir, registry, state, latest_round, latest_date, actual_idx,
                verification, trusted,
            )

    complete = str(state.get("status")) == "complete_fixed_horizon"
    if not complete:
        current_target = int(registry.get("target_round", -1)) if registry else -1
        need_freeze = not registry or current_target <= latest_round
        if need_freeze:
            # If a result is known but still awaiting trusted verification, do not jump ahead.
            if registry and current_target == latest_round and grade_action == "awaiting_trusted_verification":
                pass
            elif registry and current_target < latest_round and grade_action == "missed_target_fail_closed":
                registry = freeze_reference(out_dir, x, latest_round, data_sha, locked_cfg, verification, min_train)
                state["current_target_round"] = int(registry["target_round"])
            elif not registry or grade_action in ("graded_trusted", "already_graded"):
                registry = freeze_reference(out_dir, x, latest_round, data_sha, locked_cfg, verification, min_train)
                state["current_target_round"] = int(registry["target_round"])

    state["shadow_version"] = VERSION
    state["last_run_jst"] = v4.now_jst()
    state["latest_seen_round"] = int(latest_round)
    state["latest_data_sha256"] = data_sha
    state["latest_source_verification"] = verification
    state["latest_source_trusted"] = bool(trusted)
    state["last_grade_action"] = grade_action
    state["promotion_role"] = PROMOTION_ROLE
    state["claim_policy"] = CLAIM_POLICY
    write_json(state_path, state)
    write_report(out_dir, state, registry)
    return {
        "status": state.get("status"),
        "latest_round": latest_round,
        "target_round": registry.get("target_round") if registry else None,
        "trusted_draws": state.get("trusted_draws", 0),
        "horizon_trusted_draws": state.get("horizon_trusted_draws", HORIZON_TRUSTED_DRAWS),
        "grade_action": grade_action,
        "calibration_config_version": registry.get("calibration_config_version") if registry else None,
        "frozen_at_jst": registry.get("frozen_at_jst") if registry else None,
        "base_q_sha256": registry.get("base_q_sha256") if registry else None,
        "calibrated_q_sha256": registry.get("calibrated_q_sha256") if registry else None,
        "claim_status": state.get("fixed_horizon_claim_status"),
        "promotion_role": PROMOTION_ROLE,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Pre-frozen Future-OOS shadow for Champion ranking calibration")
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
