#!/usr/bin/env python3
"""Read-only chronological Top1-overlap34 vs equally shaped random-anchor control.

This is retrospective evidence from *reused* model-development history, not a
prospective OOS sample. Existing SHA-locked future evaluation is untouched.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

import balanced_uniform_portfolio as geometry35
import signal_portfolio_factorial as signal
from loto7_evolving_agent import (
    N_NUMBERS, PICKS, expert_probabilities, fingerprint_file,
    make_history, read_csv_flexible,
)
import top1_overlap34 as geometry34

VERSION = "top1-overlap34-chronological-diagnostic-v1"
SEED = 20261025
ARMS = ("legacy_top1_overlap34", "uniform_anchor_overlap34", "uniform_disjoint35")
METRIC_KEYS = ("score", "max_hits", "mean_hits", "ge3", "ge4")


def top1_from_q(q: np.ndarray, seed: int) -> int:
    q = np.asarray(q, dtype=float)
    if (q.shape != (N_NUMBERS,) or not np.isfinite(q).all()
            or np.any(q < 0) or not np.isclose(q.sum(), 1.0, atol=1e-10)):
        raise ValueError("invalid 37-number probability vector")
    # Uniform numbers and exact score ties get a reproducible unbiased rank.
    rng = np.random.default_rng(seed)
    return int(np.lexsort((rng.random(N_NUMBERS), -q))[0] + 1)


def create_forecasts(legacy_top1: int, uniform_top1: int,
                     draw_seed: int) -> dict[str, list[tuple[int, ...]]]:
    return {
        "legacy_top1_overlap34":
            geometry34.make_portfolio(legacy_top1, draw_seed + 1_000_000),
        "uniform_anchor_overlap34":
            geometry34.make_portfolio(uniform_top1, draw_seed + 1_000_000),
        "uniform_disjoint35":
            geometry35.disjoint_portfolio(draw_seed + 1_000_000),
    }


def paired_ci(rows: list[dict], candidate: str, control: str,
              *, seed: int, reps: int = 2000) -> dict[str, float]:
    diffs = np.asarray([r["scores"][candidate]["score"] -
                        r["scores"][control]["score"] for r in rows], dtype=float)
    if not len(diffs):
        raise ValueError("empty evaluation")
    rng = np.random.default_rng(seed)
    # Explicitly descriptive interval on research-reused data, not valid
    # prospective proof, selection-adjusted inference, or a promotion gate.
    resampled = rng.choice(diffs, size=(reps, len(diffs)), replace=True).mean(axis=1)
    return {
        "paired_mean_delta": float(diffs.mean()),
        "paired_bootstrap_95pct_low": float(np.percentile(resampled, 2.5)),
        "paired_bootstrap_95pct_high": float(np.percentile(resampled, 97.5)),
        "bootstrap_reps": reps,
    }


def summarize(rows: list[dict], seed: int) -> dict:
    if not rows:
        raise ValueError("no graded rounds")
    return {
        "count": len(rows),
        "first_round": rows[0]["round"],
        "last_round": rows[-1]["round"],
        "arms": {
            arm: {k: float(np.mean([r["scores"][arm][k] for r in rows]))
                  for k in METRIC_KEYS}
            for arm in ARMS
        },
        "paired_top1_vs_uniform_anchor": paired_ci(
            rows, ARMS[0], ARMS[1], seed=seed + 717
        ),
        "paired_top1_vs_disjoint": paired_ci(
            rows, ARMS[0], ARMS[2], seed=seed + 727
        ),
        "paired_uniform_anchor_vs_disjoint": paired_ci(
            rows, ARMS[1], ARMS[2], seed=seed + 737
        ),
        "top1_hit_rate": float(np.mean([
            r["legacy_top1"] in r["actual_numbers"] for r in rows
        ])),
        "fair_uniform_top1_hit_rate": PICKS / N_NUMBERS,
    }


def evaluate(history: np.ndarray, *, dates: list[str] | None = None,
             seed: int = SEED) -> dict:
    x = np.asarray(history)
    if (x.ndim != 2 or x.shape[1] != N_NUMBERS or len(x) < 21
            or not np.issubdtype(x.dtype, np.integer)
            or not np.all((x == 0) | (x == 1))
            or not np.all(x.sum(axis=1, dtype=np.int64) == PICKS)):
        raise ValueError("need >=21 valid chronological 7-of-37 draws")
    if dates is not None and len(dates) != len(x):
        raise ValueError("date count does not match draw count")
    weight = None
    rows = []
    for t in range(1, len(x)):
        round_number = t + 1
        draw_seed = seed + round_number * 1009
        prior = x[:t]
        ex = None
        if t >= 20:
            ex = expert_probabilities(prior)
            if weight is None:
                weight = np.zeros(len(ex), dtype=float)
            q = signal.probability_from_weights(ex, weight)
            regime = "prior_only_legacy_signal"
        else:
            q = np.ones(N_NUMBERS, dtype=float) / N_NUMBERS
            regime = "uniform_cold_start_no_legacy_experts"
        model_top1 = top1_from_q(q, draw_seed + 31)
        random_top1 = top1_from_q(
            np.full(N_NUMBERS, 1.0 / N_NUMBERS), draw_seed + 31
        )
        predictions = create_forecasts(model_top1, random_top1, draw_seed)
        frozen_payload = {
            "target_round": round_number,
            "prior_draws": t,
            "legacy_top1": model_top1,
            "uniform_anchor": random_top1,
            "tickets": {k: [list(v) for v in predictions[k]] for k in ARMS},
        }
        forecast_sha = hashlib.sha256(json.dumps(
            frozen_payload, sort_keys=True, separators=(",", ":")
        ).encode()).hexdigest()
        # Only below this line may the target outcome be used.
        actual = set((np.flatnonzero(x[t]) + 1).tolist())
        scores = {key: signal.ticket_metrics(tickets, actual)
                  for key, tickets in predictions.items()}
        rows.append({
            "round": round_number,
            "date": dates[t] if dates else None,
            "prior_draws": t,
            "regime": regime,
            "legacy_top1": model_top1,
            "uniform_anchor": random_top1,
            "pre_outcome_forecast_sha256": forecast_sha,
            "tickets": frozen_payload["tickets"],
            "actual_numbers": sorted(actual),
            "scores": scores,
        })
        if t >= 20:
            weight = signal.update_weights(ex, weight, np.flatnonzero(x[t]))
    windows = {
        "all_2_to_latest": rows,
        "cold_start_2_to_20": [r for r in rows if r["round"] <= 20],
        "online_21_to_latest": [r for r in rows if r["round"] >= 21],
        "rounds_101_to_latest": [r for r in rows if r["round"] >= 101],
        "last_120": rows[-120:],
        "last_60": rows[-60:],
    }
    return {
        "version": VERSION,
        "first_target_round": 2,
        "last_target_round": len(x),
        "evaluated_rounds": len(rows),
        "baseline_config": "baseline-5fdb8dc2ad",
        "seed": seed,
        "scenario": "Top1 from past-only legacy model, shared in tickets 1 and 2",
        "arms": list(ARMS),
        "fair_world_exact": geometry34.theory_report(),
        "periods": {
            name: summarize(window, seed + 4999 * idx)
            for idx, (name, window) in enumerate(windows.items()) if window
        },
        "rows": rows,
        "scope": "research_only_reused_historical_draws",
        "target_outcome_used_before_prediction": False,
        "independent_evidence": False,
        "pre_registered_prospective_evidence": False,
        "promotion_authorized": False,
        "existing_future_oos_changed": False,
        "production_changed": False,
        "interpretation": (
            "The uniform-anchor control holds 34-number geometry constant. "
            "Any difference from it is retrospective evidence only. For a "
            "fair draw neither the legacy Top1 nor the random anchor has an "
            "advantage. Every five-distinct-ticket portfolio has equal first-"
            "prize probability; no improvement in profit is established."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path, default=Path("loto7.csv"))
    parser.add_argument("--out", type=Path,
                        default=Path("research_output/top1_overlap34_research.json"))
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    x, clean = make_history(read_csv_flexible(args.csv))
    if "回別" not in clean.columns:
        raise ValueError("missing actual round IDs")
    numbers = [int("".join(c for c in str(raw) if c.isdigit()))
               for raw in clean["回別"]]
    if numbers != list(range(1, len(x) + 1)):
        raise ValueError("draw sequence must be exactly 1..N")
    dates = [v.date().isoformat() for v in clean["抽せん日"]]
    report = evaluate(x, dates=dates, seed=args.seed)
    report["input_csv_sha256"] = fingerprint_file(args.csv)
    report["script_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "targets": report["evaluated_rounds"],
        "first": report["first_target_round"],
        "last": report["last_target_round"],
        "score_by_arm": {
            k: v["score"] for k, v in report["periods"]["all_2_to_latest"]["arms"].items()
        },
        "research_only": True, "promotion_authorized": False,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
