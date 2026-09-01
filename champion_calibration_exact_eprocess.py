#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

import numpy as np

import champion_calibration_oos as shadow
import loto7_v4_runner as v4

VERSION = "champion-calibration-exact-eprocess-v1"
HORIZON_TRUSTED_DRAWS = 26
N_NUMBERS = 37
DRAW_SIZE = 7
FAMILY_ALPHA = 0.05
ENDPOINTS = ("log_score", "brier_improvement")
ENDPOINT_ALPHA = FAMILY_ALPHA / len(ENDPOINTS)
E_VALUE_THRESHOLD = 1.0 / ENDPOINT_ALPHA  # 40.0, conservative Bonferroni family control.
LAMBDAS: Tuple[float, ...] = (0.25, 0.50, 1.00, 2.00, 4.00)
NULL_HYPOTHESIS = (
    "conditional_on_the_past_each_future_winning_7_set_is_uniform_over_all_C(37,7)_subsets"
)
CLAIM = "robust_uniform_proper_score_edge"
REGISTRATION_NAME = "champion_calibration_exact_eprocess_registration.json"
STATE_NAME = "champion_calibration_exact_eprocess_state.json"
REPORT_NAME = "champion_calibration_exact_eprocess_report.md"


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


def read_jsonl(path: Path) -> List[Dict[str, object]]:
    if not path.exists():
        return []
    rows: List[Dict[str, object]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def read_results(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _logaddexp(a: float, b: float) -> float:
    if math.isinf(a) and a < 0:
        return b
    if math.isinf(b) and b < 0:
        return a
    m = max(a, b)
    return m + math.log(math.exp(a - m) + math.exp(b - m))


def log_elementary_symmetric_mean(log_weights: Sequence[float], k: int) -> float:
    """log mean product of k weights over all k-subsets, computed exactly by DP."""
    n = len(log_weights)
    if not 0 <= k <= n:
        raise ValueError("k must be in [0, n]")
    if k == 0:
        return 0.0
    dp = [float("-inf")] * (k + 1)
    dp[0] = 0.0
    seen = 0
    for lw in log_weights:
        seen += 1
        for j in range(min(k, seen), 0, -1):
            dp[j] = _logaddexp(dp[j], dp[j - 1] + float(lw))
    return float(dp[k] - math.log(math.comb(n, k)))


def sample_mean_sd(values: Sequence[float], k: int = DRAW_SIZE) -> float:
    """Null SD of a simple-random-sample-without-replacement sample mean."""
    arr = np.asarray(values, dtype=float)
    n = int(arr.size)
    if n <= 1 or not 1 <= k <= n:
        raise ValueError("invalid population/sample size")
    pop_var = float(np.mean((arr - float(np.mean(arr))) ** 2))
    if pop_var <= 0.0:
        return 0.0
    fpc = (n - k) / (n - 1)
    return math.sqrt(fpc * pop_var / k)


def exact_standardized_log_mgf(values: Sequence[float], observed_metric: float,
                               coefficient: float, lam: float,
                               k: int = DRAW_SIZE) -> Dict[str, float]:
    """
    Exact MGF for a metric of form constant + coefficient * sample_mean(values).
    Centering removes the constant, so only the population values are required.
    """
    arr = np.asarray(values, dtype=float)
    if arr.ndim != 1 or arr.size < k or not np.all(np.isfinite(arr)):
        raise ValueError("values must be a finite one-dimensional population")
    mean_v = float(np.mean(arr))
    sd_mean = sample_mean_sd(arr, k=k)
    metric_sd = abs(float(coefficient)) * sd_mean
    null_mean = float(coefficient) * mean_v
    if metric_sd <= 1e-15:
        return {
            "null_mean_without_constant": null_mean,
            "metric_sd": 0.0,
            "standardized_observed": 0.0,
            "log_mgf": 0.0,
            "log_factor": 0.0,
            "factor": 1.0,
        }
    centered = arr - mean_v
    scale = float(coefficient) / (float(k) * metric_sd)
    log_weights = [float(lam) * scale * float(x) for x in centered]
    log_mgf = log_elementary_symmetric_mean(log_weights, k)
    standardized_observed = float(observed_metric) / metric_sd
    log_factor = float(lam) * standardized_observed - log_mgf
    return {
        "null_mean_without_constant": null_mean,
        "metric_sd": metric_sd,
        "standardized_observed": standardized_observed,
        "log_mgf": log_mgf,
        "log_factor": log_factor,
        "factor": math.exp(min(700.0, log_factor)),
    }


def log_endpoint_terms(q: np.ndarray, observed_log_edge: float, lam: float) -> Dict[str, float]:
    q = np.asarray(q, dtype=float)
    q = q / q.sum()
    values = np.log(float(N_NUMBERS) * q)
    null_mean = float(np.mean(values))
    centered_observed = float(observed_log_edge) - null_mean
    out = exact_standardized_log_mgf(values, centered_observed, 1.0, lam, DRAW_SIZE)
    out["null_mean"] = null_mean
    out["observed_metric"] = float(observed_log_edge)
    return out


def brier_endpoint_terms(q: np.ndarray, observed_improvement: float, lam: float) -> Dict[str, float]:
    q = np.asarray(q, dtype=float)
    q = q / q.sum()
    constant = -float(np.sum(q * q)) - (1.0 / N_NUMBERS)
    null_mean = (1.0 / N_NUMBERS) - float(np.sum(q * q))
    centered_observed = float(observed_improvement) - null_mean
    out = exact_standardized_log_mgf(q, centered_observed, 2.0, lam, DRAW_SIZE)
    out["constant"] = constant
    out["null_mean"] = null_mean
    out["observed_metric"] = float(observed_improvement)
    return out


def mixture_log_e(component_logs: Dict[str, float]) -> float:
    vals = [float(component_logs[str(lam)]) for lam in LAMBDAS]
    m = max(vals)
    return m + math.log(sum(math.exp(v - m) for v in vals) / len(vals))


def safe_exp(log_value: float) -> float:
    return math.exp(min(700.0, float(log_value)))


def register_if_missing(out_dir: Path, shadow_registry: Dict[str, object]) -> Dict[str, object]:
    path = out_dir / REGISTRATION_NAME
    existing = load_json(path, {})
    if existing:
        return existing
    target = int(shadow_registry.get("target_round", -1))
    if target < 1:
        raise RuntimeError("cannot preregister without an active prefrozen shadow target")
    registration = {
        "version": VERSION,
        "registered_at_jst": v4.now_jst(),
        "starts_target_round": target,
        "initial_calibration_q_sha256": shadow_registry.get("calibrated_q_sha256", ""),
        "initial_base_q_sha256": shadow_registry.get("base_q_sha256", ""),
        "shadow_protocol_version": shadow.VERSION,
        "horizon_trusted_draws": HORIZON_TRUSTED_DRAWS,
        "null_hypothesis": NULL_HYPOTHESIS,
        "endpoint_family": list(ENDPOINTS),
        "family_alpha": FAMILY_ALPHA,
        "endpoint_alpha": ENDPOINT_ALPHA,
        "e_value_threshold_each": E_VALUE_THRESHOLD,
        "lambda_mixture": list(LAMBDAS),
        "mgf_method": "exact_without_replacement_elementary_symmetric_dp_on_each_prefrozen_q",
        "primary_claim": CLAIM,
        "claim_rule": {
            "trusted_draws_equal_horizon": True,
            "rank_preserved_all_trusted_draws": True,
            "mean_log_edge_vs_uniform_positive": True,
            "mean_brier_improvement_vs_uniform_positive": True,
            "log_score_mixture_e_value_at_least": E_VALUE_THRESHOLD,
            "brier_improvement_mixture_e_value_at_least": E_VALUE_THRESHOLD,
        },
        "interim_claims_allowed": False,
        "promotion_role": "diagnostic_only",
    }
    write_json(path, registration)
    return registration


def _freeze_by_round(freeze_rows: Iterable[Dict[str, object]]) -> Dict[int, Dict[str, object]]:
    out: Dict[int, Dict[str, object]] = {}
    for rec in freeze_rows:
        try:
            r = int(rec.get("target_round", -1))
        except Exception:
            continue
        if r > 0 and r not in out:
            out[r] = rec
    return out


def rebuild_state(out_dir: Path, registration: Dict[str, object]) -> Dict[str, object]:
    freeze_rows = read_jsonl(out_dir / shadow.FREEZE_HISTORY_NAME)
    results = read_results(out_dir / shadow.RESULTS_NAME)
    frozen = _freeze_by_round(freeze_rows)
    start_round = int(registration["starts_target_round"])

    component_logs = {
        "log_score": {str(lam): 0.0 for lam in LAMBDAS},
        "brier_improvement": {str(lam): 0.0 for lam in LAMBDAS},
    }
    processed: List[int] = []
    audit_rows: List[Dict[str, object]] = []
    sum_log_edge = 0.0
    sum_brier_improvement = 0.0
    sum_mass_edge = 0.0
    rank_ok_count = 0

    trusted_rows = []
    for row in results:
        try:
            r = int(row.get("round", -1))
        except Exception:
            continue
        if r >= start_round and str(row.get("trusted", "")).lower() == "true":
            trusted_rows.append((r, row))
    trusted_rows.sort(key=lambda x: x[0])

    for r, row in trusted_rows:
        if r in processed:
            raise RuntimeError(f"duplicate trusted result for round {r}")
        ref = frozen.get(r)
        if not ref:
            raise RuntimeError(f"trusted round {r} has no prefrozen reference")
        if str(ref.get("calibrated_q_sha256", "")) != str(row.get("calibrated_q_sha256", "")):
            raise RuntimeError(f"calibrated q hash mismatch for round {r}")
        q = shadow.parse_q(ref.get("calibrated_q_canonical"))
        observed_log = float(row["log_delta_vs_uniform"])
        observed_brier = float(row["brier_improvement_vs_uniform"])
        observed_mass = float(row["actual_mass_delta_vs_uniform"])
        rank_ok = str(row.get("rank_preserved", "")).lower() == "true" and abs(float(row["top7_delta_vs_base"])) <= 1e-12

        draw_audit: Dict[str, object] = {
            "round": r,
            "calibrated_q_sha256": ref.get("calibrated_q_sha256", ""),
            "observed_log_edge_vs_uniform": observed_log,
            "observed_brier_improvement_vs_uniform": observed_brier,
            "observed_actual_mass_delta_vs_uniform": observed_mass,
            "rank_preserved": rank_ok,
            "log_factors": {},
            "brier_factors": {},
        }
        for lam in LAMBDAS:
            lt = log_endpoint_terms(q, observed_log, lam)
            bt = brier_endpoint_terms(q, observed_brier, lam)
            component_logs["log_score"][str(lam)] += float(lt["log_factor"])
            component_logs["brier_improvement"][str(lam)] += float(bt["log_factor"])
            draw_audit["log_factors"][str(lam)] = lt
            draw_audit["brier_factors"][str(lam)] = bt

        sum_log_edge += observed_log
        sum_brier_improvement += observed_brier
        sum_mass_edge += observed_mass
        if rank_ok:
            rank_ok_count += 1
        processed.append(r)
        audit_rows.append(draw_audit)

    n = len(processed)
    log_mix = mixture_log_e(component_logs["log_score"])
    brier_mix = mixture_log_e(component_logs["brier_improvement"])
    complete = n == HORIZON_TRUSTED_DRAWS
    claim = bool(
        complete
        and rank_ok_count == n
        and (sum_log_edge / n) > 0.0
        and (sum_brier_improvement / n) > 0.0
        and log_mix >= math.log(E_VALUE_THRESHOLD)
        and brier_mix >= math.log(E_VALUE_THRESHOLD)
    ) if n else False

    return {
        "version": VERSION,
        "registration_version": registration.get("version"),
        "registered_at_jst": registration.get("registered_at_jst"),
        "starts_target_round": start_round,
        "horizon_trusted_draws": HORIZON_TRUSTED_DRAWS,
        "trusted_draws_processed": n,
        "processed_rounds": processed,
        "rank_preserved_trusted_draws": rank_ok_count,
        "mean_log_edge_vs_uniform": (sum_log_edge / n) if n else None,
        "mean_brier_improvement_vs_uniform": (sum_brier_improvement / n) if n else None,
        "mean_actual_mass_delta_vs_uniform": (sum_mass_edge / n) if n else None,
        "component_log_e_values": component_logs,
        "log_score_mixture_log_e_value": log_mix,
        "log_score_mixture_e_value": safe_exp(log_mix),
        "brier_mixture_log_e_value": brier_mix,
        "brier_mixture_e_value": safe_exp(brier_mix),
        "e_value_threshold_each": E_VALUE_THRESHOLD,
        "family_alpha": FAMILY_ALPHA,
        "endpoint_alpha": ENDPOINT_ALPHA,
        "fixed_horizon_complete": complete,
        "claim_name": CLAIM,
        "claim_confirmed": claim,
        "claim_status": "confirmed" if claim else ("not_confirmed_at_fixed_horizon" if complete else "not_evaluated_until_horizon_complete"),
        "interim_values_are_descriptive_only": not complete,
        "null_hypothesis": NULL_HYPOTHESIS,
        "audit": audit_rows,
        "updated_at_jst": v4.now_jst(),
        "promotion_role": "diagnostic_only",
    }


def write_report(out_dir: Path, registration: Dict[str, object], state: Dict[str, object]) -> None:
    n = int(state.get("trusted_draws_processed", 0) or 0)
    def fmt(x: object, digits: int = 8) -> str:
        return "未採点" if x is None else f"{float(x):+.{digits}f}"
    lines = [
        "# Champion Calibration Exact Future-OOS E-Process",
        "",
        f"- version: **{VERSION}**",
        f"- preregistered at JST: **{registration.get('registered_at_jst', '')}**",
        f"- starts target: **round {registration.get('starts_target_round')}**",
        f"- fixed horizon: **{n}/{HORIZON_TRUSTED_DRAWS} trusted draws**",
        f"- null: **{NULL_HYPOTHESIS}**",
        f"- exact MGF: **without-replacement elementary-symmetric DP**",
        f"- lambda mixture: **{', '.join(str(x) for x in LAMBDAS)}**",
        f"- endpoint threshold: **e >= {E_VALUE_THRESHOLD:.0f} each**",
        f"- family alpha: **{FAMILY_ALPHA:.3f}** (two-endpoint Bonferroni registration)",
        "",
        "## Current evidence",
        "",
        f"- mean log edge vs Uniform: **{fmt(state.get('mean_log_edge_vs_uniform'))}**",
        f"- log-score mixture e-value: **{float(state.get('log_score_mixture_e_value', 1.0)):.8f}**",
        f"- mean Brier improvement vs Uniform: **{fmt(state.get('mean_brier_improvement_vs_uniform'))}**",
        f"- Brier mixture e-value: **{float(state.get('brier_mixture_e_value', 1.0)):.8f}**",
        f"- mean actual-mass delta vs Uniform: **{fmt(state.get('mean_actual_mass_delta_vs_uniform'))}**",
        f"- rank preserved: **{state.get('rank_preserved_trusted_draws', 0)}/{n}**",
        "",
        "## Fixed claim rule",
        "",
        f"A `{CLAIM}` claim is allowed only after exactly {HORIZON_TRUSTED_DRAWS} trusted draws and only if:",
        f"1. ranking is preserved on all trusted draws;",
        f"2. mean log edge vs Uniform is positive;",
        f"3. mean Brier improvement vs Uniform is positive;",
        f"4. log-score mixture e-value is at least {E_VALUE_THRESHOLD:.0f};",
        f"5. Brier mixture e-value is at least {E_VALUE_THRESHOLD:.0f}.",
        "",
        f"- current claim status: **{state.get('claim_status')}**",
        "- Interim e-values and means are diagnostics only; this protocol has no Production promotion authority.",
    ]
    (out_dir / REPORT_NAME).write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(out_dir: Path) -> Dict[str, object]:
    shadow_registry = load_json(out_dir / shadow.REGISTRY_NAME, {})
    if not shadow_registry:
        raise RuntimeError("Champion calibration OOS registry is missing")
    registration = register_if_missing(out_dir, shadow_registry)
    state = rebuild_state(out_dir, registration)
    write_json(out_dir / STATE_NAME, state)
    write_report(out_dir, registration, state)
    return state


def main() -> int:
    ap = argparse.ArgumentParser(description="Exact e-process for the Champion calibration Future-OOS shadow")
    ap.add_argument("--out-dir", type=Path, default=Path("loto7_agent_output"))
    args = ap.parse_args()
    state = run(args.out_dir)
    print(json.dumps({
        "version": state["version"],
        "trusted_draws_processed": state["trusted_draws_processed"],
        "horizon_trusted_draws": state["horizon_trusted_draws"],
        "log_score_mixture_e_value": state["log_score_mixture_e_value"],
        "brier_mixture_e_value": state["brier_mixture_e_value"],
        "claim_status": state["claim_status"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
