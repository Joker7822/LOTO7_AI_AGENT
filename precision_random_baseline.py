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
import loto7_v3_runner as v3
from loto7_evolving_agent import fingerprint_file, make_history, read_csv_flexible

REPORT_VERSION = "precision-random-baseline-v2-symmetric"
FIELDS = [
    "round_index", "random_reps", "mean_max_hits", "mean_ticket_hits",
    "ge3_rate", "ge4_rate", "mean_score", "score_se",
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


def random_round(actual_set: set[int], t: int, reps: int) -> Dict[str, float]:
    max_hits = np.empty(reps, dtype=float)
    mean_hits = np.empty(reps, dtype=float)
    ge3 = np.empty(reps, dtype=float)
    ge4 = np.empty(reps, dtype=float)
    scores = np.empty(reps, dtype=float)
    for rep in range(reps):
        rng = np.random.default_rng(41_000_000 + t * 100_003 + rep)
        m = v2._portfolio_metrics(v2._random_portfolio(rng), actual_set)
        max_hits[rep] = float(m["max_hits"])
        mean_hits[rep] = float(m["mean_hits"])
        ge3[rep] = float(m["ge3"])
        ge4[rep] = float(m["ge4"])
        scores[rep] = float(v3.row_score(m))
    return {
        "mean_max_hits": float(np.mean(max_hits)),
        "mean_ticket_hits": float(np.mean(mean_hits)),
        "ge3_rate": float(np.mean(ge3)),
        "ge4_rate": float(np.mean(ge4)),
        "mean_score": float(np.mean(scores)),
        "score_se": float(np.std(scores, ddof=1) / np.sqrt(reps)) if reps > 1 else 0.0,
    }


def aggregate(rows: Sequence[Dict[str, object]]) -> Dict[str, float]:
    if not rows:
        return {
            "random_max_hits": 0.0, "random_mean_hits": 0.0,
            "random_ge3": 0.0, "random_ge4": 0.0,
            "random_score": 0.0, "mean_round_score_se": 0.0,
        }
    return {
        "random_max_hits": float(np.mean([float(r["mean_max_hits"]) for r in rows])),
        "random_mean_hits": float(np.mean([float(r["mean_ticket_hits"]) for r in rows])),
        "random_ge3": float(np.mean([float(r["ge3_rate"]) for r in rows])),
        "random_ge4": float(np.mean([float(r["ge4_rate"]) for r in rows])),
        "random_score": float(np.mean([float(r["mean_score"]) for r in rows])),
        "mean_round_score_se": float(np.mean([float(r["score_se"]) for r in rows])),
    }


def build(csv_path: Path, min_train: int, reps: int) -> tuple[Dict[str, object], List[Dict[str, object]]]:
    df = read_csv_flexible(csv_path)
    x, _ = make_history(df)

    # Under a uniformly random 7-of-37 draw and uniformly random five-ticket portfolio,
    # the metric distribution is invariant to the labels of the seven actual numbers.
    # Therefore one high-precision Monte Carlo sample against {1..7} is statistically
    # identical to resampling separately for every historical draw, without multiplying
    # runtime by the number of rounds.
    shared = random_round(set(range(1, 8)), t=0, reps=reps)
    rows: List[Dict[str, object]] = [
        {"round_index": t + 1, "random_reps": reps, **shared}
        for t in range(min_train, len(x))
    ]

    windows: Dict[str, Dict[str, float]] = {"full": aggregate(rows)}
    for n in (120, 60, 30):
        windows[str(n)] = aggregate(rows[-min(n, len(rows)):])
    summary: Dict[str, object] = {
        "report_version": REPORT_VERSION,
        "csv_sha256": fingerprint_file(csv_path),
        "min_train": int(min_train),
        "random_portfolios_per_round": int(reps),
        "monte_carlo_portfolios_generated_total": int(reps),
        "symmetry_reused_across_rounds": True,
        "evaluated_rounds": len(rows),
        "first_round": rows[0]["round_index"] if rows else None,
        "last_round": rows[-1]["round_index"] if rows else None,
        "windows": windows,
        "purpose": "shared cached portfolio null reference for Research-only evaluation",
        "symmetry_note": (
            "For random 5-ticket portfolios, relabeling the seven actual numbers leaves the hit/score distribution unchanged; "
            "one Monte Carlo null distribution is therefore reused across historical rounds."
        ),
        "independent_evidence": False,
        "promotion_eligible": False,
    }
    return summary, rows


def is_fresh(path: Path, csv_sha: str, min_train: int, reps: int) -> bool:
    if not path.exists():
        return False
    try:
        old = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return False
    return bool(
        old.get("report_version") == REPORT_VERSION
        and old.get("csv_sha256") == csv_sha
        and int(old.get("min_train", -1)) == min_train
        and int(old.get("random_portfolios_per_round", -1)) == reps
    )


def ensure(csv_path: Path, out_dir: Path, min_train: int = 100, reps: int = 4096) -> Dict[str, object]:
    summary_path = out_dir / "precision_random_baseline_summary.json"
    csv_sha = fingerprint_file(csv_path)
    if is_fresh(summary_path, csv_sha, min_train, reps):
        return json.loads(summary_path.read_text(encoding="utf-8"))
    summary, rows = build(csv_path, min_train, reps)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(summary_path, summary)
    write_csv(out_dir / "precision_random_baseline.csv", rows)
    report = [
        "# High-Precision Random Portfolio Baseline",
        "",
        f"- evaluated rounds: **{summary['evaluated_rounds']}**",
        f"- Monte Carlo random portfolios: **{reps:,}**",
        "- symmetry reuse across rounds: **YES**",
        "- cache key: **data SHA + min_train + reps**",
        "",
        "| Window | max hits | mean hits | >=3 | >=4 | score |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name in ("full", "120", "60", "30"):
        w = summary["windows"][name]
        report.append(
            f"| {name} | {w['random_max_hits']:.4f} | {w['random_mean_hits']:.4f} | "
            f"{w['random_ge3']*100:.2f}% | {w['random_ge4']*100:.2f}% | {w['random_score']:.4f} |"
        )
    report += [
        "",
        "> 7/37の数字ラベル対称性により、同じNull分布を全履歴回へ再利用しています。",
        "> Research comparison only; this does not create Future OOS evidence.",
        "",
    ]
    (out_dir / "precision_random_baseline_report.md").write_text("\n".join(report), encoding="utf-8")
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description="Build one shared high-precision random portfolio baseline and cache it by data SHA")
    ap.add_argument("--csv", type=Path, default=Path("loto7.csv"))
    ap.add_argument("--out-dir", type=Path, default=Path("loto7_agent_output"))
    ap.add_argument("--min-train", type=int, default=100)
    ap.add_argument("--reps", type=int, default=4096)
    ap.add_argument("--if-stale", action="store_true")
    args = ap.parse_args()
    summary_path = args.out_dir / "precision_random_baseline_summary.json"
    csv_sha = fingerprint_file(args.csv)
    if args.if_stale and is_fresh(summary_path, csv_sha, args.min_train, args.reps):
        print("[PRECISION-RANDOM] fresh; skipped")
        return 0
    summary = ensure(args.csv, args.out_dir, args.min_train, args.reps)
    print(
        f"[PRECISION-RANDOM] rounds={summary['evaluated_rounds']} reps={summary['random_portfolios_per_round']} "
        f"generated_total={summary['monte_carlo_portfolios_generated_total']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
