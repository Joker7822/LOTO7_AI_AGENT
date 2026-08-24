#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import numpy as np

import loto7_v2_runner as v2
import loto7_v3_runner as v3
import precision_random_baseline as prb
import separated_optimizer as so
from loto7_evolving_agent import expert_probabilities, fingerprint_file, make_history, make_ticket_portfolio, read_csv_flexible

REPORT_VERSION = "true-nested-evolution-v1"
FIELDS = [
    "round_index", "selected_model", "selected_overlap", "prior_signal_objective",
    "signal_top7_hits", "signal_actual_mass", "signal_log_edge", "signal_brier_edge",
    "portfolio_max_hits", "portfolio_mean_hits", "portfolio_ge3", "portfolio_ge4", "portfolio_score",
    "random_max_hits", "random_mean_hits", "random_ge3", "random_ge4", "random_score",
    "score_delta_vs_random",
]


def write_json(path: Path, obj: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv(path: Path, rows: Sequence[Dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in FIELDS})


def read_precision_rows(path: Path) -> Dict[int, Dict[str, float]]:
    out: Dict[int, Dict[str, float]] = {}
    with path.open(encoding="utf-8-sig", newline="") as f:
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


def prefix_sha(x: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(x).tobytes()).hexdigest()


def forecast_q(prefix: np.ndarray, cfg: v2.ModelConfig, min_train: int) -> np.ndarray:
    keys = list(expert_probabilities(prefix[:min_train]).keys())
    logw = np.zeros(len(keys), dtype=float)
    for t in range(min_train, len(prefix)):
        logw = v2._update_log_weights(prefix[:t], np.flatnonzero(prefix[t]), keys, logw, cfg)
    return v2._score_distribution(prefix, keys, logw, cfg)


def evolve_from_prior(prefix: np.ndarray, parent: v2.ModelConfig, min_train: int,
                      inner_candidates: int, step_id: int) -> Tuple[v2.ModelConfig, float, Dict[str, object]]:
    parent_windows, _ = so.replay_signal(prefix, parent, min_train, keep_q=False)
    parent_obj = so.weighted_signal_objective(parent_windows, parent)
    decisions: List[Dict[str, object]] = []
    accepted: List[Tuple[float, v2.ModelConfig]] = []
    psha = prefix_sha(prefix)
    for cfg in so.signal_candidates(parent, psha, step_id, count=inner_candidates):
        windows, _ = so.replay_signal(prefix, cfg, min_train, keep_q=False)
        ok, decision = so.signal_accept(windows, parent_windows, cfg, parent)
        decisions.append({"version": cfg.version(), "accepted": bool(ok), **decision})
        if ok:
            accepted.append((so.weighted_signal_objective(windows, cfg), cfg))
    if accepted:
        accepted.sort(key=lambda z: z[0], reverse=True)
        return accepted[0][1], float(accepted[0][0]), {"accepted": True, "decisions": decisions}
    return parent, float(parent_obj), {"accepted": False, "decisions": decisions}


def bootstrap_ci(values: Sequence[float], seed: int = 77123, reps: int = 5000) -> Dict[str, float]:
    arr = np.asarray(values, dtype=float)
    if len(arr) == 0:
        return {"mean": 0.0, "low95": 0.0, "high95": 0.0}
    rng = np.random.default_rng(seed)
    means = np.empty(reps, dtype=float)
    for i in range(reps):
        means[i] = float(np.mean(rng.choice(arr, size=len(arr), replace=True)))
    return {
        "mean": float(np.mean(arr)),
        "low95": float(np.quantile(means, 0.025)),
        "high95": float(np.quantile(means, 0.975)),
    }


def summarize(rows: Sequence[Dict[str, object]], data_sha: str, min_train: int,
              last_n: int, warmup_steps: int, inner_candidates: int,
              pool_size: int, random_reps: int) -> Dict[str, object]:
    deltas = [float(r["score_delta_vs_random"]) for r in rows]
    return {
        "report_version": REPORT_VERSION,
        "evaluation_type": "prequential_online_evolution_strict_prior_only",
        "data_sha256": data_sha,
        "min_train": min_train,
        "evaluated_rounds": len(rows),
        "last_n": last_n,
        "warmup_evolution_steps": warmup_steps,
        "inner_signal_candidates_per_step": inner_candidates,
        "portfolio_pool_size": pool_size,
        "random_portfolios_per_round": random_reps,
        "starting_model": v2.DEFAULT_CHAMPION.version(),
        "leakage_control": (
            "At target t, the evolutionary parent, candidate mutation seed, candidate scoring, and model selection "
            "use x[:t] only. The current v4 Research Winner is never injected. Target x[t] is read only after selection."
        ),
        "signal": {
            "mean_top7_hits": float(np.mean([float(r["signal_top7_hits"]) for r in rows])) if rows else 0.0,
            "top7_delta_vs_uniform": (float(np.mean([float(r["signal_top7_hits"]) for r in rows])) - so.UNIFORM_TOP7_HITS) if rows else 0.0,
            "mean_actual_mass": float(np.mean([float(r["signal_actual_mass"]) for r in rows])) if rows else 0.0,
            "mean_log_edge_vs_uniform": float(np.mean([float(r["signal_log_edge"]) for r in rows])) if rows else 0.0,
            "mean_brier_edge_vs_uniform": float(np.mean([float(r["signal_brier_edge"]) for r in rows])) if rows else 0.0,
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
        "interpretation": (
            "This is substantially stricter historical evidence than applying today's winner to old draws, "
            "but only frozen future OOS can promote Production."
        ),
    }


def render_report(summary: Dict[str, object]) -> str:
    s = summary["signal"]
    p = summary["portfolio"]
    ci = p["score_delta_vs_random"]
    return "\n".join([
        "# True Nested / Prequential Evolution",
        "",
        f"- evaluated rounds: **{summary['evaluated_rounds']}**",
        f"- warm-up evolution steps: **{summary['warmup_evolution_steps']}**",
        f"- inner signal candidates/step: **{summary['inner_signal_candidates_per_step']}**",
        "- current Research Winner injected into history: **NO**",
        "- target result used before model selection: **NO**",
        "- Portfolio overlap during this test: **predeclared starting policy, not retrospectively optimized**",
        "",
        "## Signal",
        f"- mean Top7 hits: **{s['mean_top7_hits']:.4f}** (delta vs uniform {s['top7_delta_vs_uniform']:+.4f})",
        f"- mean actual mass: **{s['mean_actual_mass']:.6f}**",
        f"- mean log edge vs uniform: **{s['mean_log_edge_vs_uniform']:+.6f}**",
        f"- mean Brier edge vs uniform: **{s['mean_brier_edge_vs_uniform']:+.6f}**",
        "",
        "## Five-ticket Portfolio",
        f"- mean max hits: **{p['mean_max_hits']:.4f}** / precision random **{p['random_mean_max_hits']:.4f}**",
        f"- >=3 round rate: **{p['ge3_round_rate']*100:.2f}%** / random **{p['random_ge3_rate']*100:.2f}%**",
        f"- >=4 round rate: **{p['ge4_round_rate']*100:.2f}%** / random **{p['random_ge4_rate']*100:.2f}%**",
        f"- score: **{p['mean_score']:.4f}** / random **{p['random_mean_score']:.4f}**",
        f"- score delta: **{ci['mean']:+.4f}** (bootstrap 95% CI {ci['low95']:+.4f}〜{ci['high95']:+.4f})",
        f"- round win rate vs random: **{p['round_win_rate_vs_random']*100:.1f}%**",
        "",
        "> 各対象回で、その回より前の履歴だけを使って進化・選択してから1回だけ予測するprequential評価です。",
        "> 過去診断であり、Production昇格は未来OOSのみです。",
        "",
    ])


def is_fresh(path: Path, data_sha: str, min_train: int, last_n: int,
             warmup_steps: int, inner_candidates: int, pool_size: int, random_reps: int) -> bool:
    if not path.exists():
        return False
    try:
        old = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return False
    return bool(
        old.get("report_version") == REPORT_VERSION
        and old.get("data_sha256") == data_sha
        and int(old.get("min_train", -1)) == min_train
        and int(old.get("last_n", -1)) == last_n
        and int(old.get("warmup_evolution_steps", -1)) == warmup_steps
        and int(old.get("inner_signal_candidates_per_step", -1)) == inner_candidates
        and int(old.get("portfolio_pool_size", -1)) == pool_size
        and int(old.get("random_portfolios_per_round", -1)) == random_reps
    )


def run(csv_path: Path = Path("loto7.csv"), out_dir: Path = Path("loto7_agent_output"),
        min_train: int = 100, last_n: int = 60, warmup_steps: int = 60,
        inner_candidates: int = 2, pool_size: int = 180, random_reps: int = 4096,
        if_stale: bool = True) -> Dict[str, object]:
    df = read_csv_flexible(csv_path)
    x, _ = make_history(df)
    data_sha = fingerprint_file(csv_path)
    summary_path = out_dir / "true_nested_evolution_summary.json"
    if if_stale and is_fresh(summary_path, data_sha, min_train, last_n, warmup_steps,
                              inner_candidates, pool_size, random_reps):
        return json.loads(summary_path.read_text(encoding="utf-8"))

    prb.ensure(csv_path, out_dir, min_train=min_train, reps=random_reps)
    random_rows = read_precision_rows(out_dir / "precision_random_baseline.csv")
    eval_start = max(min_train + 30, len(x) - last_n)
    evolution_start = max(min_train + 30, eval_start - warmup_steps)
    parent = v2.DEFAULT_CHAMPION
    rows: List[Dict[str, object]] = []

    for t in range(evolution_start, len(x)):
        prefix = x[:t]
        parent, prior_obj, _ = evolve_from_prior(prefix, parent, min_train, inner_candidates, t + 1)
        if t < eval_start:
            continue
        q = forecast_q(prefix, parent, min_train)
        actual_idx = np.flatnonzero(x[t])
        sig = so.signal_row(q, actual_idx)
        tickets = make_ticket_portfolio(
            q, n_tickets=5, seed=77_000_000 + t * 1009,
            pool_size=pool_size, overlap_penalty=float(parent.overlap_penalty),
        )
        actual_set = set((actual_idx + 1).tolist())
        pm = v2._portfolio_metrics(tickets, actual_set)
        pscore = float(v3.row_score(pm))
        rnd = random_rows.get(t + 1)
        if rnd is None:
            raise RuntimeError(f"precision random baseline missing round_index={t+1}")
        rows.append({
            "round_index": t + 1,
            "selected_model": parent.version(),
            "selected_overlap": float(parent.overlap_penalty),
            "prior_signal_objective": float(prior_obj),
            "signal_top7_hits": float(sig["top7_hits"]),
            "signal_actual_mass": float(sig["actual_mass"]),
            "signal_log_edge": float(sig["mean_log_prob_actual"] - so.UNIFORM_LOG_PROB),
            "signal_brier_edge": float(sig["uniform_brier"] - sig["brier"]),
            "portfolio_max_hits": float(pm["max_hits"]),
            "portfolio_mean_hits": float(pm["mean_hits"]),
            "portfolio_ge3": float(pm["ge3"]),
            "portfolio_ge4": float(pm["ge4"]),
            "portfolio_score": pscore,
            **rnd,
            "score_delta_vs_random": pscore - float(rnd["random_score"]),
        })

    summary = summarize(rows, data_sha, min_train, last_n, warmup_steps,
                        inner_candidates, pool_size, random_reps)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(summary_path, summary)
    write_csv(out_dir / "true_nested_evolution.csv", rows)
    (out_dir / "true_nested_evolution_report.md").write_text(render_report(summary), encoding="utf-8")
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description="Run strict prequential online evolution using only data available before each target draw")
    ap.add_argument("--csv", type=Path, default=Path("loto7.csv"))
    ap.add_argument("--out-dir", type=Path, default=Path("loto7_agent_output"))
    ap.add_argument("--min-train", type=int, default=100)
    ap.add_argument("--last-n", type=int, default=60)
    ap.add_argument("--warmup-steps", type=int, default=60)
    ap.add_argument("--inner-candidates", type=int, default=2)
    ap.add_argument("--pool-size", type=int, default=180)
    ap.add_argument("--random-reps", type=int, default=4096)
    ap.add_argument("--if-stale", action="store_true")
    args = ap.parse_args()
    summary = run(args.csv, args.out_dir, args.min_train, args.last_n, args.warmup_steps,
                  args.inner_candidates, args.pool_size, args.random_reps, args.if_stale)
    print(f"[TRUE-NESTED] rounds={summary['evaluated_rounds']} log_edge={summary['signal']['mean_log_edge_vs_uniform']:+.6f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
