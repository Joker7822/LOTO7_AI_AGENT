#!/usr/bin/env python3
"""Advanced validation laboratory: rigorous diagnostics, never Production.

Two strictly separated layers:
(1) Reused history: simultaneous two-model fair-world max correction,
    paired moving-block bootstrap, and transparent stability diagnostics.
(2) After pre-draw SHA-frozen NEW results: exact single-stream e-process
    under the conditional null of an independent uniform 7-of-37 lottery.

Only reads the existing fifth-expert frozen ledger via its own strict audit.
Its own statistical code, hypothesis and inference plan are registered before
round 701; none of the frozen predictors/ledgers can be rewritten.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping

import numpy as np

import accuracy_extension_agent as candidate
import continuous_learning_agent as ledger
import predictive_expert_agent as incumbent
from joint_set_v2_model import N_NUMBERS, PICKS, UNIFORM_INCLUSION
from loto7_evolving_agent import fingerprint_file

VERSION = "advanced-validation-lab-v1"
REG = "advanced_validation_lab_registration.json"
SUMMARY = "advanced_validation_lab_summary.json"
REPORT = "advanced_validation_lab_report.md"
JST = timezone(timedelta(hours=9))
HORIZON = 60
WORLD_COUNT = 32
WORLD_SEED = 874902
BOOTSTRAPS = 2048
BLOCK_LENGTH = 4
BOOTSTRAP_SEED = 102817
E_ALPHA = 0.05
E_THRESHOLD = 1 / E_ALPHA
FIRST_FUTURE = 701
EXPECTED_HYPOTHESIS = "one_predeclared_fifth_expert_prefix_frozen_inclusion_mass"
FAIR_NULL = "conditionally_independent_uniform_seven_of_thirty_seven"


def canonical(data: Mapping[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


def sha(data: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical(data).encode()).hexdigest()


def manifest(root: Path, candidate_registration: dict) -> dict:
    my_code = root / "advanced_validation_lab.py"
    if not my_code.is_file():
        raise ValueError("missing registered lab source code")
    cfg = {
        "version": VERSION,
        "lab_code_sha256": hashlib.sha256(my_code.read_bytes()).hexdigest(),
        "fifth_expert_manifest_sha256": candidate_registration["algorithm_manifest"]["manifest_sha256"],
        "first_prospective_target": FIRST_FUTURE,
        "historical_models": ["original_four_expert", "shrunken_lag_one_five_expert"],
        "historical_horizon": HORIZON,
        "matched_fair_worlds": WORLD_COUNT,
        "matched_fair_seed": WORLD_SEED,
        "historical_max_statistic": "max(mean_log_edge_four,mean_log_edge_five)",
        "paired_circular_block_bootstraps": BOOTSTRAPS,
        "paired_block_length": BLOCK_LENGTH,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "single_future_e_hypothesis": EXPECTED_HYPOTHESIS,
        "conditional_fair_null": FAIR_NULL,
        "future_e_alpha": E_ALPHA,
        "future_e_threshold": E_THRESHOLD,
        "e_multiplier": "sum_of_frozen_p_for_actual_seven_over_49_37",
        "e_process_is_self_financing_under_fair_conditional_lottery": True,
        "auto_promote": False,
        "inference_separated_from_exploratory_historical_screen": True,
    }
    cfg["manifest_sha256"] = sha(cfg)
    return cfg


def register(root: Path, out: Path, candidate_registration: dict,
             latest_round: int, clock: datetime) -> dict:
    fixed = manifest(root, candidate_registration)
    current = ledger.read_json(out / REG)
    if current:
        if (current.get("version") != VERSION
                or current.get("algorithm_manifest") != fixed
                or current.get("promotion_role") != "read_only_diagnostic"
                or current.get("registered_when_latest_round", FIRST_FUTURE) >= FIRST_FUTURE):
            raise ValueError("statistical protocol drift from original registration")
        return current
    if latest_round >= FIRST_FUTURE:
        raise ValueError("statistical e-process registration occurred after first possible outcome")
    rec = {
        "version": VERSION, "registered_at_jst": clock.isoformat(timespec="seconds"),
        "registered_when_latest_round": latest_round,
        "future_hypothesis_first_target": FIRST_FUTURE,
        "promotion_role": "read_only_diagnostic",
        "algorithm_manifest": fixed,
        "no_unplanned_model_family_additions": True,
    }
    ledger.write_json(out / REG, rec)
    return rec


def paired_circular_block_ci(four: np.ndarray, five: np.ndarray) -> dict:
    if four.shape != five.shape or len(four) != HORIZON or not np.isfinite(four - five).all():
        raise ValueError("paired chronological model comparison requires aligned 60 draws")
    differences = five - four
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    nblocks = math.ceil(HORIZON / BLOCK_LENGTH)
    start = rng.integers(0, HORIZON, size=(BOOTSTRAPS, nblocks))
    offsets = np.arange(BLOCK_LENGTH, dtype=int)
    idx = ((start[:, :, None] + offsets) % HORIZON).reshape(BOOTSTRAPS, -1)[:, :HORIZON]
    draws = differences[idx].mean(axis=1)
    return {
        "mean_five_minus_four": float(differences.mean()),
        "block_length": BLOCK_LENGTH,
        "bootstrap_repetitions": BOOTSTRAPS,
        "low95": float(np.quantile(draws, 0.025)),
        "high95": float(np.quantile(draws, 0.975)),
        "historic_exploratory_only": True,
    }


def historical_stability(four: np.ndarray, five: np.ndarray) -> dict:
    d = five - four
    if len(d) != HORIZON:
        raise ValueError("predeclared 60-draw window needed")
    chunks = [float(np.mean(d[i:i + 15])) for i in range(0, HORIZON, 15)]
    # One-sided bounded CUSUM of recent underperformance; a dashboard diagnostic,
    # *not* a prespecified detection test or evidence of nonstationarity.
    allowance = 0.0001
    path = []
    current = 0.0
    for edge in d:
        current = max(0.0, current - float(edge) - allowance)
        path.append(round(current, 12))
    return {
        "fifteen_draw_mean_edges_five_minus_four": chunks,
        "worst_fifteen_draw_edge": min(chunks),
        "best_fifteen_draw_edge": max(chunks),
        "underperformance_cusum_heuristic": path[-1],
        "max_cusum_heuristic": max(path),
        "allowance": allowance,
        "not_a_formal_drift_significance_test": True,
    }


def historical_research(x: np.ndarray, *, worlds: int = WORLD_COUNT) -> dict:
    if worlds != WORLD_COUNT:
        raise ValueError("must rerun full preregistered fair-world budget")
    four, rows_four = incumbent.walk(x, min_train=100, last_n=HORIZON)
    five, rows_five, _ = candidate.walk(x, last_n=HORIZON)
    if ([int(r["round_index"]) for r in rows_four] !=
            [int(r["round"]) for r in rows_five]):
        raise ValueError("four/five prior-only evaluation target rounds differ")
    edges_four = np.array([float(r["scout_log_edge"]) for r in rows_four])
    edges_five = np.array([float(r["log_edge"]) for r in rows_five])
    raw_max = max(float(edges_four.mean()), float(edges_five.mean()))
    null_max, null_four, null_five = [], [], []
    for i in range(worlds):
        synthetic = incumbent.synthetic_fair_history(len(x), WORLD_SEED + 7919 * i)
        four_null, _ = incumbent.walk(synthetic, min_train=100, last_n=HORIZON, retain_rows=False)
        five_null, _, _ = candidate.walk(synthetic, last_n=HORIZON)
        a, b = float(four_null["mean_log_edge_vs_uniform"]), float(five_null["mean_log_edge"])
        null_four.append(a)
        null_five.append(b)
        null_max.append(max(a, b))
    p_empirical = (1 + sum(v >= raw_max - 1e-15 for v in null_max)) / (worlds + 1)
    return {
        "scope": "reused_history_exploratory_not_independent_evidence",
        "round_start": rows_four[0]["round_index"],
        "round_end": rows_four[-1]["round_index"],
        "rounds": HORIZON,
        "uniform_expected_top7": PICKS * PICKS / N_NUMBERS,
        "original_four": {
            "mean_log_edge": float(edges_four.mean()),
            "mean_brier_edge": four["mean_brier_edge_vs_uniform"],
            "mean_top7_hits": four["mean_top7_hits"],
        },
        "candidate_five": {
            "mean_log_edge": float(edges_five.mean()),
            "mean_brier_edge": five["mean_brier_edge"],
            "mean_top7_hits": five["mean_top7_hits"],
        },
        "paired_block_bootstrap": paired_circular_block_ci(edges_four, edges_five),
        "stability_diagnostics": historical_stability(edges_four, edges_five),
        "matched_full_budget_fair_draws": {
            "worlds": worlds,
            "seed": WORLD_SEED,
            "family": ["original_four", "candidate_five"],
            "observed_max_log_edge": raw_max,
            "fair_world_max_mean": float(np.mean(null_max)),
            "fair_world_max_p95": float(np.quantile(null_max, 0.95)),
            "max_statistic_selection_adjusted_empirical_tail_p": p_empirical,
            "minimum_possible_empirical_p": 1 / (worlds + 1),
            "same_synthetic_draws_and_full_algorithm_per_world": True,
            "p_value_exploratory_not_confirmatory": True,
        },
        "conclusion": "not_authorized_to_choose_a_model_from_reused_history",
    }


def frozen_multiplier(inclusion: np.ndarray, actual_indices: np.ndarray) -> float:
    p = np.asarray(inclusion, dtype=float)
    actual = np.asarray(actual_indices, dtype=int)
    if (p.shape != (N_NUMBERS,) or not np.isfinite(p).all()
            or np.any(p <= 0) or np.any(p >= 1)
            or not np.isclose(p.sum(), PICKS, atol=1e-9)
            or actual.shape != (PICKS,) or np.any(actual < 0)
            or np.any(actual >= N_NUMBERS) or len(set(actual.tolist())) != PICKS):
        raise ValueError("e-multiplier requires a prior frozen, valid 7-of-37 marginal vector")
    payout = float(p[actual].sum())
    # Under the conditional fair null E[I_n | past] = 7/37, so
    # E[sum_{n in actual} p_n | past] = (7/37) * sum_n p_n = 49/37.
    # This is exact without independence among the 37 inclusion indicators.
    result = payout / (PICKS * PICKS / N_NUMBERS)
    if not np.isfinite(result) or result <= 0:
        raise ValueError("non-positive exact fair-null e-factor")
    return result


def future_e_process(freezes: list[dict], grades: list[dict]) -> dict:
    if len(grades) > len(freezes):
        raise ValueError("grade count exceeds pre-frozen predictions")
    log_product = 0.0
    running_max = 1.0
    points = []
    for i, grade in enumerate(grades):
        frozen = freezes[i]
        if (int(grade["target_round"]) != FIRST_FUTURE + i
                or int(frozen["target_round"]) != FIRST_FUTURE + i
                or grade.get("frozen_record_sha256") != frozen.get("record_sha256")
                or grade.get("source_verification") != candidate.SOURCE_TRUST):
            raise ValueError("prospective e-process must use trusted pre-frozen paired records")
        p = np.array([float(q) for q in frozen["inclusion_p_canonical"]])
        observed = np.array([int(n) - 1 for n in grade["actual_numbers"]])
        multiplier = frozen_multiplier(p, observed)
        log_product += math.log(multiplier)
        level = math.exp(log_product) if log_product < 690 else math.inf
        if not math.isfinite(level):
            raise ValueError("e-value numerical overflow; fail closed")
        running_max = max(running_max, level)
        points.append({
            "round": int(grade["target_round"]),
            "factor": round(multiplier, 12),
            "e_value": round(level, 12),
        })
    return {
        "hypothesis": EXPECTED_HYPOTHESIS,
        "conditional_null": FAIR_NULL,
        "future_only": True,
        "verified_prefrozen_draws": len(grades),
        "current_e_value": math.exp(log_product),
        "max_e_value": running_max,
        "predeclared_alpha": E_ALPHA,
        "ville_threshold": E_THRESHOLD,
        "threshold_crossed": running_max >= E_THRESHOLD,
        "ongoing_descriptive_not_auto_promotion": True,
        "series": points,
    }


def run(root: Path, out: Path, *, now: datetime | None = None) -> dict:
    root, out = root.resolve(), out.resolve()
    clock = (now or datetime.now(JST)).astimezone(JST)
    x, clean, latest = ledger.validated_draws(root / "loto7.csv")
    candidate_reg = ledger.read_json(out / candidate.REG, required=True)
    if (candidate_reg.get("algorithm_manifest") != candidate.manifest(root)
            or candidate_reg.get("start_target_round") != FIRST_FUTURE
            or candidate_reg.get("promotion_role") != "diagnostic_only"):
        raise ValueError("candidate algorithm SHA or research authority changed")
    lab_reg = register(root, out, candidate_reg, latest, clock)
    freezes, grades, _registry, state = candidate.audit(out, candidate_reg, x, clean)
    if state.get("trusted_draws") != len(grades):
        raise ValueError("candidate graded state absent or does not match audited records")
    if any(g["target_round"] > latest for g in grades):
        raise ValueError("future outcomes do not exist in current historical CSV")
    current_data_sha = fingerprint_file(root / "loto7.csv")
    old = ledger.read_json(out / SUMMARY)
    if (old.get("historical_data_sha256") == current_data_sha
            and old.get("registered_statistical_manifest_sha256") == lab_reg["algorithm_manifest"]["manifest_sha256"]
            and old.get("historical_exploratory", {}).get("matched_full_budget_fair_draws", {}).get("worlds") == WORLD_COUNT):
        historical = old["historical_exploratory"]
    else:
        historical = historical_research(x)
    future = future_e_process(freezes, grades)
    result = {
        "version": VERSION, "registered_statistical_manifest_sha256": lab_reg["algorithm_manifest"]["manifest_sha256"],
        "source_code_frozen": True, "source_model_manifest_sha256": candidate_reg["algorithm_manifest"]["manifest_sha256"],
        "historical_data_sha256": current_data_sha,
        "latest_seen_round": latest,
        "candidate_status": state.get("status", "unknown"),
        "historical_exploratory": historical, "future_e_monitor": future,
        "scope": "research_only", "automatic_model_selection": False,
        "production_changed": False, "champion_changed": False,
        "registered_existing_shadows_changed": False,
        "formal_p_value_from_reused_history": False,
        "claim": (
            "Matched model-selection null and moving-block bootstrap are exploratory on already "
            "mined history. A single predeclared future-only e-process tests the conditional "
            "uniform 7-of-37 null using exactly pre-frozen marginal weights; even threshold "
            "crossing would require separate review and cannot promote Production."
        ),
    }
    ledger.write_json(out / SUMMARY, result)
    hist = historical
    e = future
    report = [
        "# Advanced Validation Laboratory — Scientific Research Gate", "",
        f"- Registered lab code SHA: **{lab_reg['algorithm_manifest']['lab_code_sha256']}**",
        f"- Candidate code SHA protocol: **{candidate_reg['algorithm_manifest']['manifest_sha256']}**",
        "- Scope: **research_only**; no Champion / Production / frozen-shadow writes",
        f"- Used history: **{hist['round_start']}–{hist['round_end']}** (ALREADY REUSED)",
        f"- Original four log edge: **{hist['original_four']['mean_log_edge']:+.9f}**",
        f"- New five log edge: **{hist['candidate_five']['mean_log_edge']:+.9f}**",
        f"- Paired 4-draw block-bootstrap 95% exploratory interval (five minus four): "
        f"**[{hist['paired_block_bootstrap']['low95']:+.9f}, "
        f"{hist['paired_block_bootstrap']['high95']:+.9f}]**",
        f"- Selection-corrected max(4,5) fair-world empirical tail (n={WORLD_COUNT}): "
        f"**{hist['matched_full_budget_fair_draws']['max_statistic_selection_adjusted_empirical_tail_p']:.4f}**",
        f"- Four 15-draw stability blocks: **{hist['stability_diagnostics']['fifteen_draw_mean_edges_five_minus_four']}**",
        "",
        "## Genuine prospectively pre-frozen evidence (NO future grades are invented)",
        f"- New trustworthy graded targets: **{e['verified_prefrozen_draws']}**",
        f"- E-value under conditional uniform 7-of-37 null: **{e['current_e_value']:.8f}**",
        f"- Historical max of prospective e-value: **{e['max_e_value']:.8f}**; "
        f"predeclared threshold: **{E_THRESHOLD:.0f}**",
        f"- Threshold crossed: **{e['threshold_crossed']}**",
        "",
        "The e-factor is sum(p_n over the actual 7 numbers) / (49/37). Under the",
        "fair independent 7-of-37 null its conditional expectation is exactly 1;",
        "multiplying the future-only factors forms a nonnegative test martingale.",
        "This is one predeclared inference target; it does not prove ability to win",
        "or superiority over other systems. Previous model selection was on explored",
        "historical draws and cannot retroactively justify any inference or promotion.",
        "The original registered prediction ledger, Production and Champion are untouched.",
        "",
    ]
    out.mkdir(parents=True, exist_ok=True)
    (out / REPORT).write_text("\n".join(report), encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Advanced scientific validation; read-only diagnostics")
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--out-dir", type=Path, default=Path("loto7_agent_output"))
    args = parser.parse_args()
    data = run(args.repo_root, args.out_dir)
    h = data["historical_exploratory"]
    e = data["future_e_monitor"]
    print(json.dumps({
        "version": VERSION, "historical_four_log_edge": h["original_four"]["mean_log_edge"],
        "historical_five_log_edge": h["candidate_five"]["mean_log_edge"],
        "historical_selection_corrected_p_exploratory_only": h["matched_full_budget_fair_draws"]["max_statistic_selection_adjusted_empirical_tail_p"],
        "future_trusted_draws": e["verified_prefrozen_draws"],
        "future_e": e["current_e_value"], "promotion_eligible": False,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
