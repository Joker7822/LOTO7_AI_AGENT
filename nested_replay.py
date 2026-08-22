#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

import numpy as np

import loto7_v2_runner as v2
import loto7_v3_runner as v3
from loto7_evolving_agent import expert_probabilities, fingerprint_file, make_history, make_ticket_portfolio, read_csv_flexible

REPORT_VERSION = "nested-replay-v1"
PREDECLARED_RESEARCH_CONFIGS = [v2.DEFAULT_CHAMPION, *v2.CHALLENGERS]
ROUND_FIELDS = [
    "round", "draw_date", "training_rows", "selected_research_model", "selection_score",
    "champion_tickets", "research_tickets",
    "champion_max_hits", "research_max_hits", "random_mean_max_hits",
    "champion_mean_hits", "research_mean_hits", "random_mean_ticket_hits",
    "champion_ge3", "research_ge3", "random_ge3_rate",
    "champion_ge4", "research_ge4", "random_ge4_rate",
    "champion_score", "research_score", "random_mean_score",
    "research_delta_vs_champion", "research_delta_vs_random",
]


def write_csv(path: Path, rows: Sequence[Dict[str, object]], fields: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(fields))
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fields})


def write_json(path: Path, obj: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def ticket_text(tickets: Sequence[Sequence[int]]) -> str:
    return " | ".join(" ".join(f"{int(n):02d}" for n in ticket) for ticket in tickets)


def simulate_config(x: np.ndarray, config: v2.ModelConfig, min_train: int, pool_size: int) -> Dict[int, Dict[str, object]]:
    """Generate every ticket before reading that target row's result, then score it."""
    keys = list(expert_probabilities(x[:min_train]).keys())
    logw = np.zeros(len(keys), dtype=float)
    out: Dict[int, Dict[str, object]] = {}
    seed_offset = int(config.version().split("-")[-1][:6], 16) % 100000
    for t in range(min_train, len(x)):
        q = v2._score_distribution(x[:t], keys, logw, config)
        tickets = make_ticket_portfolio(
            q,
            n_tickets=5,
            seed=2_000_000 + t * 1000 + seed_offset,
            pool_size=pool_size,
            overlap_penalty=config.overlap_penalty,
        )
        actual_set = set((np.flatnonzero(x[t]) + 1).tolist())
        metrics = v2._portfolio_metrics(tickets, actual_set)
        out[t] = {
            "tickets": [tuple(int(n) for n in ticket) for ticket in tickets],
            "metrics": metrics,
            "score": v3.row_score(metrics),
        }
        logw = v2._update_log_weights(x[:t], np.flatnonzero(x[t]), keys, logw, config)
    return out


def composite_past_score(records: Dict[int, Dict[str, object]], t: int, min_train: int) -> float:
    """Research selection score from rows strictly before t."""
    total = 0.0
    used = 0.0
    for window, weight in ((30, 0.2), (60, 0.5), (120, 1.0)):
        start = max(min_train, t - window)
        vals = [float(records[i]["score"]) for i in range(start, t) if i in records]
        if vals:
            total += weight * float(np.mean(vals))
            used += weight
    return total / used if used else -1e9


def select_research_model(
    simulations: Dict[str, Dict[int, Dict[str, object]]],
    configs: Sequence[v2.ModelConfig],
    t: int,
    min_train: int,
) -> Tuple[v2.ModelConfig, float]:
    ranked = []
    for cfg in configs:
        score = composite_past_score(simulations[cfg.version()], t, min_train)
        ranked.append((score, cfg.version(), cfg))
    ranked.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return ranked[0][2], float(ranked[0][0])


def random_reference(actual_set: set[int], t: int, reps: int) -> Dict[str, float]:
    rows = []
    for rep in range(max(1, reps)):
        rng = np.random.default_rng(9_000_000 + t * 1009 + rep)
        rows.append(v2._portfolio_metrics(v2._random_portfolio(rng), actual_set))
    return {
        "max_hits": float(np.mean([r["max_hits"] for r in rows])),
        "mean_hits": float(np.mean([r["mean_hits"] for r in rows])),
        "ge3": float(np.mean([r["ge3"] for r in rows])),
        "ge4": float(np.mean([r["ge4"] for r in rows])),
        "score": float(np.mean([v3.row_score(r) for r in rows])),
    }


def bootstrap_mean_ci(values: Sequence[float], seed: int = 12345, reps: int = 5000) -> Dict[str, float]:
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


def aggregate_metric(rows: Sequence[Dict[str, object]], prefix: str, key: str) -> float:
    vals = [float(r[f"{prefix}_{key}"]) for r in rows]
    return float(np.mean(vals)) if vals else 0.0


def summarize(rows: Sequence[Dict[str, object]], csv_sha: str, source_rows: int, min_train: int,
              last_n: int, pool_size: int, random_reps: int) -> Dict[str, object]:
    selected = Counter(str(r["selected_research_model"]) for r in rows)
    delta_champ = [float(r["research_delta_vs_champion"]) for r in rows]
    delta_random = [float(r["research_delta_vs_random"]) for r in rows]
    return {
        "report_version": REPORT_VERSION,
        "evaluation_type": "nested_walk_forward_predeclared_model_family",
        "leakage_control": (
            "All four candidate model configurations were predeclared before v4 research. "
            "At target row t, model selection uses only scored predictions from rows < t; "
            "the target result is excluded from selection."
        ),
        "csv_sha256": csv_sha,
        "source_rows": source_rows,
        "min_train": min_train,
        "last_n": last_n,
        "portfolio_pool_size": pool_size,
        "random_portfolios_per_round": random_reps,
        "evaluated_rounds": len(rows),
        "first_round": rows[0]["round"] if rows else None,
        "last_round": rows[-1]["round"] if rows else None,
        "predeclared_models": [cfg.version() for cfg in PREDECLARED_RESEARCH_CONFIGS],
        "selected_model_counts": dict(selected),
        "champion_reference": {
            "model": v2.DEFAULT_CHAMPION.version(),
            "mean_max_hits": aggregate_metric(rows, "champion", "max_hits"),
            "mean_ticket_hits": aggregate_metric(rows, "champion", "mean_hits"),
            "ge3_round_rate": aggregate_metric(rows, "champion", "ge3"),
            "ge4_round_rate": aggregate_metric(rows, "champion", "ge4"),
            "mean_score": aggregate_metric(rows, "champion", "score"),
        },
        "nested_research": {
            "mean_max_hits": aggregate_metric(rows, "research", "max_hits"),
            "mean_ticket_hits": aggregate_metric(rows, "research", "mean_hits"),
            "ge3_round_rate": aggregate_metric(rows, "research", "ge3"),
            "ge4_round_rate": aggregate_metric(rows, "research", "ge4"),
            "mean_score": aggregate_metric(rows, "research", "score"),
            "score_delta_vs_champion": bootstrap_mean_ci(delta_champ, seed=12001),
            "score_delta_vs_random": bootstrap_mean_ci(delta_random, seed=12002),
            "round_win_rate_vs_champion": float(np.mean([d > 0 for d in delta_champ])) if delta_champ else 0.0,
            "round_win_rate_vs_random": float(np.mean([d > 0 for d in delta_random])) if delta_random else 0.0,
        },
        "random_reference": {
            "mean_max_hits": aggregate_metric(rows, "random", "mean_max_hits"),
            "mean_ticket_hits": aggregate_metric(rows, "random", "mean_ticket_hits"),
            "ge3_round_rate": aggregate_metric(rows, "random", "ge3_rate"),
            "ge4_round_rate": aggregate_metric(rows, "random", "ge4_rate"),
            "mean_score": aggregate_metric(rows, "random", "mean_score"),
        },
        "interpretation": (
            "This is diagnostic nested backtesting. It is stronger than retrospectively testing the current Research Winner, "
            "but it remains historical evidence and never contributes to v4 future-OOS Champion promotion."
        ),
    }


def render_report(summary: Dict[str, object]) -> str:
    c = summary["champion_reference"]
    r = summary["nested_research"]
    rnd = summary["random_reference"]
    dc = r["score_delta_vs_champion"]
    dr = r["score_delta_vs_random"]
    selections = " / ".join(f"{k}: {v}" for k, v in sorted(summary["selected_model_counts"].items()))
    return "\n".join([
        "# LOTO7 Nested Walk-Forward Comparison",
        "",
        f"- 評価回数: **{summary['evaluated_rounds']}回** ({summary['first_round']}〜{summary['last_round']})",
        "- Research選択: **対象回より前の予測成績だけで選択**",
        "- 現在のResearch Winnerを過去へ後付け: **していない**",
        f"- 事前定義モデル: **{len(summary['predeclared_models'])}個**",
        "",
        "| 指標 | Champion reference | Nested Research | Random reference |",
        "|---|---:|---:|---:|",
        f"| 平均最大一致 | {c['mean_max_hits']:.4f} | {r['mean_max_hits']:.4f} | {rnd['mean_max_hits']:.4f} |",
        f"| 1口平均一致 | {c['mean_ticket_hits']:.4f} | {r['mean_ticket_hits']:.4f} | {rnd['mean_ticket_hits']:.4f} |",
        f"| 3個以上一致回率 | {c['ge3_round_rate']*100:.2f}% | {r['ge3_round_rate']*100:.2f}% | {rnd['ge3_round_rate']*100:.2f}% |",
        f"| 4個以上一致回率 | {c['ge4_round_rate']*100:.2f}% | {r['ge4_round_rate']*100:.2f}% | {rnd['ge4_round_rate']*100:.2f}% |",
        f"| 平均score | {c['mean_score']:.4f} | {r['mean_score']:.4f} | {rnd['mean_score']:.4f} |",
        "",
        f"- Research score差 vs Champion: **{dc['mean']:+.4f}** (bootstrap 95% CI {dc['low95']:+.4f}〜{dc['high95']:+.4f})",
        f"- Research score差 vs Random: **{dr['mean']:+.4f}** (bootstrap 95% CI {dr['low95']:+.4f}〜{dr['high95']:+.4f})",
        f"- Research勝率 vs Champion: **{r['round_win_rate_vs_champion']*100:.1f}%**",
        f"- Research勝率 vs Random: **{r['round_win_rate_vs_random']*100:.1f}%**",
        f"- 選択モデル回数: {selections or 'なし'}",
        "",
        "> nested replayは過去診断専用です。Production昇格は引き続き事前凍結した未来OOSだけで判定します。",
        "",
    ])


def is_fresh(path: Path, csv_sha: str, last_n: int, min_train: int, pool_size: int, random_reps: int) -> bool:
    if not path.exists():
        return False
    try:
        old = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return False
    return bool(
        old.get("report_version") == REPORT_VERSION
        and old.get("csv_sha256") == csv_sha
        and int(old.get("last_n", -1)) == last_n
        and int(old.get("min_train", -1)) == min_train
        and int(old.get("portfolio_pool_size", -1)) == pool_size
        and int(old.get("random_portfolios_per_round", -1)) == random_reps
    )


def run(args) -> Dict[str, object]:
    df = read_csv_flexible(args.csv)
    x, clean = make_history(df)
    if len(x) <= args.min_train + 30:
        raise SystemExit("not enough history for nested replay")
    csv_sha = fingerprint_file(args.csv)
    summary_path = args.out_dir / "nested_replay_summary.json"
    if args.if_stale and is_fresh(summary_path, csv_sha, args.last_n, args.min_train, args.pool_size, args.random_reps):
        print("[NESTED] report is fresh; skipped")
        return json.loads(summary_path.read_text(encoding="utf-8"))

    configs = PREDECLARED_RESEARCH_CONFIGS
    simulations = {
        cfg.version(): simulate_config(x, cfg, args.min_train, args.pool_size)
        for cfg in configs
    }
    eval_start = max(args.min_train + 30, len(x) - args.last_n) if args.last_n > 0 else args.min_train + 30
    rows: List[Dict[str, object]] = []
    champion_version = v2.DEFAULT_CHAMPION.version()
    for t in range(eval_start, len(x)):
        selected, selection_score = select_research_model(simulations, configs, t, args.min_train)
        champ = simulations[champion_version][t]
        research = simulations[selected.version()][t]
        actual_set = set((np.flatnonzero(x[t]) + 1).tolist())
        rnd = random_reference(actual_set, t, args.random_reps)
        cm = champ["metrics"]
        rm = research["metrics"]
        round_text = str(clean["回別"].iloc[t]) if "回別" in clean.columns else str(t + 1)
        digits = "".join(ch for ch in round_text if ch.isdigit())
        round_no = int(digits) if digits else t + 1
        draw_date = clean["抽せん日"].iloc[t].date().isoformat()
        cscore = float(champ["score"])
        rscore = float(research["score"])
        rows.append({
            "round": round_no,
            "draw_date": draw_date,
            "training_rows": t,
            "selected_research_model": selected.version(),
            "selection_score": f"{selection_score:.6f}",
            "champion_tickets": ticket_text(champ["tickets"]),
            "research_tickets": ticket_text(research["tickets"]),
            "champion_max_hits": f"{cm['max_hits']:.0f}",
            "research_max_hits": f"{rm['max_hits']:.0f}",
            "random_mean_max_hits": f"{rnd['max_hits']:.6f}",
            "champion_mean_hits": f"{cm['mean_hits']:.6f}",
            "research_mean_hits": f"{rm['mean_hits']:.6f}",
            "random_mean_ticket_hits": f"{rnd['mean_hits']:.6f}",
            "champion_ge3": int(cm["ge3"]),
            "research_ge3": int(rm["ge3"]),
            "random_ge3_rate": f"{rnd['ge3']:.6f}",
            "champion_ge4": int(cm["ge4"]),
            "research_ge4": int(rm["ge4"]),
            "random_ge4_rate": f"{rnd['ge4']:.6f}",
            "champion_score": f"{cscore:.6f}",
            "research_score": f"{rscore:.6f}",
            "random_mean_score": f"{rnd['score']:.6f}",
            "research_delta_vs_champion": f"{rscore-cscore:.6f}",
            "research_delta_vs_random": f"{rscore-rnd['score']:.6f}",
        })

    summary = summarize(rows, csv_sha, len(x), args.min_train, args.last_n, args.pool_size, args.random_reps)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.out_dir / "nested_replay_rounds.csv", rows, ROUND_FIELDS)
    write_json(summary_path, summary)
    (args.out_dir / "nested_replay_report.md").write_text(render_report(summary), encoding="utf-8")
    print(f"[NESTED] rounds={summary['evaluated_rounds']} research-vs-champion={summary['nested_research']['score_delta_vs_champion']['mean']:+.4f}")
    print(f"[NESTED] research-vs-random={summary['nested_research']['score_delta_vs_random']['mean']:+.4f}")
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description="Leakage-safe nested walk-forward comparison for LOTO7")
    ap.add_argument("--csv", type=Path, default=Path("loto7.csv"))
    ap.add_argument("--out-dir", type=Path, default=Path("loto7_agent_output"))
    ap.add_argument("--min-train", type=int, default=100)
    ap.add_argument("--last-n", type=int, default=120)
    ap.add_argument("--pool-size", type=int, default=350)
    ap.add_argument("--random-reps", type=int, default=32)
    ap.add_argument("--if-stale", action="store_true")
    args = ap.parse_args()
    if args.last_n < 0 or args.pool_size < 100 or args.random_reps < 1:
        raise SystemExit("invalid nested replay parameters")
    run(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
