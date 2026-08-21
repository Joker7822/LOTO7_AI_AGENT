#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import csv
import json
import math
import re
from dataclasses import asdict
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

import numpy as np

import loto7_v2_runner as v2
import loto7_v3_runner as v3
from audit_ledger import grade_ticket
from loto7_evolving_agent import N_NUMBERS, PICKS, RANDOM_HIT_MEAN, expert_probabilities, fingerprint_file, make_history, make_ticket_portfolio, read_csv_flexible

REPORT_VERSION = "historical-replay-v1"
TICKET_FIELDS = [
    "round", "draw_date", "training_rows", "ticket", "predicted_numbers",
    "actual_main_numbers", "actual_bonus_numbers", "main_hits", "bonus_hits",
    "grade", "prize_amount",
]
ROUND_FIELDS = [
    "round", "draw_date", "training_rows", "top7_numbers", "top7_hits",
    "portfolio_max_hits", "portfolio_mean_hits", "portfolio_ge3", "portfolio_ge4",
    "portfolio_score", "random_mean_max_hits", "random_mean_ticket_hits",
    "random_ge3_rate", "random_ge4_rate", "random_mean_score",
    "score_delta_vs_random", "best_grade", "winning_tickets",
]


def fmt_nums(values: Iterable[int]) -> str:
    return " ".join(f"{int(v):02d}" for v in sorted(values))


def parse_nums(value: object) -> Tuple[int, ...]:
    return tuple(int(x) for x in re.findall(r"\d+", str(value or "")))


def parse_round(value: object, fallback: int) -> int:
    m = re.search(r"\d+", str(value or ""))
    return int(m.group()) if m else int(fallback)


def read_json(path: Path) -> Dict[str, object]:
    if not path.exists():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def write_json(path: Path, obj: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv(path: Path, rows: Sequence[Dict[str, object]], fields: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(fields))
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})


def parse_prize(row, grade: str) -> str:
    if grade == "はずれ":
        return "0円"
    key = f"{grade}当選金額"
    value = str(row.get(key, "") or "").strip()
    return value or "確認できません"


def grade_rank(grade: str) -> int:
    if grade == "はずれ":
        return 99
    m = re.match(r"(\d+)等", grade)
    return int(m.group(1)) if m else 98


def forecast_portfolio(hist: np.ndarray, config: v2.ModelConfig, keys: List[str], logw: np.ndarray,
                       target_round: int, pool_size: int) -> Tuple[np.ndarray, List[Tuple[int, ...]]]:
    """Forecast using only the supplied history. No target-row information is accepted."""
    q = v2._score_distribution(hist, keys, logw, config)
    tickets = make_ticket_portfolio(
        q,
        n_tickets=5,
        seed=int(target_round),
        pool_size=int(pool_size),
        overlap_penalty=config.overlap_penalty,
    )
    return q, tickets


def random_baseline(actual_set: set[int], target_round: int, reps: int) -> Dict[str, float]:
    rows: List[Dict[str, float]] = []
    for rep in range(max(1, int(reps))):
        rng = np.random.default_rng(8_000_000 + int(target_round) * 1009 + rep)
        rows.append(v2._portfolio_metrics(v2._random_portfolio(rng), actual_set))
    return {
        "max_hits": float(np.mean([r["max_hits"] for r in rows])),
        "mean_hits": float(np.mean([r["mean_hits"] for r in rows])),
        "ge3_rate": float(np.mean([r["ge3"] for r in rows])),
        "ge4_rate": float(np.mean([r["ge4"] for r in rows])),
        "score": float(np.mean([v3.row_score(r) for r in rows])),
    }


def top7_significance(hits: Sequence[int]) -> Tuple[float, float, float]:
    if not hits:
        return 0.0, 0.0, 1.0
    mean_hits = float(np.mean(hits))
    var_single = (
        PICKS
        * (PICKS / N_NUMBERS)
        * (1.0 - PICKS / N_NUMBERS)
        * ((N_NUMBERS - PICKS) / (N_NUMBERS - 1))
    )
    se = math.sqrt(var_single / len(hits))
    z = (mean_hits - RANDOM_HIT_MEAN) / se if se > 0 else 0.0
    p2 = math.erfc(abs(z) / math.sqrt(2.0))
    return mean_hits, float(z), float(p2)


def summary_from_rows(ticket_rows: Sequence[Dict[str, object]], round_rows: Sequence[Dict[str, object]],
                      config: v2.ModelConfig, csv_sha: str, min_train: int, pool_size: int,
                      random_reps: int, total_rows: int) -> Dict[str, object]:
    top_hits = [int(r["top7_hits"]) for r in round_rows]
    mean_top7, z_top7, p_top7 = top7_significance(top_hits)
    scores = [float(r["portfolio_score"]) for r in round_rows]
    random_scores = [float(r["random_mean_score"]) for r in round_rows]
    deltas = [a - b for a, b in zip(scores, random_scores)]
    max_hits = [float(r["portfolio_max_hits"]) for r in round_rows]
    rnd_max = [float(r["random_mean_max_hits"]) for r in round_rows]
    ge3 = [int(r["portfolio_ge3"]) for r in round_rows]
    ge4 = [int(r["portfolio_ge4"]) for r in round_rows]
    random_ge3 = [float(r["random_ge3_rate"]) for r in round_rows]
    random_ge4 = [float(r["random_ge4_rate"]) for r in round_rows]
    grade_counts: Dict[str, int] = {}
    for row in ticket_rows:
        g = str(row.get("grade", "はずれ"))
        grade_counts[g] = grade_counts.get(g, 0) + 1
    wins = sum(v for k, v in grade_counts.items() if k != "はずれ")
    rounds_with_prize = sum(1 for r in round_rows if int(r.get("winning_tickets", 0)) > 0)
    return {
        "report_version": REPORT_VERSION,
        "evaluation_type": "strict_walk_forward_fixed_baseline",
        "leakage_control": "For target row t, model scoring and ticket generation use only rows [0,t). The target result is read only after tickets are frozen.",
        "model_version": config.version(),
        "model_config": asdict(config),
        "csv_sha256": csv_sha,
        "source_rows": int(total_rows),
        "min_train": int(min_train),
        "portfolio_pool_size": int(pool_size),
        "random_portfolios_per_round": int(random_reps),
        "evaluated_rounds": len(round_rows),
        "evaluated_tickets": len(ticket_rows),
        "first_evaluated_round": round_rows[0]["round"] if round_rows else None,
        "last_evaluated_round": round_rows[-1]["round"] if round_rows else None,
        "top7": {
            "mean_hits": mean_top7,
            "random_theoretical_mean_hits": RANDOM_HIT_MEAN,
            "delta_vs_random": mean_top7 - RANDOM_HIT_MEAN,
            "z_vs_random": z_top7,
            "approx_two_sided_p": p_top7,
            "signal_claim": "not_confirmed" if p_top7 >= 0.05 else "requires_independent_validation",
        },
        "portfolio_5_tickets": {
            "mean_max_hits": float(np.mean(max_hits)) if max_hits else 0.0,
            "random_mean_max_hits": float(np.mean(rnd_max)) if rnd_max else 0.0,
            "mean_score": float(np.mean(scores)) if scores else 0.0,
            "random_mean_score": float(np.mean(random_scores)) if random_scores else 0.0,
            "mean_score_delta_vs_random": float(np.mean(deltas)) if deltas else 0.0,
            "rounds_beating_random_rate": float(np.mean([d > 0 for d in deltas])) if deltas else 0.0,
            "ge3_round_rate": float(np.mean(ge3)) if ge3 else 0.0,
            "random_ge3_round_rate": float(np.mean(random_ge3)) if random_ge3 else 0.0,
            "ge4_round_rate": float(np.mean(ge4)) if ge4 else 0.0,
            "random_ge4_round_rate": float(np.mean(random_ge4)) if random_ge4 else 0.0,
        },
        "prize_grades": {
            "grade_counts": grade_counts,
            "winning_tickets": wins,
            "winning_ticket_rate": wins / max(1, len(ticket_rows)),
            "rounds_with_any_prize": rounds_with_prize,
            "rounds_with_any_prize_rate": rounds_with_prize / max(1, len(round_rows)),
        },
        "interpretation": "Historical replay is a baseline/reference backtest, not future OOS evidence for v4 Champion promotion.",
    }


def render_report(summary: Dict[str, object]) -> str:
    top = summary["top7"]
    pf = summary["portfolio_5_tickets"]
    prizes = summary["prize_grades"]
    grades = prizes.get("grade_counts", {})
    grade_text = " / ".join(f"{k}: {v}" for k, v in sorted(grades.items(), key=lambda kv: grade_rank(kv[0])))
    return "\n".join([
        "# LOTO7 Historical Replay Accuracy",
        "",
        f"- 評価方式: **{summary['evaluation_type']}**",
        f"- モデル: **{summary['model_version']}**",
        f"- 評価回数: **{summary['evaluated_rounds']}回** ({summary['first_evaluated_round']}〜{summary['last_evaluated_round']})",
        f"- 評価口数: **{summary['evaluated_tickets']}口**",
        f"- 学習開始最低履歴: **{summary['min_train']}回**",
        f"- 5口生成pool: **{summary['portfolio_pool_size']}**",
        "- 未来参照: **なし（各対象回より前のデータだけで予測）**",
        "",
        "## Top7 accuracy",
        "",
        f"- 平均本数字一致: **{top['mean_hits']:.4f}**",
        f"- ランダム理論平均: **{top['random_theoretical_mean_hits']:.4f}**",
        f"- 差: **{top['delta_vs_random']:+.4f}**",
        f"- z: **{top['z_vs_random']:.4f}**",
        f"- 近似両側p: **{top['approx_two_sided_p']:.6f}**",
        f"- 判定: **{top['signal_claim']}**",
        "",
        "## 5-ticket portfolio",
        "",
        f"- 5口中の平均最大一致数: **{pf['mean_max_hits']:.4f}** / random **{pf['random_mean_max_hits']:.4f}**",
        f"- 平均複合score: **{pf['mean_score']:.4f}** / random **{pf['random_mean_score']:.4f}**",
        f"- 平均score差: **{pf['mean_score_delta_vs_random']:+.4f}**",
        f"- random平均scoreを上回った回: **{pf['rounds_beating_random_rate']*100:.1f}%**",
        f"- 3個以上一致券があった回: **{pf['ge3_round_rate']*100:.1f}%** / random **{pf['random_ge3_round_rate']*100:.1f}%**",
        f"- 4個以上一致券があった回: **{pf['ge4_round_rate']*100:.1f}%** / random **{pf['random_ge4_round_rate']*100:.1f}%**",
        "",
        "## Prize-grade replay",
        "",
        f"- 当選口数: **{prizes['winning_tickets']} / {summary['evaluated_tickets']}** ({prizes['winning_ticket_rate']*100:.3f}%)",
        f"- 当選が1口以上あった回: **{prizes['rounds_with_any_prize']} / {summary['evaluated_rounds']}** ({prizes['rounds_with_any_prize_rate']*100:.2f}%)",
        f"- 等級内訳: {grade_text or 'なし'}",
        "",
        "> この結果は過去回を順番に再生したbaseline/reference評価です。v4 Production Championの昇格に使う未来OOS証拠とは別管理です。",
        "",
    ])


def is_fresh(summary_path: Path, csv_sha: str, config: v2.ModelConfig, min_train: int,
             pool_size: int, random_reps: int, last_n: int) -> bool:
    old = read_json(summary_path)
    return bool(
        old.get("report_version") == REPORT_VERSION
        and old.get("csv_sha256") == csv_sha
        and old.get("model_version") == config.version()
        and int(old.get("min_train", -1)) == int(min_train)
        and int(old.get("portfolio_pool_size", -1)) == int(pool_size)
        and int(old.get("random_portfolios_per_round", -1)) == int(random_reps)
        and int(old.get("last_n", 0)) == int(last_n)
    )


def run(args) -> Dict[str, object]:
    df = read_csv_flexible(args.csv)
    x, clean = make_history(df)
    if len(x) <= args.min_train:
        raise SystemExit(f"not enough rows: {len(x)} <= min_train {args.min_train}")
    config = v2.DEFAULT_CHAMPION
    csv_sha = fingerprint_file(args.csv)
    summary_path = args.out_dir / "historical_replay_summary.json"
    if args.if_stale and is_fresh(summary_path, csv_sha, config, args.min_train, args.pool_size, args.random_reps, args.last_n):
        print("[HISTORICAL] report is fresh; skipped")
        return read_json(summary_path)

    keys = list(expert_probabilities(x[:args.min_train]).keys())
    logw = np.zeros(len(keys), dtype=float)
    eval_start = args.min_train
    if args.last_n > 0:
        eval_start = max(eval_start, len(x) - args.last_n)

    ticket_rows: List[Dict[str, object]] = []
    round_rows: List[Dict[str, object]] = []
    for t in range(args.min_train, len(x)):
        if t >= eval_start:
            row = clean.iloc[t]
            target_round = parse_round(row.get("回別", ""), t + 1)
            draw_date = row["抽せん日"].date().isoformat() if hasattr(row["抽せん日"], "date") else str(row["抽せん日"])
            q, tickets = forecast_portfolio(x[:t], config, keys, logw, target_round, args.pool_size)
            actual_main = tuple(int(n) for n in (np.flatnonzero(x[t]) + 1).tolist())
            actual_set = set(actual_main)
            actual_bonus = parse_nums(row.get("ボーナス数字", ""))[:2]
            top7 = tuple(int(n) for n in (np.argsort(q)[::-1][:7] + 1).tolist())
            top7_hits = len(set(top7) & actual_set)
            model_m = v2._portfolio_metrics(tickets, actual_set)
            model_score = v3.row_score(model_m)
            rnd = random_baseline(actual_set, target_round, args.random_reps)
            grades: List[str] = []
            for ticket_no, ticket in enumerate(tickets, 1):
                mh, bh, grade = grade_ticket(tuple(ticket), actual_main, actual_bonus)
                grades.append(grade)
                ticket_rows.append({
                    "round": target_round,
                    "draw_date": draw_date,
                    "training_rows": t,
                    "ticket": ticket_no,
                    "predicted_numbers": fmt_nums(ticket),
                    "actual_main_numbers": fmt_nums(actual_main),
                    "actual_bonus_numbers": fmt_nums(actual_bonus),
                    "main_hits": mh,
                    "bonus_hits": bh,
                    "grade": grade,
                    "prize_amount": parse_prize(row, grade),
                })
            best_grade = min(grades, key=grade_rank) if grades else "はずれ"
            round_rows.append({
                "round": target_round,
                "draw_date": draw_date,
                "training_rows": t,
                "top7_numbers": fmt_nums(top7),
                "top7_hits": top7_hits,
                "portfolio_max_hits": f"{model_m['max_hits']:.0f}",
                "portfolio_mean_hits": f"{model_m['mean_hits']:.6f}",
                "portfolio_ge3": int(model_m["ge3"]),
                "portfolio_ge4": int(model_m["ge4"]),
                "portfolio_score": f"{model_score:.6f}",
                "random_mean_max_hits": f"{rnd['max_hits']:.6f}",
                "random_mean_ticket_hits": f"{rnd['mean_hits']:.6f}",
                "random_ge3_rate": f"{rnd['ge3_rate']:.6f}",
                "random_ge4_rate": f"{rnd['ge4_rate']:.6f}",
                "random_mean_score": f"{rnd['score']:.6f}",
                "score_delta_vs_random": f"{model_score-rnd['score']:.6f}",
                "best_grade": best_grade,
                "winning_tickets": sum(1 for g in grades if g != "はずれ"),
            })
        actual_idx = np.flatnonzero(x[t])
        logw = v2._update_log_weights(x[:t], actual_idx, keys, logw, config)

    summary = summary_from_rows(
        ticket_rows, round_rows, config, csv_sha, args.min_train,
        args.pool_size, args.random_reps, len(x),
    )
    summary["last_n"] = int(args.last_n)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.out_dir / "historical_round_predictions.csv", ticket_rows, TICKET_FIELDS)
    write_csv(args.out_dir / "historical_round_accuracy.csv", round_rows, ROUND_FIELDS)
    write_json(summary_path, summary)
    (args.out_dir / "historical_accuracy_report.md").write_text(render_report(summary), encoding="utf-8")
    print(f"[HISTORICAL] rounds={summary['evaluated_rounds']} tickets={summary['evaluated_tickets']}")
    print(f"[TOP7] mean={summary['top7']['mean_hits']:.4f} random={RANDOM_HIT_MEAN:.4f} p={summary['top7']['approx_two_sided_p']:.6f}")
    print(f"[PORTFOLIO] score={summary['portfolio_5_tickets']['mean_score']:.4f} random={summary['portfolio_5_tickets']['random_mean_score']:.4f}")
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description="Leakage-safe round-by-round historical replay for LOTO7")
    ap.add_argument("--csv", type=Path, default=Path("loto7.csv"))
    ap.add_argument("--out-dir", type=Path, default=Path("loto7_agent_output"))
    ap.add_argument("--min-train", type=int, default=100)
    ap.add_argument("--pool-size", type=int, default=650)
    ap.add_argument("--random-reps", type=int, default=32)
    ap.add_argument("--last-n", type=int, default=0, help="0 evaluates every eligible historical round")
    ap.add_argument("--if-stale", action="store_true")
    args = ap.parse_args()
    if args.pool_size < 100:
        raise SystemExit("--pool-size must be >= 100")
    if args.random_reps < 1:
        raise SystemExit("--random-reps must be >= 1")
    if args.last_n < 0:
        raise SystemExit("--last-n must be >= 0")
    run(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
