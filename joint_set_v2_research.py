#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import numpy as np

import precision_random_baseline as prb
from joint_set_v2_model import (
    JointSetV2Config,
    bernoulli_signal_metrics,
    candidate_configs,
    expected_utility_portfolio,
    forecast,
    portfolio_metrics,
    signal_quality,
)
from loto7_evolving_agent import fingerprint_file, make_history, read_csv_flexible

REPORT_VERSION = "joint-set-v2-true-nested-v1"
FIELDS = [
    "round_index", "selected_config", "selected_config_score", "gate",
    "regime_stable", "regime_shift", "regime_volatile",
    "signal_top7_hits", "signal_actual_mass", "signal_log_edge", "signal_brier_edge",
    "portfolio_max_hits", "portfolio_mean_hits", "portfolio_ge3", "portfolio_ge4", "portfolio_score",
    "random_max_hits", "random_mean_hits", "random_ge3", "random_ge4", "random_score",
    "score_delta_vs_random",
]


def parse_round(value: object, fallback: int) -> int:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    return int(digits) if digits else int(fallback)


def write_json(path: Path, obj: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def read_precision_rows(path: Path) -> Dict[int, Dict[str, float]]:
    out: Dict[int, Dict[str, float]] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            idx = int(row["round_index"])
            out[idx] = {
                "random_max_hits": float(row["mean_max_hits"]),
                "random_mean_hits": float(row["mean_ticket_hits"]),
                "random_ge3": float(row["ge3_rate"]),
                "random_ge4": float(row["ge4_rate"]),
                "random_score": float(row["mean_score"]),
            }
    return out


def build_prequential_signal(x: np.ndarray, cfg: JointSetV2Config, min_train: int) -> List[Dict[str, float]]:
    rows: List[Dict[str, float]] = []
    for t in range(min_train, len(x)):
        bundle = forecast(x[:t], cfg, rows)
        row = bernoulli_signal_metrics(bundle.inclusion_p, np.flatnonzero(x[t]))
        row.update({
            "gate": float(bundle.gate),
            "regime_stable": float(bundle.regime[0]),
            "regime_shift": float(bundle.regime[1]),
            "regime_volatile": float(bundle.regime[2]),
        })
        rows.append(row)
    return rows


def robust_prior_score(rows: Sequence[Dict[str, float]], window: int = 120) -> float:
    recent = list(rows[-max(30, int(window)):])
    if len(recent) < 30:
        return -1e9
    values = np.array([signal_quality(r) for r in recent], dtype=float)
    chunks = [x for x in np.array_split(values, 3) if len(x)]
    worst = min(float(x.mean()) for x in chunks)
    return float(values.mean() + 0.30 * worst - 0.10 * values.std())


def select_config(
    configs: Sequence[JointSetV2Config],
    prequential: Dict[str, List[Dict[str, float]]],
    prior_count: int,
    selection_window: int,
) -> Tuple[JointSetV2Config, float]:
    ranked: List[Tuple[float, str, JointSetV2Config]] = []
    for cfg in configs:
        rows = prequential[cfg.version()][:max(0, int(prior_count))]
        score = robust_prior_score(rows, selection_window)
        ranked.append((score, cfg.version(), cfg))
    ranked.sort(key=lambda z: (z[0], z[1]), reverse=True)
    return ranked[0][2], float(ranked[0][0])


def bootstrap_ci(values: Sequence[float], seed: int = 20310917, reps: int = 5000) -> Dict[str, float]:
    arr = np.asarray(values, dtype=float)
    if len(arr) == 0:
        return {"mean": 0.0, "low95": 0.0, "high95": 0.0}
    rng = np.random.default_rng(seed)
    means = np.array([float(np.mean(rng.choice(arr, size=len(arr), replace=True))) for _ in range(int(reps))])
    return {"mean": float(arr.mean()), "low95": float(np.quantile(means, 0.025)), "high95": float(np.quantile(means, 0.975))}


def write_rows(path: Path, rows: Sequence[Dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in FIELDS})


def summarize(
    rows: Sequence[Dict[str, object]],
    data_sha: str,
    configs: Sequence[JointSetV2Config],
    min_train: int,
    last_n: int,
    selection_window: int,
    validation_scenarios: int,
    validation_candidates: int,
) -> Dict[str, object]:
    deltas = [float(r["score_delta_vs_random"]) for r in rows]
    selected = Counter(str(r["selected_config"]) for r in rows)
    return {
        "report_version": REPORT_VERSION,
        "evaluation_type": "strict_prior_only_prequential_inclusion_probability_joint_set_v2",
        "data_sha256": data_sha,
        "min_train": int(min_train),
        "last_n": int(last_n),
        "evaluated_rounds": len(rows),
        "selection_window": int(selection_window),
        "predeclared_config_count": len(configs),
        "config_versions": [c.version() for c in configs],
        "validation_scenarios": int(validation_scenarios),
        "validation_candidates": int(validation_candidates),
        "components": {
            "bernoulli_inclusion_probability_sum_7": True,
            "proper_log_score_all_37_numbers": True,
            "proper_brier_score_all_37_numbers": True,
            "low_rank_pair_interaction": True,
            "hidden_regime_filter": True,
            "dynamic_uniform_gate": True,
            "expected_utility_portfolio": True,
            "external_metadata": False,
        },
        "selected_config_counts": dict(selected),
        "signal": {
            "mean_top7_hits": float(np.mean([float(r["signal_top7_hits"]) for r in rows])) if rows else 0.0,
            "mean_actual_inclusion_probability": float(np.mean([float(r["signal_actual_mass"]) for r in rows])) if rows else 0.0,
            "mean_log_edge_vs_uniform": float(np.mean([float(r["signal_log_edge"]) for r in rows])) if rows else 0.0,
            "mean_brier_edge_vs_uniform": float(np.mean([float(r["signal_brier_edge"]) for r in rows])) if rows else 0.0,
            "mean_gate": float(np.mean([float(r["gate"]) for r in rows])) if rows else 0.0,
        },
        "portfolio": {
            "mean_max_hits": float(np.mean([float(r["portfolio_max_hits"]) for r in rows])) if rows else 0.0,
            "random_mean_max_hits": float(np.mean([float(r["random_max_hits"]) for r in rows])) if rows else 0.0,
            "ge3_round_rate": float(np.mean([float(r["portfolio_ge3"]) for r in rows])) if rows else 0.0,
            "random_ge3_rate": float(np.mean([float(r["random_ge3"]) for r in rows])) if rows else 0.0,
            "ge4_round_rate": float(np.mean([float(r["portfolio_ge4"]) for r in rows])) if rows else 0.0,
            "random_ge4_rate": float(np.mean([float(r["random_ge4"]) for r in rows])) if rows else 0.0,
            "mean_score": float(np.mean([float(r["portfolio_score"]) for r in rows])) if rows else 0.0,
            "random_mean_score": float(np.mean([float(r["random_score"]) for r in rows])) if rows else 0.0,
            "score_delta_vs_random": bootstrap_ci(deltas),
            "round_win_rate_vs_random": float(np.mean([d > 0 for d in deltas])) if deltas else 0.0,
        },
        "independent_evidence": False,
        "promotion_eligible": False,
        "leakage_control": "At target t all config selection, calibration, pair/regime estimation, and portfolio construction use only draws before t.",
        "interpretation": "Research-only v2 challenger. Production remains governed by frozen Future OOS evidence.",
    }


def render_report(summary: Dict[str, object]) -> str:
    s, p = summary["signal"], summary["portfolio"]
    ci = p["score_delta_vs_random"]
    return "\n".join([
        "# Joint Set Research v2 — Inclusion Probability Strict True Nested",
        "",
        f"- evaluated rounds: **{summary['evaluated_rounds']}**",
        f"- predeclared configs: **{summary['predeclared_config_count']}**",
        f"- selection window: **{summary['selection_window']}** prior draws",
        "- target result used before selection: **NO**",
        "- Production promotion eligible: **NO**",
        "",
        "## Bernoulli Inclusion Signal (sum p = 7)",
        f"- mean Top7 hits: **{s['mean_top7_hits']:.4f}**",
        f"- mean actual inclusion probability: **{s['mean_actual_inclusion_probability']:.6f}**",
        f"- mean Bernoulli log edge vs uniform: **{s['mean_log_edge_vs_uniform']:+.6f}**",
        f"- mean Bernoulli Brier edge vs uniform: **{s['mean_brier_edge_vs_uniform']:+.6f}**",
        f"- mean model gate: **{s['mean_gate']:.3f}**",
        "",
        "## Expected-Utility Five-Ticket Portfolio",
        f"- mean max hits: **{p['mean_max_hits']:.4f}** / random **{p['random_mean_max_hits']:.4f}**",
        f"- >=3 round rate: **{p['ge3_round_rate']*100:.2f}%** / random **{p['random_ge3_rate']*100:.2f}%**",
        f"- >=4 round rate: **{p['ge4_round_rate']*100:.2f}%** / random **{p['random_ge4_rate']*100:.2f}%**",
        f"- score: **{p['mean_score']:.4f}** / random **{p['random_mean_score']:.4f}**",
        f"- score delta: **{ci['mean']:+.4f}** (bootstrap 95% CI {ci['low95']:+.4f}〜{ci['high95']:+.4f})",
        "",
        "> v2は37数字を独立カテゴリ確率ではなく、合計7のinclusion probabilityとして校正します。",
        "> Research-only。Future OOS確認前にProductionへ昇格しません。",
        "",
    ])


def run(
    csv_path: Path = Path("loto7.csv"),
    out_dir: Path = Path("loto7_agent_output"),
    min_train: int = 100,
    last_n: int = 60,
    selection_window: int = 120,
    validation_scenarios: int = 256,
    validation_candidates: int = 64,
    current_scenarios: int = 2048,
    current_candidates: int = 128,
    random_reps: int = 4096,
) -> Dict[str, object]:
    df = read_csv_flexible(csv_path)
    x, clean = make_history(df)
    data_sha = fingerprint_file(csv_path)
    configs = candidate_configs()
    preq = {cfg.version(): build_prequential_signal(x, cfg, min_train) for cfg in configs}
    prb.ensure(csv_path, out_dir, min_train=min_train, reps=random_reps)
    random_rows = read_precision_rows(out_dir / "precision_random_baseline.csv")
    eval_start = max(min_train + 30, len(x) - int(last_n))
    rows: List[Dict[str, object]] = []
    for t in range(eval_start, len(x)):
        prior_count = t - min_train
        cfg, cfg_score = select_config(configs, preq, prior_count, selection_window)
        bundle = forecast(x[:t], cfg, preq[cfg.version()][:prior_count])
        actual_idx = np.flatnonzero(x[t])
        sig = bernoulli_signal_metrics(bundle.inclusion_p, actual_idx)
        tickets, _ = expected_utility_portfolio(
            bundle, seed=123_000_000 + t * 1009,
            scenarios=validation_scenarios, candidate_count=validation_candidates,
        )
        pm = portfolio_metrics(tickets, set((actual_idx + 1).tolist()))
        rnd = random_rows.get(t + 1)
        if rnd is None:
            raise RuntimeError(f"precision random baseline missing round_index={t+1}")
        rows.append({
            "round_index": t + 1,
            "selected_config": cfg.version(), "selected_config_score": cfg_score,
            "gate": bundle.gate,
            "regime_stable": float(bundle.regime[0]), "regime_shift": float(bundle.regime[1]), "regime_volatile": float(bundle.regime[2]),
            "signal_top7_hits": sig["top7_hits"], "signal_actual_mass": sig["actual_mass"],
            "signal_log_edge": sig["log_edge"], "signal_brier_edge": sig["brier_edge"],
            "portfolio_max_hits": pm["max_hits"], "portfolio_mean_hits": pm["mean_hits"],
            "portfolio_ge3": pm["ge3"], "portfolio_ge4": pm["ge4"], "portfolio_score": pm["score"],
            **rnd, "score_delta_vs_random": float(pm["score"] - rnd["random_score"]),
        })
    summary = summarize(rows, data_sha, configs, min_train, last_n, selection_window, validation_scenarios, validation_candidates)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "joint_set_v2_true_nested_summary.json", summary)
    write_rows(out_dir / "joint_set_v2_true_nested.csv", rows)
    (out_dir / "joint_set_v2_true_nested_report.md").write_text(render_report(summary), encoding="utf-8")

    target_t = len(x)
    cfg, cfg_score = select_config(configs, preq, target_t - min_train, selection_window)
    bundle = forecast(x, cfg, preq[cfg.version()])
    latest_round = parse_round(clean["回別"].iloc[-1] if "回別" in clean.columns else len(clean), len(clean))
    target_round = latest_round + 1
    tickets, diagnostics = expected_utility_portfolio(
        bundle, seed=127_000_000 + target_round * 1009,
        scenarios=current_scenarios, candidate_count=current_candidates,
    )
    current = {
        "report_version": "joint-set-v2-current-research-v1",
        "data_sha256": data_sha,
        "target_round": target_round,
        "selected_config": cfg.version(),
        "selected_config_prior_score": cfg_score,
        "gate": bundle.gate,
        "gate_diagnostics": bundle.gate_diagnostics,
        "inclusion_sum": float(bundle.inclusion_p.sum()),
        "regime": {"stable": float(bundle.regime[0]), "shift": float(bundle.regime[1]), "volatile": float(bundle.regime[2])},
        "portfolio_diagnostics": diagnostics,
        "tickets": [[int(n) for n in ticket] for ticket in tickets],
        "research_only": True,
        "promotion_eligible": False,
    }
    write_json(out_dir / "joint_set_v2_current_research.json", current)
    with (out_dir / "joint_set_v2_candidate_tickets.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["ticket", "numbers", "sum", "odd_count"])
        w.writeheader()
        for i, ticket in enumerate(tickets, 1):
            w.writerow({"ticket": i, "numbers": " ".join(f"{int(n):02d}" for n in ticket), "sum": sum(ticket), "odd_count": sum(int(n) % 2 for n in ticket)})
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description="Research-only Joint Set v2 inclusion-probability strict replay")
    ap.add_argument("--csv", type=Path, default=Path("loto7.csv"))
    ap.add_argument("--out-dir", type=Path, default=Path("loto7_agent_output"))
    ap.add_argument("--min-train", type=int, default=100)
    ap.add_argument("--last-n", type=int, default=60)
    ap.add_argument("--selection-window", type=int, default=120)
    ap.add_argument("--validation-scenarios", type=int, default=256)
    ap.add_argument("--validation-candidates", type=int, default=64)
    ap.add_argument("--current-scenarios", type=int, default=2048)
    ap.add_argument("--current-candidates", type=int, default=128)
    ap.add_argument("--random-reps", type=int, default=4096)
    args = ap.parse_args()
    summary = run(
        args.csv, args.out_dir, args.min_train, args.last_n, args.selection_window,
        args.validation_scenarios, args.validation_candidates,
        args.current_scenarios, args.current_candidates, args.random_reps,
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
