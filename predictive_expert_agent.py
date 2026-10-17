#!/usr/bin/env python3
"""Research-only predictive expert agent.

Makes genuinely new forecasting hypotheses (smoothed frequency/momentum),
combines them with a prior-only online proper-score learner, and runs the
COMPLETE learner on identical-budget independent synthetic fair-draw worlds.
No existing SHA-locked v2 code, Production, or registered OOS is touched.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Dict, List, Mapping, Sequence, Tuple

import numpy as np

from joint_set_v2_model import N_NUMBERS, PICKS, UNIFORM_INCLUSION, bernoulli_signal_metrics
from loto7_evolving_agent import fingerprint_file, make_history, read_csv_flexible

VERSION = "predictive-expert-agent-v1"
EXPERTS = ("uniform", "bayes_short40", "bayes_long160", "momentum_shrink")
PRIOR = np.array([0.55, 0.15, 0.15, 0.15], dtype=float)
MIN_TRAIN = 100
EVALUATION_ROUNDS = 60
ONLINE_LOG_EDGE_RATE = 10.0
ONLINE_DECAY = 0.995
FAIR_WORLD_SEED = 74190329
NULL_WORLDS = 64
ROW_FIELDS = (
    "round_index", "scout_top7_hits", "scout_log_edge", "scout_brier_edge",
    "short_log_edge", "long_log_edge", "momentum_log_edge",
    "weight_uniform", "weight_short", "weight_long", "weight_momentum",
)
RANK_BINS = ((1, 7), (8, 14), (15, 37))


def assert_history(x: np.ndarray, min_train: int = MIN_TRAIN) -> None:
    if x.ndim != 2 or x.shape[1] != N_NUMBERS or len(x) <= min_train:
        raise ValueError("expected a 37-column draw history longer than min_train")
    if np.any((x != 0) & (x != 1)) or np.any(x.sum(axis=1) != PICKS):
        raise ValueError("each draw must have exactly seven different 1-37 numbers")


def expert_vectors(prefix_cumsum: np.ndarray, t: int) -> np.ndarray:
    """Only cumulative rows up to and including t-1 are inspected."""
    if not 0 < t < len(prefix_cumsum):
        raise ValueError("positive prior count required")
    base = np.full(N_NUMBERS, UNIFORM_INCLUSION, dtype=float)

    def rate(window: int, prior_count: int) -> np.ndarray:
        a = max(0, t - window)
        n = t - a
        counts = prefix_cumsum[t] - prefix_cumsum[a]
        return (counts + prior_count * base) / (n + prior_count)

    short = rate(window=40, prior_count=160)
    long = rate(window=160, prior_count=320)
    # Deliberately small, zero-sum momentum adjustment. It is a hypothesis,
    # not a claim that hot/cold numbers have a different actual probability.
    momentum = base + 0.60 * (short - long)
    result = np.stack((base, short, long, momentum))
    if not np.all(np.isfinite(result)) or np.max(np.abs(result.sum(axis=1) - PICKS)) > 1e-9:
        raise RuntimeError("expert inclusion probabilities invalid")
    if np.any(result < 0) or np.any(result > 1):
        raise RuntimeError("expert probability escaped [0,1]")
    return result


def weights_from_prior_scores(scores: np.ndarray) -> np.ndarray:
    """Cumulative expert edges are updated only AFTER the target is graded."""
    logits = np.log(PRIOR) + ONLINE_LOG_EDGE_RATE * scores
    logits -= logits.max()
    exp = np.exp(logits)
    w = exp / exp.sum()
    if abs(float(w.sum()) - 1) > 1e-12:
        raise RuntimeError("expert weights failed to normalize")
    return w


def mean_bootstrap_ci(values: Sequence[float], seed: int = 29938, reps: int = 4000) -> dict:
    arr = np.asarray(values, dtype=float)
    if not arr.size:
        raise ValueError("empty bootstrap input")
    rng = np.random.default_rng(seed)
    sampled = arr[rng.integers(0, arr.size, size=(reps, arr.size))].mean(axis=1)
    return {
        "mean": float(arr.mean()),
        "low95": float(np.quantile(sampled, .025)),
        "high95": float(np.quantile(sampled, .975)),
    }


def walk(
    x: np.ndarray, min_train: int = MIN_TRAIN, last_n: int = EVALUATION_ROUNDS,
    *, retain_rows: bool = True,
) -> Tuple[Dict[str, object], List[Dict[str, object]]]:
    """One full chronological experiment; cannot see t before predicting t."""
    assert_history(x, min_train)
    if last_n < 1 or len(x) - last_n < min_train:
        raise ValueError("test window overlaps initial training prefix")
    eval_start = len(x) - last_n
    cumulative = np.vstack((np.zeros((1, N_NUMBERS), dtype=np.int64),
                            np.cumsum(x.astype(np.int64), axis=0)))
    running = np.zeros(len(EXPERTS), dtype=float)
    rows: List[Dict[str, object]] = []
    scores: List[float] = []
    briers: List[float] = []
    top7s: List[float] = []
    all_weights: List[np.ndarray] = []
    bucket_data = {f"{lo}-{hi}": {
        "count": 0, "hits": 0., "predicted_sum": 0.,
    } for lo, hi in RANK_BINS}

    for t in range(min_train, len(x)):
        vectors = expert_vectors(cumulative, t)
        w = weights_from_prior_scores(running)
        predicted = w @ vectors  # every expert and hence their mix sums to 7
        assert np.all((predicted > 0) & (predicted < 1))
        actual_indices = np.flatnonzero(x[t])
        # Correct order: score with previously learned weights, THEN update.
        outcome = bernoulli_signal_metrics(predicted, actual_indices)
        component = [
            bernoulli_signal_metrics(vectors[k], actual_indices) for k in range(len(EXPERTS))
        ]
        running = ONLINE_DECAY * running + np.asarray(
            [m["log_edge"] for m in component], dtype=float
        )
        if t < eval_start:
            continue
        scores.append(float(outcome["log_edge"]))
        briers.append(float(outcome["brier_edge"]))
        top7s.append(float(outcome["top7_hits"]))
        all_weights.append(w)
        if retain_rows:
            rows.append({
                "round_index": t + 1,
                "scout_top7_hits": outcome["top7_hits"],
                "scout_log_edge": outcome["log_edge"],
                "scout_brier_edge": outcome["brier_edge"],
                "short_log_edge": component[1]["log_edge"],
                "long_log_edge": component[2]["log_edge"],
                "momentum_log_edge": component[3]["log_edge"],
                "weight_uniform": w[0], "weight_short": w[1],
                "weight_long": w[2], "weight_momentum": w[3],
            })
        rank = np.argsort(-predicted, kind="stable")
        y = x[t]
        for lo, hi in RANK_BINS:
            part = rank[lo - 1:hi]
            bucket = bucket_data[f"{lo}-{hi}"]
            bucket["count"] += len(part)
            bucket["hits"] += int(y[part].sum())
            bucket["predicted_sum"] += float(predicted[part].sum())

    assert len(scores) == last_n
    arr = np.asarray(all_weights)
    return {
        "mean_log_edge_vs_uniform": float(np.mean(scores)),
        "mean_brier_edge_vs_uniform": float(np.mean(briers)),
        "mean_top7_hits": float(np.mean(top7s)),
        "mean_weights": {name: float(v) for name, v in zip(EXPERTS, arr.mean(axis=0))},
        "last_prior_only_weights": {name: float(v) for name, v in zip(EXPERTS, arr[-1])},
        "rank_bucket_calibration": [
            {
                "rank_bucket": key,
                "realized_frequency": float(bucket["hits"] / bucket["count"]),
                "predicted_probability": float(bucket["predicted_sum"] / bucket["count"]),
                "observations": int(bucket["count"]),
            }
            for key, bucket in bucket_data.items()
        ],
        "log_edge_paired_bootstrap_95": mean_bootstrap_ci(scores),
    }, rows


def synthetic_fair_history(n: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    x = np.zeros((n, N_NUMBERS), dtype=np.int8)
    for i in range(n):
        x[i, rng.choice(N_NUMBERS, size=PICKS, replace=False)] = 1
    return x


def full_budget_synthetic_null(
    n: int, min_train: int, last_n: int, worlds: int = NULL_WORLDS,
    seed: int = FAIR_WORLD_SEED,
) -> dict:
    if not 1 <= worlds <= 4096:
        raise ValueError("world budget must be 1..4096")
    values, top = [], []
    for world in range(worlds):
        synthetic = synthetic_fair_history(n, seed + 7919 * world)
        result, _ = walk(synthetic, min_train, last_n, retain_rows=False)
        values.append(result["mean_log_edge_vs_uniform"])
        top.append(result["mean_top7_hits"])
    return {
        "worlds": worlds,
        "matching_algorithm_and_history_length": True,
        "mean_log_edge": float(np.mean(values)),
        "log_edge_null_p95": float(np.quantile(values, 0.95)),
        "top7_null_mean": float(np.mean(top)),
        "null_log_edges": values,
        "null_top7_hits": top,
        "simulation_seed": seed,
        "synthetic_worlds_not_prospective_evidence": True,
    }


def upper_tail_p(observed: float, null_values: Sequence[float]) -> float:
    arr = np.asarray(null_values, dtype=float)
    if not len(arr):
        raise ValueError("no synthetic null")
    return (1 + int(np.sum(arr >= observed - 1e-15))) / (len(arr) + 1)


def run(
    csv_path: Path, out_dir: Path,
    min_train: int = MIN_TRAIN, last_n: int = EVALUATION_ROUNDS,
    worlds: int = NULL_WORLDS,
    v2_saved_summary: Path = Path("loto7_agent_output/joint_set_v2_true_nested_summary.json"),
) -> dict:
    x, clean = make_history(read_csv_flexible(csv_path))
    fingerprint = fingerprint_file(csv_path)
    # No cherry-picked outcome ranges: use exactly the most recent predeclared
    # consecutive last_n actual draws and all preceding observed rounds for online learning.
    result, rows = walk(x, min_train, last_n)
    expected_indices = list(range(len(x) - last_n + 1, len(x) + 1))
    if [int(row["round_index"]) for row in rows] != expected_indices:
        raise RuntimeError("noncontiguous prequential outcome range")
    if "回別" in clean:
        observed = [int("".join(c for c in str(v) if c.isdigit())) for v in clean["回別"].iloc[-last_n:]]
        if observed != expected_indices:
            raise RuntimeError("CSV round-index identity mismatch")
    synthetic = full_budget_synthetic_null(len(x), min_train, last_n, worlds)
    log_p = upper_tail_p(result["mean_log_edge_vs_uniform"], synthetic["null_log_edges"])
    top_p = upper_tail_p(result["mean_top7_hits"], synthetic["null_top7_hits"])
    reference: Dict[str, object] = {"available": False}
    if v2_saved_summary.exists():
        original = json.loads(v2_saved_summary.read_text(encoding="utf-8"))
        if (original.get("data_sha256") != fingerprint
                or int(original.get("evaluated_rounds", -1)) != last_n
                or original.get("evaluation_type") != "strict_prior_only_prequential_inclusion_probability_joint_set_v2"):
            raise ValueError("existing v2 strict-nested comparator is stale or mismatched")
        reference = {
            "available": True, "same_historical_rounds": True,
            "mean_log_edge": float(original["signal"]["mean_log_edge_vs_uniform"]),
            "mean_top7_hits": float(original["signal"]["mean_top7_hits"]),
            "mean_brier_edge": float(original["signal"]["mean_brier_edge_vs_uniform"]),
        }
    summary = {
        "version": VERSION, "scope": "research_only",
        "independent_evidence": False, "promotion_eligible": False,
        "prospective_shadow_updated": False, "production_changed": False,
        "model_family_predeclared": list(EXPERTS),
        "expert_prior_weights": PRIOR.tolist(),
        "online_log_edge_rate": ONLINE_LOG_EDGE_RATE,
        "online_decay": ONLINE_DECAY,
        "min_train": min_train, "evaluated_rounds": last_n,
        "evaluated_round_start": expected_indices[0],
        "evaluated_round_end": expected_indices[-1],
        "data_sha256": fingerprint,
        "scout": result,
        "v2_reference": reference,
        "full_budget_fair_draw_null": {
            k: v for k, v in synthetic.items() if k not in ("null_log_edges", "null_top7_hits")
        },
        "synthetic_null_p_log_edge": log_p,
        "synthetic_null_p_top7": top_p,
        "agent_roles": {
            "hypothesis_engineer": "Construct fixed uniform, shrinkage-frequency and momentum experts.",
            "online_calibration_specialist": "Update weights using strictly previous outcomes and proper log score.",
            "skeptical_evaluator": "Compare against fixed uniform, saved v2 and synthetic full-budget fair draws.",
            "promotion_firewall": "Historical/reused evidence cannot promote, freeze, or overwrite Production.",
        },
        "handoff": {
            "research_finding": (
                "exploratory_signal_only" if result["mean_log_edge_vs_uniform"] > 0
                else "no_historical_proper_score_improvement"
            ),
            "next_allowed_step": "Pre-register a disjoint prospective test before future target results; do not tune the registered v2 shadow.",
            "automatic_model_adoption": False,
        },
        "interpretation": (
            "All real draws in this diagnosis have already been investigated elsewhere, so "
            "neither favorable historical values nor a synthetic-null p value are independent proof. "
            "Even a lower synthetic p cannot authorize Production promotion. "
            "The synthetic null repeats the entire same forecast/online-learning budget "
            "under truly uniform 7-of-37 draws; it is not a fresh real-world holdout."
        ),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "predictive_expert_agent_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    with (out_dir / "predictive_expert_agent_rounds.csv").open(
        "w", newline="", encoding="utf-8-sig"
    ) as f:
        writer = csv.DictWriter(f, fieldnames=ROW_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    s = result
    report = [
        "# Predictive Expert Agent — Strict Prior-only Research",
        "",
        "- model authority: **Research-only, no Champion or registered shadow change**",
        "- independent prospective OOS: **NO** (previously used historical draws)",
        "- forecast role: **smoothed expert hypotheses + online log-score aggregation**",
        "- statistical skeptic: **complete matched-budget fair-draw synthetic null**",
        f"- evaluated historical targets: **{expected_indices[0]}–{expected_indices[-1]}**",
        f"- forecast mean Top7 hits: **{s['mean_top7_hits']:.4f}** (uniform expectation 1.3243)",
        f"- all-number mean Bernoulli log edge vs uniform: **{s['mean_log_edge_vs_uniform']:+.8f}**",
        f"- mean Brier improvement vs uniform: **{s['mean_brier_edge_vs_uniform']:+.8f}**",
        f"- synthetic fair-world null (n={worlds}), upper-tail p for primary log edge: **{log_p:.4f}**",
        f"- synthetic fair-world Top7 exploratory p: **{top_p:.4f}**",
        f"- prior-only mean online weights: **{s['mean_weights']}**",
        "",
        "## Historical v2 signal reference (not an independent holdout)",
        f"- valid same-round comparator: **{reference['available']}**",
        f"- v2 log edge: **{reference.get('mean_log_edge', None)}**",
        f"- v2 Top7 mean: **{reference.get('mean_top7_hits', None)}**",
        "",
        "## Promotion firewall",
        "These already-used draws **cannot select or promote** this agent. "
        "An unmodified, separately registered future OOS is required before any adoption.",
        "No portfolio accuracy improvement or lottery winning probability is claimed.",
        "",
    ]
    (out_dir / "predictive_expert_agent_report.md").write_text("\n".join(report), encoding="utf-8")
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description="Prior-only multi-expert lottery signal research")
    ap.add_argument("--csv", type=Path, default=Path("loto7.csv"))
    ap.add_argument("--out-dir", type=Path, default=Path("loto7_agent_output"))
    ap.add_argument("--min-train", type=int, default=MIN_TRAIN)
    ap.add_argument("--last-n", type=int, default=EVALUATION_ROUNDS)
    ap.add_argument("--null-worlds", type=int, default=NULL_WORLDS)
    ap.add_argument("--v2-summary", type=Path, default=Path("loto7_agent_output/joint_set_v2_true_nested_summary.json"))
    args = ap.parse_args()
    result = run(args.csv, args.out_dir, args.min_train, args.last_n, args.null_worlds, args.v2_summary)
    print(json.dumps({
        "signal_log_edge": result["scout"]["mean_log_edge_vs_uniform"],
        "null_upper_p": result["synthetic_null_p_log_edge"],
        "promotion_eligible": result["promotion_eligible"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
