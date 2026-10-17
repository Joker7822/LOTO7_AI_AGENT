#!/usr/bin/env python3
"""Research-only v2 rank/calibration/gate and five-ticket conversion audit.

Every historical forecast is rebuilt from a strict previous-draw prefix and the
already recorded prior-only v2 config. The historical 60 draws have been reused
in earlier research: this is diagnostic, not a newly untouched holdout.
This module DOES NOT alter registered prospective shadow, model, or Production.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Mapping, Sequence, Tuple

import numpy as np

from joint_set_v2_model import (
    ForecastBundle, N_NUMBERS, PICKS, UNIFORM_INCLUSION,
    _sets_to_binary, bernoulli_signal_metrics, candidate_configs,
    expected_utility_portfolio, forecast, portfolio_metrics, sample_joint_sets,
)
from joint_set_v2_research import build_prequential_signal
from loto7_evolving_agent import make_history, read_csv_flexible

REPORT_VERSION = "joint-set-v2-conversion-audit-v1"
RANK_BUCKETS = ((1, 7), (8, 14), (15, 21), (22, 28), (29, 37))
ROW_FIELDS = (
    "round_index", "selected_config", "gate", "top7_raw", "top7_gated",
    "log_edge_raw", "log_edge_gated", "brier_edge_raw", "brier_edge_gated",
    "baseline_score", "aligned_score", "paired_delta",
    "baseline_train_mc", "baseline_independent_mc",
    "aligned_train_mc", "aligned_independent_mc",
    "baseline_mc_optimism", "aligned_mc_optimism",
)


def load_historical_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError("existing v2 nested backtest has no rows")
    ints = [int(row["round_index"]) for row in rows]
    if len(ints) != len(set(ints)) or ints != list(range(ints[0], ints[0] + len(ints))):
        raise ValueError("existing v2 nested backtest must have contiguous, unique rounds")
    return rows


def scenario_score(hits: np.ndarray) -> np.ndarray:
    """Exactly the same formula as real-outcome portfolio_metrics(score)."""
    arr = np.asarray(hits, dtype=np.float64)
    if arr.ndim != 2 or arr.shape[1] < 1:
        raise ValueError("scenarios x tickets hit matrix required")
    best = arr.max(axis=1)
    return best + 0.35 * (best >= 3) + 0.75 * (best >= 4) + 0.10 * arr.mean(axis=1)


def mean_candidate_scores(hits: np.ndarray, selected: Sequence[int]) -> np.ndarray:
    """Score each remaining ticket conditional on the selected ticket subset."""
    mat = np.asarray(hits, dtype=np.float64)
    if selected:
        kept = mat[:, list(selected)]
        mx = kept.max(axis=1)
        total = kept.sum(axis=1)
    else:
        mx = np.zeros(mat.shape[0], dtype=float)
        total = np.zeros(mat.shape[0], dtype=float)
    best = np.maximum(mx[:, None], mat)
    avg = (total[:, None] + mat) / (len(selected) + 1)
    scores = best + 0.35 * (best >= 3) + 0.75 * (best >= 4) + 0.10 * avg
    return scores.mean(axis=0)


def aligned_objective_portfolio(
    bundle: ForecastBundle, seed: int, scenarios: int = 256,
    candidate_count: int = 64, local_passes: int = 2, n_tickets: int = 5,
) -> Tuple[List[Tuple[int, ...]], Dict[str, float]]:
    """Uses the identical candidate distribution/seed as the baseline optimizer."""
    scenario_sets = sample_joint_sets(bundle, scenarios, seed=seed + 11)
    candidate_draws = sample_joint_sets(bundle, max(candidate_count * 8, 512), seed=seed + 29)
    unique, counts = np.unique(candidate_draws, axis=0, return_counts=True)
    candidate_sets = unique[np.argsort(counts)[::-1][:candidate_count]]
    if len(candidate_sets) < n_tickets:
        raise ValueError("insufficient unique ticket candidates")
    hits = _sets_to_binary(scenario_sets) @ _sets_to_binary(candidate_sets).T
    selected: List[int] = []
    for _ in range(n_tickets):
        values = mean_candidate_scores(hits, selected)
        values[selected] = -np.inf
        selected.append(int(np.argmax(values)))

    for _ in range(max(0, int(local_passes))):
        changed = False
        for pos in range(n_tickets):
            remaining = selected[:pos] + selected[pos + 1:]
            values = mean_candidate_scores(hits, remaining)
            values[remaining] = -np.inf
            old_idx = selected[pos]
            best_idx = int(np.argmax(values))
            if values[best_idx] > values[old_idx] + 1e-12:
                selected[pos] = best_idx
                changed = True
        if not changed:
            break
    tickets = [tuple(int(n) for n in candidate_sets[j]) for j in selected]
    assert len(set(tickets)) == n_tickets
    return tickets, {
        "train_objective": float(np.mean(scenario_score(hits[:, selected]))),
        "scenario_count": float(scenarios),
        "candidate_count": float(len(candidate_sets)),
    }


def scenario_portfolio_mean(
    tickets: Sequence[Sequence[int]], scenario_sets: np.ndarray,
) -> float:
    if not tickets:
        raise ValueError("no portfolio tickets")
    mat = _sets_to_binary(np.asarray(tickets, dtype=int))
    hits = _sets_to_binary(scenario_sets) @ mat.T
    return float(np.mean(scenario_score(hits)))


def bootstrap_paired(values: Sequence[float], seed: int = 724055, reps: int = 4000) -> Dict[str, float]:
    arr = np.asarray(values, dtype=float)
    if arr.size == 0:
        raise ValueError("empty paired effect series")
    rng = np.random.default_rng(seed)
    samples = rng.integers(0, len(arr), size=(int(reps), len(arr)))
    draws = arr[samples].mean(axis=1)
    return {
        "mean": float(arr.mean()),
        "low95": float(np.quantile(draws, 0.025)),
        "high95": float(np.quantile(draws, 0.975)),
        "rounds": int(len(arr)),
    }


def append_rank_buckets(
    buckets: Dict[str, Dict[str, float]],
    raw: np.ndarray,
    gated: np.ndarray,
    actual: np.ndarray,
) -> None:
    ranking = np.argsort(-raw, kind="mergesort")
    for low, high in RANK_BUCKETS:
        idx = ranking[low - 1:high]
        bucket = buckets[f"{low:02d}-{high:02d}"]
        bucket["count"] += len(idx)
        bucket["realized"] += float(actual[idx].sum())
        bucket["raw_probability"] += float(raw[idx].sum())
        bucket["gated_probability"] += float(gated[idx].sum())


def audit(
    csv_path: Path,
    stored_csv: Path,
    stored_summary: Path,
    out_dir: Path,
    rounds: int = 60,
    independent_scenarios: int = 512,
) -> Dict[str, object]:
    x, cleaned = make_history(read_csv_flexible(csv_path))
    saved = json.loads(stored_summary.read_text(encoding="utf-8"))
    rows = load_historical_rows(stored_csv)
    if saved.get("evaluation_type") != "strict_prior_only_prequential_inclusion_probability_joint_set_v2":
        raise ValueError("stored v2 report is not strict prior-only nested")
    if len(rows) != int(saved.get("evaluated_rounds", -1)):
        raise ValueError("v2 nested row count and summary differ")
    if len(rows) < int(rounds) or rounds < 1:
        raise ValueError("invalid number of historical evaluation rounds")
    rows = rows[-int(rounds):]
    for row in rows:
        target = int(row["round_index"])
        if target < 1 or target > len(x):
            raise ValueError(f"missing historical actual outcome for round {target}")
        if str(cleaned["回別"].iloc[target - 1]).strip("第回") != str(target):
            raise ValueError(f"historical draw identity mismatch at {target}")

    configs = {cfg.version(): cfg for cfg in candidate_configs()}
    prior_min = int(saved["min_train"])
    scenarios = int(saved["validation_scenarios"])
    candidates = int(saved["validation_candidates"])
    required = sorted(set(row["selected_config"] for row in rows))
    for version in required:
        if version not in configs or version not in saved["config_versions"]:
            raise ValueError("stored selected config is not in locked v2 family")
    final_draw = int(rows[-1]["round_index"])
    # Evaluate only past draws up through the stored historical evaluation horizon.
    # All prequential training/calibration for target t use strictly rounds < t.
    preq = {
        version: build_prequential_signal(x[:final_draw], configs[version], prior_min)
        for version in required
    }
    buckets: Dict[str, Dict[str, float]] = defaultdict(
        lambda: {"count": 0.0, "realized": 0.0, "raw_probability": 0.0, "gated_probability": 0.0}
    )
    output_rows: List[Dict[str, object]] = []
    top7_same = 0
    gate_zero = 0
    verified_baseline = 0
    for saved_row in rows:
        target = int(saved_row["round_index"])
        t = target - 1
        version = saved_row["selected_config"]
        bundle = forecast(x[:t], configs[version], preq[version][:t - prior_min])
        gated = np.asarray(bundle.inclusion_p, dtype=float)
        raw = np.asarray(bundle.raw_inclusion_p, dtype=float)
        if not (abs(gated.sum() - PICKS) < 1e-8 and abs(raw.sum() - PICKS) < 1e-8):
            raise RuntimeError("replayed inclusion vector does not sum to seven")
        actual_idx = np.flatnonzero(x[t])
        y = x[t].astype(float)
        raw_metrics = bernoulli_signal_metrics(raw, actual_idx)
        gated_metrics = bernoulli_signal_metrics(gated, actual_idx)
        if abs(float(saved_row["signal_log_edge"]) - gated_metrics["log_edge"]) > 1e-9:
            raise RuntimeError(f"stored log edge failed exact reconstruction for {target}")
        if abs(float(saved_row["gate"]) - bundle.gate) > 1e-9:
            raise RuntimeError(f"stored v2 gate failed reconstruction for {target}")
        if abs(float(saved_row["signal_top7_hits"]) - gated_metrics["top7_hits"]) > 1e-9:
            raise RuntimeError(f"stored Top7 result failed reconstruction for {target}")
        top_raw = set(np.argsort(-raw, kind="mergesort")[:PICKS].tolist())
        top_gated = set(np.argsort(-gated, kind="mergesort")[:PICKS].tolist())
        top7_same += int(top_raw == top_gated)
        gate_zero += int(bundle.gate == 0.0)
        append_rank_buckets(buckets, raw, gated, y)

        seed = 123_000_000 + t * 1009  # exactly as stored strict v2 replay
        baseline, _ = expected_utility_portfolio(
            bundle, seed=seed, scenarios=scenarios, candidate_count=candidates,
        )
        actual_set = set((actual_idx + 1).tolist())
        baseline_score = float(portfolio_metrics(baseline, actual_set)["score"])
        if abs(float(saved_row["portfolio_score"]) - baseline_score) > 1e-9:
            raise RuntimeError(f"baseline five-ticket score not reconstructed for {target}")
        verified_baseline += 1
        aligned, _ = aligned_objective_portfolio(
            bundle, seed=seed, scenarios=scenarios, candidate_count=candidates,
        )
        aligned_score = float(portfolio_metrics(aligned, actual_set)["score"])

        # The optimizer's own construction scenarios; hold separate independent
        # Monte Carlo scenarios apart from both those and candidate draws.
        train_draws = sample_joint_sets(bundle, scenarios, seed=seed + 11)
        test_draws = sample_joint_sets(bundle, independent_scenarios, seed=seed + 9911)
        btrain = scenario_portfolio_mean(baseline, train_draws)
        btest = scenario_portfolio_mean(baseline, test_draws)
        atrain = scenario_portfolio_mean(aligned, train_draws)
        atest = scenario_portfolio_mean(aligned, test_draws)
        output_rows.append({
            "round_index": target,
            "selected_config": version,
            "gate": float(bundle.gate),
            "top7_raw": int(len(top_raw & set(actual_idx.tolist()))),
            "top7_gated": float(gated_metrics["top7_hits"]),
            "log_edge_raw": float(raw_metrics["log_edge"]),
            "log_edge_gated": float(gated_metrics["log_edge"]),
            "brier_edge_raw": float(raw_metrics["brier_edge"]),
            "brier_edge_gated": float(gated_metrics["brier_edge"]),
            "baseline_score": baseline_score,
            "aligned_score": aligned_score,
            "paired_delta": aligned_score - baseline_score,
            "baseline_train_mc": btrain,
            "baseline_independent_mc": btest,
            "aligned_train_mc": atrain,
            "aligned_independent_mc": atest,
            "baseline_mc_optimism": btrain - btest,
            "aligned_mc_optimism": atrain - atest,
        })

    def avg(name: str) -> float:
        return float(np.mean([float(row[name]) for row in output_rows]))

    rank_bins = []
    for low, high in RANK_BUCKETS:
        rec = buckets[f"{low:02d}-{high:02d}"]
        n = rec["count"]
        rank_bins.append({
            "raw_rank_bucket": f"{low}-{high}",
            "observations": int(n),
            "empirical_inclusion_rate": rec["realized"] / n,
            "mean_raw_inclusion_probability": rec["raw_probability"] / n,
            "mean_gated_inclusion_probability": rec["gated_probability"] / n,
        })
    diffs = [float(row["paired_delta"]) for row in output_rows]
    summary: Dict[str, object] = {
        "version": REPORT_VERSION,
        "research_only": True,
        "independent_evidence": False,
        "promotion_eligible": False,
        "source_existing_true_nested_data_sha256": saved["data_sha256"],
        "historical_rounds": len(output_rows),
        "historical_target_start": int(rows[0]["round_index"]),
        "historical_target_end": int(rows[-1]["round_index"]),
        "min_train": prior_min,
        "predeclared_v2_selection_not_retuned": True,
        "baseline_reconstruction_verified_rounds": verified_baseline,
        "train_scenarios": scenarios,
        "independent_simulator_scenarios": independent_scenarios,
        "candidate_count": candidates,
        "signal": {
            "raw_top7_mean_hits": avg("top7_raw"),
            "gated_top7_mean_hits": avg("top7_gated"),
            "same_raw_gated_top7_fraction": top7_same / len(output_rows),
            "zero_gate_rounds": gate_zero,
            "mean_gate": avg("gate"),
            "mean_raw_log_edge": avg("log_edge_raw"),
            "mean_gated_log_edge": avg("log_edge_gated"),
            "mean_raw_brier_edge": avg("brier_edge_raw"),
            "mean_gated_brier_edge": avg("brier_edge_gated"),
            "expected_uniform_top7_hits": float(PICKS * PICKS / N_NUMBERS),
            "rank_bucket_calibration": rank_bins,
        },
        "portfolio": {
            "baseline_mean_realized_score": avg("baseline_score"),
            "aligned_mean_realized_score": avg("aligned_score"),
            "aligned_minus_baseline_realized_paired": bootstrap_paired(diffs),
            "baseline_mean_training_scenario_score": avg("baseline_train_mc"),
            "baseline_mean_independent_scenario_score": avg("baseline_independent_mc"),
            "aligned_mean_training_scenario_score": avg("aligned_train_mc"),
            "aligned_mean_independent_scenario_score": avg("aligned_independent_mc"),
            "baseline_mc_optimism": avg("baseline_mc_optimism"),
            "aligned_mc_optimism": avg("aligned_mc_optimism"),
        },
        "interpretation_boundary": (
            "Historical exploratory reuse of the same 60 draws; neither aligned objective "
            "nor rank/calibration/gate diagnostics are untouched OOS evidence. "
            "Independent Monte Carlo scenarios test optimizer stability conditional on the "
            "same fitted model, not actual prospective forecasting accuracy. "
            "No selection or modification of Production, Champion or prefrozen shadow."
        ),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "joint_set_v2_conversion_audit_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    with (out_dir / "joint_set_v2_conversion_audit_rows.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as f:
        writer = csv.DictWriter(f, fieldnames=ROW_FIELDS)
        writer.writeheader()
        for row in output_rows:
            writer.writerow({key: row.get(key, "") for key in ROW_FIELDS})
    s = summary["signal"]
    p = summary["portfolio"]
    ci = p["aligned_minus_baseline_realized_paired"]
    lines = [
        "# Joint Set v2 — Rank / Calibration / Gate / Portfolio Conversion Audit",
        "",
        "- Research-only, historically reused data: **YES**",
        "- New independent real-world OOS: **NO**",
        "- Production promotion: **NO**",
        f"- evaluated saved strict-nested rounds: **{len(output_rows)}**",
        f"- baseline five-ticket scores independently reconstructed: **{verified_baseline}/{len(output_rows)}**",
        "",
        "## Raw rank versus gated inclusion",
        f"- mean raw Top7 hits: **{s['raw_top7_mean_hits']:.4f}**",
        f"- mean gated Top7 hits: **{s['gated_top7_mean_hits']:.4f}**",
        f"- raw/gated Top7 membership agreement: **{s['same_raw_gated_top7_fraction']:.1%}**",
        f"- mean uniform gate: **{s['mean_gate']:.4f}**; exactly-zero gate rounds: **{gate_zero}**",
        f"- raw/gated log-score edge vs uniform: **{s['mean_raw_log_edge']:+.6f} / {s['mean_gated_log_edge']:+.6f}**",
        f"- raw/gated Brier improvement vs uniform: **{s['mean_raw_brier_edge']:+.6f} / {s['mean_gated_brier_edge']:+.6f}**",
        "",
        "## Raw-rank-bucket calibration",
        "| Raw rank | Realized inclusion | Raw probability | Gated probability |",
        "|---|---:|---:|---:|",
    ]
    for row in rank_bins:
        lines.append(
            f"| {row['raw_rank_bucket']} | {row['empirical_inclusion_rate']:.4f}"
            f" | {row['mean_raw_inclusion_probability']:.4f}"
            f" | {row['mean_gated_inclusion_probability']:.4f} |"
        )
    lines.extend([
        "",
        "## Five-ticket objective-alignment diagnostic",
        f"- Original-objective mean realized score: **{p['baseline_mean_realized_score']:.4f}**",
        f"- Exact-evaluation-objective mean realized score: **{p['aligned_mean_realized_score']:.4f}**",
        f"- aligned-minus-original paired score: **{ci['mean']:+.4f}** "
        f"(historical bootstrap CI {ci['low95']:+.4f} to {ci['high95']:+.4f})",
        f"- original train / independent MC score: **{p['baseline_mean_training_scenario_score']:.4f} / {p['baseline_mean_independent_scenario_score']:.4f}**",
        f"- aligned train / independent MC score: **{p['aligned_mean_training_scenario_score']:.4f} / {p['aligned_mean_independent_scenario_score']:.4f}**",
        f"- original / aligned MC optimism: **{p['baseline_mc_optimism']:+.4f} / {p['aligned_mc_optimism']:+.4f}**",
        "",
        "> The MC validation scenarios are independent samples of the **same** fitted",
        "> generator; they are not independent winning-draw evidence.",
        "> Historical rounds were reused to motivate this design. No candidate is adopted",
        "> based on this report. The 26-draw prospective shadow and Production remain frozen.",
        "",
    ])
    (out_dir / "joint_set_v2_conversion_audit_report.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Research-only v2 rank/optimizer conversion audit")
    parser.add_argument("--csv", type=Path, default=Path("loto7.csv"))
    parser.add_argument("--stored-csv", type=Path, default=Path("loto7_agent_output/joint_set_v2_true_nested.csv"))
    parser.add_argument("--stored-summary", type=Path, default=Path("loto7_agent_output/joint_set_v2_true_nested_summary.json"))
    parser.add_argument("--out-dir", type=Path, default=Path("loto7_agent_output"))
    parser.add_argument("--rounds", type=int, default=60)
    parser.add_argument("--independent-scenarios", type=int, default=512)
    args = parser.parse_args()
    summary = audit(args.csv, args.stored_csv, args.stored_summary, args.out_dir,
                    rounds=args.rounds, independent_scenarios=args.independent_scenarios)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
