#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, List, Sequence

import numpy as np

import loto7_v2_runner as v2
import separated_optimizer as so
import signal_meta_model as meta
from loto7_evolving_agent import fingerprint_file, make_history, read_csv_flexible

REPORT_VERSION = "signal-meta-nested-replay-v1"


def _uniform_rows(x: np.ndarray, min_train: int) -> List[Dict[str, float]]:
    return [so.signal_row(so.UNIFORM_Q, np.flatnonzero(x[t])) for t in range(min_train, len(x))]


def _hedge_rows(x: np.ndarray, min_train: int) -> tuple[List[Dict[str, float]], List[np.ndarray]]:
    _, qs = so.replay_signal(x, v2.DEFAULT_CHAMPION, min_train=min_train, keep_q=True)
    rows = [so.signal_row(q, np.flatnonzero(x[t])) for q, t in zip(qs, range(min_train, len(x)))]
    return rows, qs


def _paired(values_a: Sequence[Dict[str, float]], values_b: Sequence[Dict[str, float]],
            key: str, sign: float = 1.0) -> List[float]:
    n = min(len(values_a), len(values_b))
    return [float(sign * (values_a[-n + i][key] - values_b[-n + i][key])) for i in range(n)]


def _current_meta_q(x: np.ndarray, replay: Dict[str, object]) -> np.ndarray:
    names = list(replay["feature_names"])
    weights_map = replay["final_weights"]
    weights = np.array([float(weights_map[name]) for name in names], dtype=float)
    features, current_names = meta.feature_matrix(x)
    if current_names != names:
        raise RuntimeError("current feature schema does not match replay schema")
    cfg = meta.MetaConfig(**replay["config"])
    return meta.predict_from_features(features, weights, cfg.uniform_mix)


def _write_rounds(path: Path, clean, x: np.ndarray, min_train: int,
                  nested: Dict[str, object], hedge_rows: Sequence[Dict[str, float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    start = int(nested["start_index"])
    rows = nested["rows"]
    versions = nested["selected_versions"]
    fields = [
        "round", "draw_date", "selected_meta_version",
        "meta_top7_hits", "hedge_top7_hits",
        "meta_actual_mass", "hedge_actual_mass",
        "meta_mean_log_prob_actual", "hedge_mean_log_prob_actual",
        "meta_brier", "hedge_brier",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for j, row in enumerate(rows):
            idx = start + j
            t = min_train + idx
            h = hedge_rows[idx]
            draw_round = clean["回別"].iloc[t] if "回別" in clean.columns else t + 1
            draw_date = clean["抽せん日"].iloc[t].date().isoformat()
            w.writerow({
                "round": draw_round,
                "draw_date": draw_date,
                "selected_meta_version": versions[j],
                "meta_top7_hits": f"{row['top7_hits']:.6f}",
                "hedge_top7_hits": f"{h['top7_hits']:.6f}",
                "meta_actual_mass": f"{row['actual_mass']:.12f}",
                "hedge_actual_mass": f"{h['actual_mass']:.12f}",
                "meta_mean_log_prob_actual": f"{row['mean_log_prob_actual']:.12f}",
                "hedge_mean_log_prob_actual": f"{h['mean_log_prob_actual']:.12f}",
                "meta_brier": f"{row['brier']:.12f}",
                "hedge_brier": f"{h['brier']:.12f}",
            })


def run(csv_path: Path, out_dir: Path, min_train: int = 100, last_n: int = 120,
        bootstrap_reps: int = 4000) -> Dict[str, object]:
    df = read_csv_flexible(csv_path)
    x, clean = make_history(df)
    features, feature_names = meta.precompute_features(x, min_train)
    replays = [meta.replay_config(x, cfg, min_train=min_train, features=features) for cfg in meta.PREDECLARED_CONFIGS]
    nested = meta.nested_select(replays, last_n=last_n)

    hedge_rows, _ = _hedge_rows(x, min_train)
    uniform_rows = _uniform_rows(x, min_train)
    n = int(nested["last_n"])
    meta_rows = list(nested["rows"])
    hedge_eval = hedge_rows[-n:]
    uniform_eval = uniform_rows[-n:]

    meta_signal = so.aggregate_signal(meta_rows)
    hedge_signal = so.aggregate_signal(hedge_eval)
    uniform_signal = so.aggregate_signal(uniform_eval)

    log_delta = _paired(meta_rows, hedge_eval, "mean_log_prob_actual")
    brier_improvement = _paired(hedge_eval, meta_rows, "brier")
    top7_delta = _paired(meta_rows, hedge_eval, "top7_hits")
    mass_delta = _paired(meta_rows, hedge_eval, "actual_mass")

    ci_log = meta.block_bootstrap_mean_ci(log_delta, seed=41_000_001, reps=bootstrap_reps, block_len=8)
    ci_brier = meta.block_bootstrap_mean_ci(brier_improvement, seed=41_000_002, reps=bootstrap_reps, block_len=8)
    ci_top7 = meta.block_bootstrap_mean_ci(top7_delta, seed=41_000_003, reps=bootstrap_reps, block_len=8)
    ci_mass = meta.block_bootstrap_mean_ci(mass_delta, seed=41_000_004, reps=bootstrap_reps, block_len=8)

    config_summaries = []
    for r in replays:
        config_summaries.append({
            "version": r["version"],
            "config": r["config"],
            "full_signal": r["windows"]["full"],
            "last120_signal": r["windows"]["120"],
            "selector_score_full": meta.selector_score(r["rows"]),
            "max_weight_abs": r["max_weight_abs"],
            "mean_weight_norm": r["mean_weight_norm"],
        })

    # Pick the next-draw research model using only already-scored historical rows.
    ranked = sorted(
        [(meta.selector_score(r["rows"]), str(r["version"]), r) for r in replays],
        key=lambda z: (z[0], z[1]), reverse=True,
    )
    next_score, next_version, next_replay = ranked[0]
    next_q = _current_meta_q(x, next_replay)
    ranking = np.argsort(next_q)[::-1] + 1

    # A retrospective signal must beat Uniform on proper scores before it is even
    # considered research-worthy. Historical success never grants Production status.
    research_worthy = bool(
        meta_signal["log_edge_vs_uniform"] > 0.0
        and meta_signal["brier_edge_vs_uniform"] > 0.0
        and meta_signal["actual_mass_delta_vs_uniform"] > 0.0
        and ci_log["mean"] > 0.0
        and ci_brier["mean"] > 0.0
    )
    robust_historical_improvement = bool(
        research_worthy
        and ci_log["low95"] > 0.0
        and ci_brier["low95"] > 0.0
    )

    latest_round_text = str(clean["回別"].iloc[-1]) if "回別" in clean.columns else str(len(clean))
    digits = "".join(ch for ch in latest_round_text if ch.isdigit())
    target_round = int(digits) + 1 if digits else len(clean) + 1

    summary: Dict[str, object] = {
        "report_version": REPORT_VERSION,
        "model_version": meta.MODEL_VERSION,
        "evaluation_type": "signal_only_true_walk_forward_predeclared_meta_family",
        "data_sha256": fingerprint_file(csv_path),
        "source_rows": int(len(x)),
        "min_train": int(min_train),
        "nested_last_n": n,
        "feature_names": feature_names,
        "predeclared_configs": config_summaries,
        "nested_meta": {
            "signal": meta_signal,
            "selected_counts": nested["selected_counts"],
        },
        "champion_hedge": {
            "version": v2.DEFAULT_CHAMPION.version(),
            "signal": hedge_signal,
        },
        "uniform_reference": uniform_signal,
        "paired_block_bootstrap_vs_champion_hedge": {
            "log_probability_delta": ci_log,
            "brier_improvement": ci_brier,
            "top7_hits_delta": ci_top7,
            "actual_mass_delta": ci_mass,
        },
        "research_worthy_signal": research_worthy,
        "robust_historical_improvement": robust_historical_improvement,
        "historical_evidence_only": True,
        "production_promotion_eligible": False,
        "future_oos_status": "not_registered",
        "next_research_target_round": target_round,
        "next_research_model_version": next_version,
        "next_research_selector_score": float(next_score),
        "next_research_top15": [
            {"number": int(num), "relative_score": float(next_q[num - 1]), "index_vs_uniform": float(next_q[num - 1] * 37.0)}
            for num in ranking[:15]
        ],
        "interpretation": (
            "Retrospective signal-only evidence. A positive result still requires matched null calibration and a new pre-frozen Future-OOS protocol before any Production claim."
        ),
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "signal_meta_replay_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    _write_rounds(out_dir / "signal_meta_replay_rounds.csv", clean, x, min_train, nested, hedge_rows)
    with (out_dir / "signal_meta_next_ranking.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["rank", "number", "relative_score", "index_vs_uniform"])
        w.writeheader()
        for rank_no, num in enumerate(ranking, 1):
            w.writerow({
                "rank": rank_no, "number": int(num),
                "relative_score": f"{next_q[num - 1]:.12f}",
                "index_vs_uniform": f"{next_q[num - 1] * 37.0:.8f}",
            })

    report = [
        "# Regularized Signal Meta-Model Replay",
        "",
        f"- model: **{meta.MODEL_VERSION}**",
        f"- evaluated nested window: **{n} draws**",
        f"- next research target: **round {target_round}**",
        f"- next research model: **{next_version}**",
        "- role: **Research signal only; no Production promotion authority**",
        "",
        "## Nested signal vs Uniform",
        "",
        f"- Top-7 hits: **{meta_signal['top7_hits']:.6f}** (edge {meta_signal['top7_hits_delta_vs_uniform']:+.6f})",
        f"- actual mass edge: **{meta_signal['actual_mass_delta_vs_uniform']:+.8f}**",
        f"- log edge: **{meta_signal['log_edge_vs_uniform']:+.8f}**",
        f"- Brier edge: **{meta_signal['brier_edge_vs_uniform']:+.8f}**",
        "",
        "## Paired vs current Champion Hedge",
        "",
        f"- log delta: **{ci_log['mean']:+.8f}** (moving-block 95% CI {ci_log['low95']:+.8f} .. {ci_log['high95']:+.8f})",
        f"- Brier improvement: **{ci_brier['mean']:+.8f}** (95% CI {ci_brier['low95']:+.8f} .. {ci_brier['high95']:+.8f})",
        f"- Top-7 delta: **{ci_top7['mean']:+.6f}** (95% CI {ci_top7['low95']:+.6f} .. {ci_top7['high95']:+.6f})",
        f"- actual mass delta: **{ci_mass['mean']:+.8f}** (95% CI {ci_mass['low95']:+.8f} .. {ci_mass['high95']:+.8f})",
        "",
        f"- research-worthy signal: **{str(research_worthy).lower()}**",
        f"- robust historical improvement: **{str(robust_historical_improvement).lower()}**",
        "",
        "> This report intentionally does not optimize ticket overlap or portfolio score. It tests number-ranking signal first.",
    ]
    (out_dir / "signal_meta_replay_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description="LOTO7 regularized signal meta-model replay")
    ap.add_argument("--csv", type=Path, default=Path("loto7.csv"))
    ap.add_argument("--out-dir", type=Path, default=Path("loto7_agent_output"))
    ap.add_argument("--min-train", type=int, default=100)
    ap.add_argument("--last-n", type=int, default=120)
    ap.add_argument("--bootstrap-reps", type=int, default=4000)
    args = ap.parse_args()
    summary = run(args.csv, args.out_dir, args.min_train, args.last_n, args.bootstrap_reps)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
