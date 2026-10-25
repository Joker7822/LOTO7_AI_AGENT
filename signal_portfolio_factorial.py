#!/usr/bin/env python3
"""Read-only, chronological signal x portfolio factorial and expert ablations.

This research diagnostic must never publish tickets, rewrite old forecasts,
promote a Champion, or enter an existing prospective OOS registry.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

import loto7_v2_runner as v2
from joint_set_v2_model import bernoulli_signal_metrics, project_inclusion
from loto7_evolving_agent import (
    N_NUMBERS, PICKS, expert_probabilities, fingerprint_file, make_history,
    read_csv_flexible,
)
from pair_context_v2 import probability as corrected_pair_probability

VERSION = "signal-portfolio-factorial-ablation-v1"
VARIANTS = (
    "legacy", "prior_uniform_gate", "pair_int64", "drop_pair", "drop_hot", "drop_ewma",
    "drop_overdue", "drop_momentum", "drop_recent_cold",
)
ARMS = ("uniform_random", "model_random", "uniform_optimized", "model_optimized")
UNIFORM_Q = np.full(N_NUMBERS, 1.0 / N_NUMBERS)


def variant_experts(base: dict, variant: str, history: np.ndarray) -> dict:
    if variant not in VARIANTS:
        raise ValueError("unknown ablation: " + variant)
    ex = dict(base)
    if variant == "pair_int64":
        ex["pair_context"] = corrected_pair_probability(history)
    elif variant.startswith("drop_"):
        group = variant[5:]
        if group == "pair":
            excluded = {"pair_context"}
        elif group in ("hot", "ewma"):
            excluded = {k for k in ex if k.startswith(group + "_")}
        else:
            excluded = {group}
        ex = {k: value for k, value in ex.items() if k not in excluded}
    if not ex:
        raise ValueError("ablation removed every expert")
    return ex


def probability_from_weights(experts: dict, logw: np.ndarray) -> np.ndarray:
    cfg = v2.DEFAULT_CHAMPION
    keys = tuple(experts)
    if logw.shape != (len(keys),):
        raise ValueError("expert weight count differs from configured experts")
    weights = v2._weights_from_log(logw, cfg.expert_uniform_mix)
    q = sum((float(weights[i]) * experts[k] for i, k in enumerate(keys)),
            np.zeros(N_NUMBERS, dtype=float))
    q /= q.sum()
    q = (1.0 - cfg.final_uniform_mix) * q + cfg.final_uniform_mix * UNIFORM_Q
    q /= q.sum()
    if not np.all(np.isfinite(q)) or not np.all(q > 0):
        raise ArithmeticError("invalid signal probability")
    return q


def update_weights(experts: dict, logw: np.ndarray, actual: np.ndarray) -> np.ndarray:
    cfg = v2.DEFAULT_CHAMPION
    rewards = np.array([float(p[actual].sum()) for p in experts.values()])
    return np.clip(cfg.decay * logw + cfg.eta * (rewards - PICKS / N_NUMBERS),
                   -20.0, 20.0)


def sampled_sets(q: np.ndarray, size: int, seed: int) -> np.ndarray:
    """Exponential race: weighted 7-of-37 sampling WITHOUT replacement."""
    if size < 1 or q.shape != (N_NUMBERS,) or not np.isfinite(q).all() or np.any(q <= 0):
        raise ValueError("invalid sampling request")
    rng = np.random.default_rng(seed)
    races = rng.exponential(size=(size, N_NUMBERS)) / q[None, :]
    indices = np.argpartition(races, PICKS - 1, axis=1)[:, :PICKS]
    return np.sort(indices + 1, axis=1).astype(np.int16)


def random_tickets(q: np.ndarray, seed: int) -> list[tuple[int, ...]]:
    """Five distinct tickets; never consult the target outcome."""
    seen = set()
    for row in sampled_sets(q, 128, seed):
        seen.add(tuple(map(int, row)))
        if len(seen) == 5:
            break
    if len(seen) != 5:
        raise RuntimeError("not enough unique ticket samples")
    # Preserve deterministic sampling order without relying on set iteration.
    picks = []
    for row in sampled_sets(q, 128, seed):
        ticket = tuple(map(int, row))
        if ticket not in picks:
            picks.append(ticket)
        if len(picks) == 5:
            return picks
    raise RuntimeError("not enough unique ticket samples")


def binary_sets(sets: np.ndarray) -> np.ndarray:
    result = np.zeros((len(sets), N_NUMBERS), dtype=np.int16)
    result[np.arange(len(sets))[:, None], sets - 1] = 1
    return result


def utility(hits: np.ndarray) -> np.ndarray:
    return hits + 0.35 * (hits >= 3) + 0.75 * (hits >= 4)


def optimized_tickets(q: np.ndarray, seed: int, scenarios: int,
                      candidates: int) -> list[tuple[int, ...]]:
    """Greedy expected max-hit utility, using model-generated scenarios only."""
    if scenarios < 8 or candidates < 5:
        raise ValueError("too few scenarios or candidates")
    scenario_sets = sampled_sets(q, scenarios, seed + 11)
    candidate_draws = sampled_sets(q, max(candidates * 6, 128), seed + 29)
    # np.unique(..., axis=0) sorts lexicographically and would prefer low
    # numbered tickets when truncated. Preserve draw order during deduplication.
    unique_rows, seen = [], set()
    for row in candidate_draws:
        ticket = tuple(map(int, row))
        if ticket not in seen:
            seen.add(ticket)
            unique_rows.append(ticket)
        if len(unique_rows) == candidates:
            break
    candidate_sets = np.asarray(unique_rows, dtype=np.int16)
    if len(candidate_sets) < 5:
        raise RuntimeError("too few unique candidate tickets")
    hits = binary_sets(scenario_sets) @ binary_sets(candidate_sets).T
    current = np.zeros(scenarios, dtype=np.int16)
    used = np.zeros(len(candidate_sets), dtype=bool)
    selected = []
    for _ in range(5):
        # The objective is the same 5-ticket composite score used by the
        # historical replay: max_hits + .35 ge3 + .75 ge4 + .10 mean_hits.
        score = np.mean(utility(np.maximum(current[:, None], hits)), axis=0)
        score += (0.10 / 5.0) * np.mean(hits, axis=0)
        score[used] = -np.inf
        index = int(np.argmax(score))
        used[index] = True
        selected.append(tuple(map(int, candidate_sets[index])))
        current = np.maximum(current, hits[:, index])
    return selected


def ticket_metrics(tickets: list[tuple[int, ...]], actual: set[int]) -> dict:
    if len(tickets) != 5 or len(set(tickets)) != 5:
        raise ValueError("portfolio must contain five distinct tickets")
    hits = [len(set(t) & actual) for t in tickets]
    metrics = {
        "max_hits": float(max(hits)),
        "mean_hits": float(np.mean(hits)),
        "ge3": float(any(h >= 3 for h in hits)),
        "ge4": float(any(h >= 4 for h in hits)),
    }
    metrics["score"] = float(
        metrics["max_hits"] + 0.35 * metrics["ge3"] +
        0.75 * metrics["ge4"] + 0.10 * metrics["mean_hits"]
    )
    return metrics


def average_metrics(rows: list[dict]) -> dict:
    if not rows:
        raise ValueError("empty metric list")
    return {k: float(np.mean([r[k] for r in rows])) for k in rows[0]}


def evaluate(history: np.ndarray, *, min_train: int = 100, last_n: int = 60,
             scenarios: int = 128, candidates: int = 48, random_reps: int = 16,
             seed: int = 20261025) -> dict:
    x = np.asarray(history)
    if (x.ndim != 2 or x.shape[1] != N_NUMBERS
            or not np.issubdtype(x.dtype, np.integer)
            or not np.all((x == 0) | (x == 1))
            or not np.all(x.sum(axis=1, dtype=np.int64) == PICKS)):
        raise ValueError("requires binary 37-number draw matrix with seven per draw")
    if min_train < 20 or last_n < 1 or len(x) < min_train + last_n:
        raise ValueError("not enough chronological history")
    if scenarios < 8 or candidates < 5 or random_reps < 1:
        raise ValueError("invalid fixed Monte Carlo budget")

    weights = {}
    arms = {name: [] for name in ARMS}
    signal = {name: [] for name in VARIANTS}
    round_rows = []
    gate_prior_scores = []  # Only observed outcomes strictly BEFORE the target.
    evaluation_start = len(x) - last_n
    for t in range(min_train, len(x)):
        prior = x[:t]
        # The target draw x[t] is not read until AFTER every forecast/portfolio
        # for this target has been generated from prior history.
        base = expert_probabilities(prior)
        forecasts = {}
        expert_sets = {}
        for name in VARIANTS:
            ex = variant_experts(base, name, prior)
            if name not in weights:
                weights[name] = np.zeros(len(ex), dtype=float)
            q = probability_from_weights(ex, weights[name])
            if name == "prior_uniform_gate" and len(gate_prior_scores) >= 30:
                if float(np.mean(gate_prior_scores[-30:])) <= 0.0:
                    q = UNIFORM_Q.copy()
            forecasts[name] = q
            expert_sets[name] = ex

        if t >= evaluation_start:
            q = forecasts["legacy"]
            target_seed = int(seed + t * 1009)
            pre_outcome = {}
            for label, p in (("uniform", UNIFORM_Q), ("model", q)):
                random_portfolios = [
                    random_tickets(p, target_seed + 10000 + rep)
                    for rep in range(random_reps)
                ]
                pre_outcome[label + "_random"] = random_portfolios
                pre_outcome[label + "_optimized"] = optimized_tickets(
                    p, target_seed + 500000, scenarios, candidates
                )
            forecast_hash = hashlib.sha256(q.astype("<f8").tobytes()).hexdigest()
            portfolio_hash = hashlib.sha256(
                repr(pre_outcome).encode("utf-8")).hexdigest()
            # Outcome is accessed ONLY after all candidates are fixed above.
            actual = set((np.flatnonzero(x[t]) + 1).tolist())
            for label in ARMS:
                portfolios = pre_outcome[label]
                if label.endswith("_random"):
                    result = average_metrics(
                        [ticket_metrics(p, actual) for p in portfolios])
                else:
                    result = ticket_metrics(portfolios, actual)
                arms[label].append(result)
            actual_idx = np.flatnonzero(x[t])
            for name in VARIANTS:
                inclusion = project_inclusion(PICKS * forecasts[name])
                signal[name].append(bernoulli_signal_metrics(inclusion, actual_idx))
            round_rows.append({
                "round_index": t + 1,
                "forecast_sha256": forecast_hash,
                "portfolio_sha256": portfolio_hash,
                "scores": {name: arms[name][-1]["score"] for name in ARMS},
            })

        actual_idx = np.flatnonzero(x[t])
        legacy_inclusion = project_inclusion(PICKS * forecasts["legacy"])
        legacy_edge = bernoulli_signal_metrics(legacy_inclusion, actual_idx)["log_edge"]
        gate_prior_scores.append(float(legacy_edge))
        for name in VARIANTS:
            weights[name] = update_weights(expert_sets[name], weights[name], actual_idx)

    arm_summary = {name: average_metrics(rows) for name, rows in arms.items()}
    signal_summary = {}
    for name, rows in signal.items():
        signal_summary[name] = {
            k: float(np.mean([r[k] for r in rows]))
            for k in ("top7_hits", "log_edge", "brier_edge", "actual_mass")
        }
    for name in VARIANTS:
        signal_summary[name]["delta_log_edge_vs_legacy"] = (
            signal_summary[name]["log_edge"] - signal_summary["legacy"]["log_edge"]
        )
        signal_summary[name]["delta_brier_edge_vs_legacy"] = (
            signal_summary[name]["brier_edge"] - signal_summary["legacy"]["brier_edge"]
        )
    return {
        "version": VERSION,
        "scope": "research_only_historical_reused_data",
        "independent_evidence": False,
        "production_changed": False,
        "future_oos_changed": False,
        "promotion_authorized": False,
        "chronological_prior_only": True,
        "min_train": min_train,
        "evaluated_rounds": last_n,
        "first_round_index": evaluation_start + 1,
        "last_round_index": len(x),
        "random_reps_per_target": random_reps,
        "scenarios_per_optimized_arm": scenarios,
        "candidates_per_optimized_arm": candidates,
        "seed": seed,
        "arms": arm_summary,
        "signal_ablation": signal_summary,
        "rounds": round_rows,
        "interpretation": (
            "Exploratory paired factorial and expert ablations. Data reused for "
            "development; neither rank nor historical improvement establishes "
            "future predictive advantage. A separately preregistered future "
            "comparison is mandatory before any model change."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path, default=Path("loto7.csv"))
    parser.add_argument("--out", type=Path,
                        default=Path("research_output/signal_portfolio_factorial.json"))
    parser.add_argument("--min-train", type=int, default=100)
    parser.add_argument("--last-n", type=int, default=60)
    parser.add_argument("--scenarios", type=int, default=128)
    parser.add_argument("--candidates", type=int, default=48)
    parser.add_argument("--random-reps", type=int, default=16)
    parser.add_argument("--seed", type=int, default=20261025)
    args = parser.parse_args()
    history, _ = make_history(read_csv_flexible(args.csv))
    result = evaluate(
        history, min_train=args.min_train, last_n=args.last_n,
        scenarios=args.scenarios, candidates=args.candidates,
        random_reps=args.random_reps, seed=args.seed,
    )
    result["data_sha256"] = fingerprint_file(args.csv)
    result["implementation_sha256"] = hashlib.sha256(
        Path(__file__).read_bytes()).hexdigest()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "scope": result["scope"],
        "evaluated_rounds": result["evaluated_rounds"],
        "score_by_arm": {name: value["score"] for name, value in result["arms"].items()},
        "promotion_authorized": False,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
