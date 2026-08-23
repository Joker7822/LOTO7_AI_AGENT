#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

import loto7_v2_runner as v2
import loto7_v3_runner as v3
from audit_ledger import grade_ticket
from historical_reconcile import (
    PURCHASE_COST_YEN,
    fmt_nums,
    index_actuals,
    parse_money_yen,
    parse_nums,
    parse_round,
    published_prize,
    read_csv,
)
from loto7_evolving_agent import (
    expert_probabilities,
    fingerprint_file,
    make_history,
    make_ticket_portfolio,
    read_csv_flexible,
)

REPORT_VERSION = "model-history-reconcile-v1"
JST = timezone(timedelta(hours=9))


def now_jst() -> str:
    return datetime.now(JST).isoformat(timespec="seconds")


def load_json(path: Path, default: Dict[str, object]) -> Dict[str, object]:
    if not path.exists():
        return dict(default)
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else dict(default)
    except Exception:
        return dict(default)


def write_json(path: Path, obj: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def cfg_from_obj(obj: object) -> Optional[v2.ModelConfig]:
    if not isinstance(obj, dict):
        return None
    try:
        return v2.ModelConfig(
            name=str(obj["name"]),
            eta=float(obj["eta"]),
            decay=float(obj["decay"]),
            expert_uniform_mix=float(obj["expert_uniform_mix"]),
            final_uniform_mix=float(obj["final_uniform_mix"]),
            overlap_penalty=float(obj["overlap_penalty"]),
        )
    except Exception:
        return None


def accepted_model(feedback_state: Dict[str, object], research_state: Dict[str, object]) -> v2.ModelConfig:
    cfg = cfg_from_obj(feedback_state.get("accepted_parent_config"))
    if cfg is None:
        cfg = cfg_from_obj(research_state.get("research_parent_config"))
    if cfg is None:
        raise RuntimeError("accepted Research Parent config is unavailable")
    return cfg


def report_key(data_sha: str, cfg: v2.ModelConfig, min_train: int, pool_size: int) -> str:
    raw = f"{REPORT_VERSION}|{data_sha}|{cfg.version()}|{min_train}|{pool_size}"
    return hashlib.sha256(raw.encode()).hexdigest()


def is_fresh(state: Dict[str, object], key: str) -> bool:
    return state.get("report_version") == REPORT_VERSION and state.get("report_key") == key


def safe_filename(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._") or "model"


def update_run_events(path: Path, model_version: str) -> None:
    obj = load_json(path, {})
    obj["model_history_reconciled"] = True
    obj["model_history_reconciled_version"] = model_version
    obj["force_checkpoint"] = True
    write_json(path, obj)


def replay_and_reconcile(
    csv_path: Path,
    cfg: v2.ModelConfig,
    min_train: int,
    pool_size: int,
) -> Tuple[Dict[str, object], List[Dict[str, object]]]:
    df = read_csv_flexible(csv_path)
    x, clean = make_history(df)
    loto_rows = read_csv(csv_path)
    by_round, previous = index_actuals(loto_rows)

    if len(x) <= min_train:
        raise RuntimeError(f"not enough rows: {len(x)} <= min_train {min_train}")

    keys = list(expert_probabilities(x[:min_train]).keys())
    logw = np.zeros(len(keys), dtype=float)
    seed_offset = int(hashlib.sha256(cfg.version().encode()).hexdigest()[:8], 16) % 100000

    round_rows: List[Dict[str, object]] = []
    grade_counts: Dict[str, int] = {}
    total_payout = 0
    unknown_payouts = 0
    winning_tickets = 0
    round_scores: List[float] = []
    round_max_hits: List[float] = []
    ge3_rounds = 0
    ge4_rounds = 0
    top7_hits: List[int] = []

    for t in range(min_train, len(x)):
        q = v2._score_distribution(x[:t], keys, logw, cfg)
        tickets = make_ticket_portfolio(
            q,
            n_tickets=5,
            seed=6_000_000 + t * 1000 + seed_offset,
            pool_size=pool_size,
            overlap_penalty=cfg.overlap_penalty,
        )

        round_value = clean["回別"].iloc[t] if "回別" in clean.columns else t + 1
        target_round = parse_round(round_value) or (t + 1)
        actual_row = by_round.get(target_round)
        if actual_row is None:
            raise RuntimeError(f"actual result missing for round {target_round}")

        main = tuple(sorted(parse_nums(actual_row.get("本数字", ""))))
        bonus = tuple(sorted(parse_nums(actual_row.get("ボーナス数字", ""))))
        x_main = tuple(sorted((np.flatnonzero(x[t]) + 1).tolist()))
        if len(main) != 7 or len(bonus) != 2 or main != x_main:
            raise RuntimeError(
                f"replay/actual mismatch at round {target_round}: history={x_main} csv={main} bonus={bonus}"
            )

        actual_set = set(main)
        metrics = v2._portfolio_metrics(tickets, actual_set)
        score = float(v3.row_score(metrics))
        round_scores.append(score)
        round_max_hits.append(float(metrics["max_hits"]))
        ge3_rounds += int(float(metrics["ge3"]) > 0)
        ge4_rounds += int(float(metrics["ge4"]) > 0)

        top7 = tuple(int(n) for n in (np.argsort(q)[-7:][::-1] + 1))
        top7_hit = len(set(top7) & actual_set)
        top7_hits.append(top7_hit)

        ticket_rows: List[Dict[str, object]] = []
        for idx, ticket in enumerate(tickets, 1):
            pred = tuple(sorted(int(n) for n in ticket))
            main_hits, bonus_hits, grade = grade_ticket(pred, main, bonus)
            prize_text = published_prize(actual_row, grade)
            prize_yen = parse_money_yen(prize_text)
            if grade == "はずれ":
                prize_yen = 0
            if prize_yen is None:
                unknown_payouts += 1
            else:
                total_payout += int(prize_yen)
            grade_counts[grade] = grade_counts.get(grade, 0) + 1
            winning_tickets += int(grade != "はずれ")
            ticket_rows.append({
                "ticket": idx,
                "predicted_numbers": fmt_nums(pred),
                "main_hits": int(main_hits),
                "bonus_hits": int(bonus_hits),
                "grade": grade,
                "published_prize_amount": prize_text,
                "published_prize_yen": prize_yen,
            })

        prev = previous.get(target_round, {})
        round_rows.append({
            "base_round": parse_round(prev.get("回別", "")) or target_round - 1,
            "target_round": target_round,
            "draw_date": actual_row.get("抽せん日", ""),
            "training_rows": t,
            "top7": fmt_nums(top7),
            "top7_hits": top7_hit,
            "actual_main": fmt_nums(main),
            "actual_bonus": fmt_nums(bonus),
            "portfolio_score": score,
            "portfolio_max_hits": float(metrics["max_hits"]),
            "tickets": ticket_rows,
        })
        logw = v2._update_log_weights(x[:t], np.flatnonzero(x[t]), keys, logw, cfg)

    evaluated_rounds = len(round_rows)
    evaluated_tickets = evaluated_rounds * 5
    purchase_cost = evaluated_tickets * PURCHASE_COST_YEN
    net = None if unknown_payouts else total_payout - purchase_cost
    roi = None if unknown_payouts or purchase_cost == 0 else total_payout / purchase_cost
    summary: Dict[str, object] = {
        "report_version": REPORT_VERSION,
        "model_version": cfg.version(),
        "config": asdict(cfg),
        "evaluated_rounds": evaluated_rounds,
        "evaluated_tickets": evaluated_tickets,
        "first_round": round_rows[0]["target_round"] if round_rows else None,
        "last_round": round_rows[-1]["target_round"] if round_rows else None,
        "winning_tickets": winning_tickets,
        "winning_ticket_rate": winning_tickets / max(1, evaluated_tickets),
        "grade_counts": grade_counts,
        "purchase_cost_yen": purchase_cost,
        "published_reference_payout_yen": total_payout,
        "published_reference_net_yen": net,
        "published_reference_roi": roi,
        "unknown_payout_rows": unknown_payouts,
        "mean_portfolio_score": float(np.mean(round_scores)) if round_scores else 0.0,
        "mean_portfolio_max_hits": float(np.mean(round_max_hits)) if round_max_hits else 0.0,
        "ge3_round_rate": ge3_rounds / max(1, evaluated_rounds),
        "ge4_round_rate": ge4_rounds / max(1, evaluated_rounds),
        "mean_top7_hits": float(np.mean(top7_hits)) if top7_hits else 0.0,
        "integrity": {
            "actuals_reloaded_independently_from_loto_csv": True,
            "replay_history_matches_actual_main": True,
            "mismatches": 0,
        },
        "independent_evidence": False,
        "promotion_eligible": False,
    }
    return summary, round_rows


def render_full_text(summary: Dict[str, object], rounds: Sequence[Dict[str, object]], data_sha: str) -> str:
    cfg = summary.get("config") or {}
    grades = summary.get("grade_counts") or {}
    grade_text = " / ".join(f"{k}:{v}" for k, v in sorted(grades.items())) or "なし"
    roi = summary.get("published_reference_roi")
    net = summary.get("published_reference_net_yen")
    lines = [
        "LOTO7 最新モデル 過去予測・照合レポート",
        "=" * 78,
        f"生成日時(JST): {summary.get('generated_at_jst', '')}",
        f"モデル: {summary.get('model_version')}",
        f"data SHA256: {data_sha}",
        f"設定: eta={cfg.get('eta')} decay={cfg.get('decay')} expert_mix={cfg.get('expert_uniform_mix')} final_mix={cfg.get('final_uniform_mix')} overlap={cfg.get('overlap_penalty')}",
        "",
        "[総合集計]",
        f"評価回数: {summary.get('evaluated_rounds')}回 ({summary.get('first_round')}〜{summary.get('last_round')})",
        f"照合口数: {summary.get('evaluated_tickets')}口",
        f"平均Top7一致: {float(summary.get('mean_top7_hits', 0.0)):.4f}",
        f"5口平均最大一致: {float(summary.get('mean_portfolio_max_hits', 0.0)):.4f}",
        f"5口平均score: {float(summary.get('mean_portfolio_score', 0.0)):.4f}",
        f"3個以上一致券あり: {float(summary.get('ge3_round_rate', 0.0))*100:.2f}%",
        f"4個以上一致券あり: {float(summary.get('ge4_round_rate', 0.0))*100:.2f}%",
        f"当選口数: {summary.get('winning_tickets')}口 ({float(summary.get('winning_ticket_rate', 0.0))*100:.3f}%)",
        f"等級内訳: {grade_text}",
        f"参考購入額: {int(summary.get('purchase_cost_yen', 0)):,}円",
        f"公表当選額ベース参考払戻: {int(summary.get('published_reference_payout_yen', 0)):,}円",
    ]
    if roi is not None and net is not None:
        lines += [
            f"公表当選額ベース参考差引: {int(net):+,}円",
            f"公表当選額ベース参考回収率: {float(roi)*100:.2f}%",
        ]
    else:
        lines.append(f"当選額未確定行: {int(summary.get('unknown_payout_rows', 0))}口")
    lines += [
        "実績整合性: loto7.csvを別読込して再照合 / mismatch 0",
        "注意: 最新モデルを過去全体へ再適用したResearch評価であり、独立した未来OOS証拠ではありません。",
        "",
        "[回別照合]",
    ]

    for row in rounds:
        lines += [
            "-" * 78,
            f"第{row['target_round']}回  抽せん日:{row['draw_date']}  学習行数:{row['training_rows']}  基準回:第{row['base_round']}回",
            f"Top7予測: {row['top7']}  / Top7一致:{row['top7_hits']}",
            f"実本数字: {row['actual_main']}  / ボーナス: {row['actual_bonus']}",
            f"5口score:{float(row['portfolio_score']):.4f}  最大一致:{int(float(row['portfolio_max_hits']))}",
        ]
        for ticket in row.get("tickets", []) or []:
            lines.append(
                f"  {int(ticket['ticket'])}. {ticket['predicted_numbers']}"
                f" | 本{int(ticket['main_hits'])} / B{int(ticket['bonus_hits'])}"
                f" | {ticket['grade']} | {ticket['published_prize_amount']}"
            )
    lines += ["", "=" * 78, "END", ""]
    return "\n".join(lines)


def render_history_entry(summary: Dict[str, object], data_sha: str) -> str:
    grades = summary.get("grade_counts") or {}
    grade_text = ", ".join(f"{k}:{v}" for k, v in sorted(grades.items())) or "なし"
    roi = summary.get("published_reference_roi")
    return "\n".join([
        "=" * 72,
        f"[{summary.get('generated_at_jst')}] model={summary.get('model_version')}",
        f"data_sha={data_sha}",
        f"rounds={summary.get('evaluated_rounds')} tickets={summary.get('evaluated_tickets')} wins={summary.get('winning_tickets')}",
        f"mean_top7_hits={float(summary.get('mean_top7_hits',0.0)):.4f} mean_max_hits={float(summary.get('mean_portfolio_max_hits',0.0)):.4f} mean_score={float(summary.get('mean_portfolio_score',0.0)):.4f}",
        f"ge3={float(summary.get('ge3_round_rate',0.0))*100:.2f}% ge4={float(summary.get('ge4_round_rate',0.0))*100:.2f}% grades={grade_text}",
        f"cost={int(summary.get('purchase_cost_yen',0)):,} payout={int(summary.get('published_reference_payout_yen',0)):,} roi={'N/A' if roi is None else f'{float(roi)*100:.2f}%'}",
        "Research-only retrospective replay; not Future OOS promotion evidence.",
        "",
    ])


def main() -> int:
    ap = argparse.ArgumentParser(description="Re-run every historical prediction with the accepted latest Research model and emit a text reconciliation report")
    ap.add_argument("--csv", type=Path, default=Path("loto7.csv"))
    ap.add_argument("--out-dir", type=Path, default=Path("loto7_agent_output"))
    ap.add_argument("--feedback-state", type=Path, default=Path("loto7_agent_output/research_feedback_state.json"))
    ap.add_argument("--research-state", type=Path, default=Path("loto7_agent_output/v4_research_state.json"))
    ap.add_argument("--min-train", type=int, default=100)
    ap.add_argument("--pool-size", type=int, default=350)
    ap.add_argument("--if-stale", action="store_true")
    args = ap.parse_args()

    feedback_state = load_json(args.feedback_state, {})
    research_state = load_json(args.research_state, {})
    cfg = accepted_model(feedback_state, research_state)
    data_sha = fingerprint_file(args.csv)
    key = report_key(data_sha, cfg, args.min_train, args.pool_size)

    state_path = args.out_dir / "model_historical_reconciliation_state.json"
    old_state = load_json(state_path, {})
    latest_text = args.out_dir / "latest_model_historical_reconciliation.txt"
    if args.if_stale and is_fresh(old_state, key) and latest_text.exists():
        print(f"[MODEL-HIST-RECON] fresh; skipped model={cfg.version()}")
        return 0

    previous_model = str(old_state.get("model_version", ""))
    reason = "model_updated" if previous_model and previous_model != cfg.version() else "data_or_first_refresh"
    summary, rounds = replay_and_reconcile(args.csv, cfg, args.min_train, args.pool_size)
    summary["generated_at_jst"] = now_jst()
    summary["data_sha256"] = data_sha
    summary["report_key"] = key
    summary["refresh_reason"] = reason

    args.out_dir.mkdir(parents=True, exist_ok=True)
    text = render_full_text(summary, rounds, data_sha)
    latest_text.write_text(text, encoding="utf-8")
    write_json(state_path, summary)

    history_path = args.out_dir / "model_historical_reconciliation_history.txt"
    with history_path.open("a", encoding="utf-8") as f:
        f.write(render_history_entry(summary, data_sha))

    archive_dir = args.out_dir / "model_reconciliation_reports"
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_name = f"{safe_filename(cfg.version())}-{data_sha[:12]}.txt"
    (archive_dir / archive_name).write_text(text, encoding="utf-8")

    update_run_events(args.out_dir / "run_events.json", cfg.version())
    print(
        f"[MODEL-HIST-RECON] model={cfg.version()} rounds={summary['evaluated_rounds']} "
        f"tickets={summary['evaluated_tickets']} wins={summary['winning_tickets']} reason={reason}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
