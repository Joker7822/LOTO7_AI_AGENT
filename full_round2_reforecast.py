#!/usr/bin/env python3
"""Full research-only chronological reforecast: target rounds 2..latest verified draw.

All predictions are generated from strictly earlier outcomes. No issued forecast,
Production prediction, Champion or Future-OOS ledger is overwritten.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

import signal_portfolio_factorial as factor
from joint_set_v2_model import bernoulli_signal_metrics, project_inclusion
from loto7_evolving_agent import (
    N_NUMBERS, PICKS, expert_probabilities, fingerprint_file,
    make_history, read_csv_flexible,
)

VERSION = "full-round2-chronological-reforecast-v1"
VARIANTS = ("legacy", "pair_int64", "drop_ewma", "prior_uniform_gate")
PORTFOLIO_ARMS = (
    "uniform_random", "legacy_random", "uniform_optimized", "legacy_optimized",
    "pair_int64_optimized", "drop_ewma_optimized", "prior_uniform_gate_optimized",
)
UNIFORM_Q = np.full(N_NUMBERS, 1.0 / N_NUMBERS)
METRIC_KEYS = ("max_hits", "mean_hits", "ge3", "ge4", "score")
SIGNAL_KEYS = ("top7_hits", "log_edge", "brier_edge", "actual_mass")


def top7_ranking(q: np.ndarray, seed: int) -> list[int]:
    """Seeded and unbiased order for exact ties, including the uniform baseline."""
    rng = np.random.default_rng(seed)
    order = np.lexsort((rng.random(N_NUMBERS), -q))
    return [int(i + 1) for i in order[:PICKS]]


def arm_portfolios(forecasts: dict[str, np.ndarray], seed: int,
                   scenarios: int, candidates: int, random_reps: int) -> dict:
    """Freeze every ticket before caller is permitted to read the actual target."""
    result = {}
    for name in ("uniform", "legacy"):
        q = forecasts[name]
        result[name + "_random"] = [
            factor.random_tickets(q, seed + 700_000 + rep * 71)
            for rep in range(random_reps)
        ]
    for name in ("uniform",) + VARIANTS:
        result[name + "_optimized"] = factor.optimized_tickets(
            forecasts[name], seed + 1_000_000,
            scenarios=scenarios, candidates=candidates,
        )
    return result


def summarise(rows: list[dict], arm: str, key: str = "portfolio") -> dict:
    if not rows:
        raise ValueError("cannot summarise zero evaluated rounds")
    keys = METRIC_KEYS if key == "portfolio" else SIGNAL_KEYS
    return {
        name: float(np.mean([row[key][arm][name] for row in rows]))
        for name in keys
    }


def phases(rows: list[dict]) -> dict:
    windows = {
        "all_rounds_2_onward": rows,
        "cold_start_rounds_2_to_20": [r for r in rows if r["round"] <= 20],
        "adaptive_rounds_21_onward": [r for r in rows if r["round"] >= 21],
        "rounds_21_to_100": [r for r in rows if 21 <= r["round"] <= 100],
        "rounds_101_onward": [r for r in rows if r["round"] >= 101],
        "last_120_rounds": rows[-min(120, len(rows)):],
        "last_60_rounds": rows[-min(60, len(rows)):],
    }
    out = {}
    for name, window in windows.items():
        if not window:
            continue
        out[name] = {
            "n": len(window),
            "from": window[0]["round"],
            "through": window[-1]["round"],
            "portfolio": {
                arm: summarise(window, arm) for arm in PORTFOLIO_ARMS
            },
            "signal": {
                arm: summarise(window, arm, "signal") for arm in
                ("uniform",) + VARIANTS
            },
            "paired_score_delta_vs_uniform_random": {
                arm: float(np.mean([
                    r["portfolio"][arm]["score"] -
                    r["portfolio"]["uniform_random"]["score"]
                    for r in window
                ])) for arm in PORTFOLIO_ARMS if arm != "uniform_random"
            },
        }
    return out


def reforecast(history: np.ndarray, *, actual_dates: list[str] | None = None,
               start_round: int = 2, scenarios: int = 96,
               candidates: int = 32, random_reps: int = 8,
               seed: int = 20261025) -> dict:
    x = np.asarray(history)
    if (x.ndim != 2 or x.shape[1] != N_NUMBERS or len(x) < 21
            or not np.issubdtype(x.dtype, np.integer)
            or not np.all((x == 0) | (x == 1))
            or not np.all(x.sum(axis=1, dtype=np.int64) == PICKS)):
        raise ValueError("requires 21+ valid binary seven-of-37 draws")
    if start_round != 2:
        raise ValueError("this immutable experiment is defined from round 2")
    if actual_dates is not None and len(actual_dates) != len(x):
        raise ValueError("dates and draws mismatch")
    if scenarios < 8 or candidates < 5 or random_reps < 1:
        raise ValueError("invalid Monte Carlo budget")
    weights: dict[str, np.ndarray] = {}
    prior_log_edges: list[float] = []
    rows: list[dict] = []
    for t in range(1, len(x)):
        round_number = t + 1
        target_seed = int(seed + round_number * 1009)
        prior = x[:t]  # The only lottery-history input to any forecast.
        forecasts: dict[str, np.ndarray] = {"uniform": UNIFORM_Q.copy()}
        experts: dict[str, dict] = {}
        if t >= 20:
            base = expert_probabilities(prior)
            for variant in VARIANTS:
                ex = factor.variant_experts(base, variant, prior)
                if variant not in weights:
                    weights[variant] = np.zeros(len(ex), dtype=float)
                q = factor.probability_from_weights(ex, weights[variant])
                if variant == "prior_uniform_gate" and len(prior_log_edges) >= 30:
                    if float(np.mean(prior_log_edges[-30:])) <= 0.0:
                        q = UNIFORM_Q.copy()
                forecasts[variant] = q
                experts[variant] = ex
        else:
            for variant in VARIANTS:
                forecasts[variant] = UNIFORM_Q.copy()
        rankings = {
            name: top7_ranking(q, target_seed + 31)
            for name, q in forecasts.items()
        }
        portfolios = arm_portfolios(
            forecasts, target_seed, scenarios, candidates, random_reps
        )
        # Freeze-only digest is computed without access to the target outcome.
        frozen = {
            "round": round_number, "prior_draws": t,
            "signal_top7": rankings,
            "ticket_portfolios": portfolios,
        }
        sha = hashlib.sha256(
            json.dumps(frozen, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":")).encode("utf-8")
        ).hexdigest()

        # Outcome use starts HERE; all target-specific predictions are fixed.
        actual = set((np.flatnonzero(x[t]) + 1).tolist())
        actual_idx = np.flatnonzero(x[t])
        metrics = {}
        for arm in PORTFOLIO_ARMS:
            if arm.endswith("_random"):
                metrics[arm] = factor.average_metrics([
                    factor.ticket_metrics(ticket_set, actual)
                    for ticket_set in portfolios[arm]
                ])
            else:
                metrics[arm] = factor.ticket_metrics(portfolios[arm], actual)
        signals = {}
        for name, q in forecasts.items():
            p = project_inclusion(PICKS * q)
            sig = bernoulli_signal_metrics(p, actual_idx)
            signals[name] = {k: float(sig[k]) for k in SIGNAL_KEYS}
            # ranking uses seeded tie break whereas bernoulli_signal_metrics
            # uses argsort tie break; make this field match disclosed forecast.
            signals[name]["top7_hits"] = float(
                len(set(rankings[name]) & actual)
            )
        record = {
            "round": round_number,
            "date": actual_dates[t] if actual_dates else None,
            "prior_draws": t,
            "regime": "uniform_cold_start" if t < 20 else "online_adaptive",
            "forecast_sha256": sha,
            "actual_numbers": sorted(actual),
            "signal_top7": rankings,
            "tickets": {
                name: [list(ticket) for ticket in ticket_sets]
                for name, ticket_sets in portfolios.items()
                if name.endswith("_optimized")
            },
            "uniform_random_sample_tickets": [
                list(ticket) for ticket in portfolios["uniform_random"][0]
            ],
            "legacy_random_sample_tickets": [
                list(ticket) for ticket in portfolios["legacy_random"][0]
            ],
            "portfolio": metrics,
            "signal": signals,
        }
        rows.append(record)
        if t >= 20:
            prior_log_edges.append(float(signals["legacy"]["log_edge"]))
            for variant in VARIANTS:
                weights[variant] = factor.update_weights(
                    experts[variant], weights[variant], actual_idx
                )

    assert len(rows) == len(x) - 1 and rows[0]["round"] == 2
    return {
        "version": VERSION,
        "history_draws": len(x),
        "evaluated_rounds": len(rows),
        "first_target_round": 2,
        "last_target_round": len(x),
        "cold_start_rounds": min(19, len(rows)),
        "adaptive_from_round": 21,
        "baseline_config": "baseline-5fdb8dc2ad",
        "signal_variants": list(VARIANTS),
        "portfolio_arms": list(PORTFOLIO_ARMS),
        "scenarios": scenarios,
        "candidates": candidates,
        "random_reps": random_reps,
        "seed": seed,
        "target_outcome_used_before_prediction": False,
        "production_changed": False,
        "future_oos_changed": False,
        "independent_evidence": False,
        "promotion_authorized": False,
        "purpose": "exploratory_reused_historical_reforecast_only",
        "caveat": (
            "Rounds 2-20 use uniform cold start (the legacy expert requires >=20 "
            "prior draws); rounds 21+ use fixed baseline configuration with "
            "online sequential learning started at round 21. This is NOT an "
            "exact reproduction of historical issued Production forecasts "
            "or an independently precommitted future-OOS evaluation. Every "
            "portfolio is a retrospective pre-outcome reconstruction."
        ),
        "summary": phases(rows),
        "rounds": rows,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--csv", type=Path, default=Path("loto7.csv"))
    p.add_argument("--out", type=Path, default=Path(
        "research_output/full_round2_reforecast.json"
    ))
    p.add_argument("--scenarios", type=int, default=96)
    p.add_argument("--candidates", type=int, default=32)
    p.add_argument("--random-reps", type=int, default=8)
    p.add_argument("--seed", type=int, default=20261025)
    args = p.parse_args()
    x, df = make_history(read_csv_flexible(args.csv))
    observed_rounds = [
        int("".join(ch for ch in str(v) if ch.isdigit()))
        for v in df["回別"]
    ]
    if observed_rounds != list(range(1, len(x) + 1)):
        raise ValueError("nonsequential draw numbers: refusing to reinterpret round IDs")
    dates = [v.date().isoformat() for v in df["抽せん日"]]
    report = reforecast(
        x, actual_dates=dates, scenarios=args.scenarios,
        candidates=args.candidates, random_reps=args.random_reps, seed=args.seed,
    )
    report["data_sha256"] = fingerprint_file(args.csv)
    report["implementation_sha256"] = hashlib.sha256(
        Path(__file__).read_bytes()).hexdigest()
    out = args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "version": VERSION, "rounds": report["evaluated_rounds"],
        "from": 2, "through": len(x), "data_sha256": report["data_sha256"],
        "mean_score_all": {
            name: values["score"] for name, values in
            report["summary"]["all_rounds_2_onward"]["portfolio"].items()
        },
        "promotion_authorized": False,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
