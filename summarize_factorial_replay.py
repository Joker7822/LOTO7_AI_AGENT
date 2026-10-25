#!/usr/bin/env python3
"""Independent reconciliation and paired diagnostic windows for historical replay.

No Production write, holdout registration, Champion choice, or promotion authority.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np

WINDOWS = (60, 120, 600)
ARM_COMPARISONS = {
    "signal_effect_random": ("model_random", "uniform_random"),
    "signal_effect_optimized": ("model_optimized", "uniform_optimized"),
    "optimizer_effect_uniform": ("uniform_optimized", "uniform_random"),
    "optimizer_effect_model": ("model_optimized", "model_random"),
}
SIGNAL_COMPARISONS = {
    "pair_int64_vs_legacy": ("pair_int64", "legacy"),
    "drop_ewma_vs_legacy": ("drop_ewma", "legacy"),
    "prior_uniform_gate_vs_legacy": ("prior_uniform_gate", "legacy"),
}


def _average(values: list[float]) -> float:
    if not values:
        raise ValueError("empty replay")
    return float(np.mean(values))


def _bootstrap_ci(deltas: list[float], seed: int, reps: int = 2048,
                  block: int = 5) -> dict:
    """Circular block bootstrap, conditional on fixed historical comparisons."""
    x = np.asarray(deltas, dtype=float)
    n = len(x)
    if n == 0 or not np.all(np.isfinite(x)):
        raise ValueError("invalid paired sample")
    rng = np.random.default_rng(seed)
    blocks = (n + block - 1) // block
    means = np.empty(reps, dtype=float)
    for i in range(reps):
        starts = rng.integers(0, n, size=blocks)
        idx = (starts[:, None] + np.arange(block)[None, :]) % n
        means[i] = float(np.mean(x[idx.ravel()[:n]]))
    return {
        "mean_delta": float(np.mean(x)),
        "low95": float(np.quantile(means, 0.025)),
        "high95": float(np.quantile(means, 0.975)),
        "rounds": int(n),
        "diagnostic_only": True,
    }


def summarize(replay: dict, windows: tuple[int, ...] = WINDOWS) -> dict:
    if (replay.get("scope") != "research_only_historical_reused_data"
            or replay.get("independent_evidence") is not False
            or replay.get("production_changed") is not False
            or replay.get("future_oos_changed") is not False
            or replay.get("promotion_authorized") is not False
            or replay.get("chronological_prior_only") is not True):
        raise ValueError("research-only safety flags are missing or invalid")
    rows = replay.get("rounds", [])
    if (len(rows) < 1 or len(rows) != replay.get("evaluated_rounds")
            or rows[0]["round_index"] != replay.get("first_round_index")
            or rows[-1]["round_index"] != replay.get("last_round_index")
            or [r["round_index"] for r in rows]
            != list(range(rows[0]["round_index"], rows[-1]["round_index"] + 1))):
        raise ValueError("incomplete or nonchronological score ledger")
    if not replay.get("data_sha256") or not replay.get("implementation_sha256"):
        raise ValueError("missing source hashes")
    # A replay may NOT report a complete full-history window without all rows.
    if replay["first_round_index"] != 101 or replay["last_round_index"] != 700:
        if 600 in windows:
            raise ValueError("600-round claims require full indices 101 through 700")
    for arm, aggregate in replay["arms"].items():
        values = [float(r["arm_metrics"][arm]["score"]) for r in rows]
        if not np.isclose(_average(values), aggregate["score"], atol=1e-10, rtol=0):
            raise ValueError(f"reported aggregate does not reconcile: {arm}")
        for row, value in zip(rows, values):
            if not np.isclose(row["scores"][arm], value, atol=1e-12, rtol=0):
                raise ValueError(f"per-round score mismatch: {arm}")
    for name, stats in replay["signal_ablation"].items():
        for metric in ("top7_hits", "log_edge", "brier_edge", "actual_mass"):
            vals = [float(r["signal_metrics"][name][metric]) for r in rows]
            if not np.isclose(_average(vals), stats[metric], atol=1e-10, rtol=0):
                raise ValueError(f"signal aggregate does not reconcile: {name}.{metric}")

    output: dict[str, Any] = {
        "type": "exploratory_historical_600_draw_prediction_replay",
        "data_sha256": replay["data_sha256"],
        "implementation_sha256": replay["implementation_sha256"],
        "first_round_index": rows[0]["round_index"],
        "last_round_index": rows[-1]["round_index"],
        "evaluated_rounds": len(rows),
        "production_changed": False,
        "future_oos_changed": False,
        "promotion_authorized": False,
        "independent_evidence": False,
        "ci_method": "2048 circular moving blocks of length 5, seed-fixed",
        "ci_limitations": (
            "Exploratory only; past draws already informed modeling, comparison "
            "selection and preprocessing. Intervals are unadjusted for model "
            "search/multiple comparisons and condition on the RNG portfolio "
            "realizations. No claim of future predictive advantage."
        ),
        "windows": {},
    }
    for w in windows:
        if w <= 0 or w > len(rows):
            raise ValueError(f"invalid window: {w}")
        subset = rows[-w:]
        summary = {
            "from_round": subset[0]["round_index"],
            "through_round": subset[-1]["round_index"],
            "arm_scores": {},
            "arm_ge3": {},
            "arm_ge4": {},
            "signal_log_edge": {},
            "signal_brier_edge": {},
            "paired_arm_score_deltas": {},
            "paired_signal_log_edge_deltas": {},
        }
        for arm in replay["arms"]:
            summary["arm_scores"][arm] = _average([
                r["arm_metrics"][arm]["score"] for r in subset])
            summary["arm_ge3"][arm] = _average([
                r["arm_metrics"][arm]["ge3"] for r in subset])
            summary["arm_ge4"][arm] = _average([
                r["arm_metrics"][arm]["ge4"] for r in subset])
        for name in replay["signal_ablation"]:
            summary["signal_log_edge"][name] = _average([
                r["signal_metrics"][name]["log_edge"] for r in subset])
            summary["signal_brier_edge"][name] = _average([
                r["signal_metrics"][name]["brier_edge"] for r in subset])
        for i, (label, (a, b)) in enumerate(ARM_COMPARISONS.items()):
            diffs = [
                r["arm_metrics"][a]["score"] - r["arm_metrics"][b]["score"]
                for r in subset
            ]
            summary["paired_arm_score_deltas"][label] = _bootstrap_ci(
                diffs, seed=20261025 + 100 * w + i)
        for i, (label, (a, b)) in enumerate(SIGNAL_COMPARISONS.items()):
            diffs = [
                r["signal_metrics"][a]["log_edge"] -
                r["signal_metrics"][b]["log_edge"] for r in subset
            ]
            summary["paired_signal_log_edge_deltas"][label] = _bootstrap_ci(
                diffs, seed=20271102 + 100 * w + i)
        output["windows"][str(w)] = summary
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--replay", type=Path,
                        default=Path("research_output/signal_portfolio_factorial.json"))
    parser.add_argument("--out", type=Path,
                        default=Path("research_output/full_history_replay_summary.json"))
    args = parser.parse_args()
    replay = json.loads(args.replay.read_text(encoding="utf-8"))
    result = summarize(replay)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "evaluated_rounds": result["evaluated_rounds"],
        "window_600_arm_scores": result["windows"]["600"]["arm_scores"],
        "independent_evidence": False,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
