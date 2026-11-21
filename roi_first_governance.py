#!/usr/bin/env python3
"""Cash-return-first governance for ranked35 Production combination research.

Return on investment (ROI) is published prizes / hypothetical ticket costs,
NOT a claim of live purchases or a reliable prediction advantage. All
promotion gates require independent prospective verification, regardless of
retrospective outcomes.  This module NEVER changes Production tickets.
"""
from __future__ import annotations

import math
from collections import defaultdict
from typing import Mapping, Sequence

import numpy as np

VERSION = "roi-first-combination-evaluation-v1"
TICKET_COST_YEN = 300
TICKETS_PER_ROUND = 5
ROUND_COST_YEN = TICKET_COST_YEN * TICKETS_PER_ROUND
PRIMARY_KPI = "public_historical_payout_yen_divided_by_1500_yen_per_round"
PERIODS = ("all_2_plus", "trained_101_plus", "recent_120", "recent_60", "recent_30")


def _number(value: object, key: str, *, allow_float: bool = False) -> float:
    try:
        n = float(value)
    except (ValueError, TypeError, OverflowError) as exc:
        raise ValueError(f"missing or invalid {key}") from exc
    if not math.isfinite(n) or n < 0 or (not allow_float and not n.is_integer()):
        raise ValueError(f"invalid nonnegative {key}")
    return n


def _verified_complete(value: object) -> bool:
    if value is True or value == "True" or value == "true":
        return True
    if value is False or value == "False" or value == "false":
        return False
    raise ValueError("missing or invalid payout completeness flag")


def _normalize(rows: Sequence[Mapping[str, object]]) -> list[dict]:
    normalized: list[dict] = []
    previous = None
    for row in rows:
        round_no = int(_number(row.get("round"), "round"))
        if round_no < 2 or (previous is not None and round_no != previous + 1):
            raise ValueError("ROI analysis requires chronological consecutive draw rounds starting at 2")
        if previous is None and round_no != 2:
            raise ValueError("ROI analysis requires chronological consecutive draw rounds starting at 2")
        previous = round_no
        complete = (_verified_complete(row.get("baseline_payout_complete"))
                    and _verified_complete(row.get("public_payout_complete")))
        a = int(_number(row.get("public_payout_yen"), "AI payout"))
        b = int(_number(row.get("baseline_payout_yen"), "baseline payout"))
        year_text = str(row.get("draw_date") or "")
        if len(year_text) != 10 or year_text[4] != "-" or year_text[7] != "-":
            raise ValueError("ROI requires concrete chronological draw dates")
        try:
            import datetime
            datetime.date.fromisoformat(year_text)
        except (ValueError, TypeError) as exc:
            raise ValueError("invalid draw date") from exc
        normalized.append({
            "round": round_no, "draw_date": year_text, "year": year_text[:4],
            "combo": a, "baseline": b, "delta": a - b,
            "complete": complete,
            "combo_score": float(row["portfolio_score"]),
            "baseline_score": float(row["baseline_score"]),
        })
    if not normalized:
        raise ValueError("no cashflow history to evaluate")
    return normalized


def paired_signflip_yen(deltas: Sequence[int], *, seed: int, reps: int = 4096) -> dict:
    """Exploratory, one-sided paired test. This is NOT a future OOS p-value."""
    x = np.asarray(deltas, dtype=float)
    if not len(x) or reps < 1 or not np.all(np.isfinite(x)):
        raise ValueError("invalid paired randomization data")
    observed = float(x.mean())
    if observed <= 0:
        return {"n": len(x), "mean_yen_per_draw": observed, "one_sided_p": 1.0}
    rng = np.random.default_rng(seed)
    exceed = 0
    for i in range(0, reps, 256):
        size = min(reps - i, 256)
        signs = rng.choice(np.array([-1.0, 1.0]), size=(size, len(x)))
        exceed += int(np.count_nonzero(np.mean(signs*x, axis=1) >= observed))
    return {
        "n": len(x),
        "mean_yen_per_draw": observed,
        "one_sided_p": float((exceed+1)/(reps+1)),
    }


def _period(rows: list[dict], *, seed: int) -> dict:
    if not rows:
        return {"draws": 0, "valid": False}
    if not all(r["complete"] for r in rows):
        # Refuse to treat unknown prize money as zero for any arm.
        return {"draws": len(rows), "valid": False,
                "missing_payout_rounds": sum(not r["complete"] for r in rows),
                "adoption_eligible": False}
    count = len(rows)
    cost = count * ROUND_COST_YEN
    combo = sum(r["combo"] for r in rows)
    baseline = sum(r["baseline"] for r in rows)
    diffs = [r["delta"] for r in rows]
    total_delta = combo - baseline
    positive = sorted((d for d in diffs if d > 0), reverse=True)
    # One or a few fourth-tier prizes can dominate the apparent ROI edge.
    top4 = sum(positive[:4])
    return {
        "valid": True, "draws": count,
        "start_round": rows[0]["round"], "end_round": rows[-1]["round"],
        "start_date": rows[0]["draw_date"], "end_date": rows[-1]["draw_date"],
        "ticket_count_per_arm": TICKETS_PER_ROUND * count,
        "purchase_cost_yen_per_arm": cost,
        "combo_payout_yen": combo, "baseline_payout_yen": baseline,
        "combo_profit_yen": combo - cost, "baseline_profit_yen": baseline - cost,
        "combo_roi": combo / cost, "baseline_roi": baseline / cost,
        "roi_delta_percentage_points": 100*(combo-baseline)/cost,
        "payout_delta_yen": total_delta,
        "payout_win_rounds": sum(d > 0 for d in diffs),
        "payout_loss_rounds": sum(d < 0 for d in diffs),
        "payout_equal_rounds": sum(d == 0 for d in diffs),
        "largest_four_positive_gain_rounds_yen": top4,
        "delta_excluding_four_largest_positive_gain_rounds_yen": total_delta - top4,
        "combo_max_single_round_payout_yen": max(r["combo"] for r in rows),
        "baseline_max_single_round_payout_yen": max(r["baseline"] for r in rows),
        "paired_cashflow_signflip_exploratory": paired_signflip_yen(diffs, seed=seed),
        "combo_mean_diagnostic_score": float(np.mean([r["combo_score"] for r in rows])),
        "baseline_mean_diagnostic_score": float(np.mean([r["baseline_score"] for r in rows])),
    }


def evaluate_roi_first(rows: Sequence[Mapping[str, object]]) -> dict:
    cleaned = _normalize(rows)
    trained = [row for row in cleaned if row["round"] >= 101]
    if not trained:
        raise ValueError("ROI decision requires trained combination history after round 100")
    periods = {
        "all_2_plus": _period(cleaned, seed=10800),
        "trained_101_plus": _period(trained, seed=10801),
        "recent_120": _period(trained[-120:], seed=10802),
        "recent_60": _period(trained[-60:], seed=10803),
        "recent_30": _period(trained[-30:], seed=10804),
    }
    by_year = defaultdict(list)
    for row in cleaned:
        by_year[row["year"]].append(row)
    annual = {year: _period(value, seed=11000+int(year))
              for year,value in sorted(by_year.items())}
    if all(p["valid"] for p in periods.values()):
        trained_metrics = periods["trained_101_plus"]
        checks = {
            "positive_trained_total_cashflow": trained_metrics["payout_delta_yen"] > 0,
            "positive_recent_120_cashflow": periods["recent_120"]["payout_delta_yen"] > 0,
            "positive_recent_60_cashflow": periods["recent_60"]["payout_delta_yen"] > 0,
            "positive_recent_30_cashflow": periods["recent_30"]["payout_delta_yen"] > 0,
            "not_driven_by_four_best_positive_rounds":
                trained_metrics["delta_excluding_four_largest_positive_gain_rounds_yen"] > 0,
            "one_sided_cashflow_signflip_below_0_05_exploratory":
                trained_metrics["paired_cashflow_signflip_exploratory"]["one_sided_p"] < 0.05,
        }
    else:
        checks = {"all_payout_data_complete": False}
    return {
        "version": VERSION,
        "primary_kpi": PRIMARY_KPI,
        "ticket_price_yen": TICKET_COST_YEN,
        "ticket_count_per_draw": TICKETS_PER_ROUND,
        "exact_null": {
            "expected_first_prize_probability_for_five_distinct_tickets": 5 / math.comb(37, 7),
            "fair_draw_unchanged_by_repartition": True,
        },
        "periods": periods, "annual": annual,
        "cashflow_adoption_checks": checks,
        "cashflow_checks_all_pass": all(checks.values()),
        "authorizes_model_promotion": False,
        "requires_new_frozen_prospective_oos": True,
        "meaning": (
            "This report prioritizes realized hypothetical returns, but historical "
            "payouts cannot establish future profitability or a learnable unfair "
            "lottery distribution. Tests are retrospective and exploratory."
        ),
    }


def roi_markdown(report: Mapping[str, object]) -> str:
    labels = [
        ("all_2_plus", "第2回〜最終"),
        ("trained_101_plus", "第101回〜最終"),
        ("recent_120", "直近120回"),
        ("recent_60", "直近60回"),
        ("recent_30", "直近30回"),
    ]
    lines = [
        "# 回収率最優先（ROI-first）再検証",
        "",
        "- 主指標：**公表払戻金総額 ÷ 5口×300円×評価回数**。購入したと仮定した参考数値です。",
        "- 比較：AI組合せ vs 同じ35数字を順位順に配置。発行済み本番台帳は変更しません。",
        "",
        "| 期間 | 回数 | 組合せAI払戻 | 順位順払戻 | 組合せROI | 順位順ROI | ROI差 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for key,label in labels:
        p=report["periods"][key]
        if not p["valid"]:
            lines.append(f"| {label} | {p['draws']} | 不明 | 不明 | 不明 | 不明 | 不明 |")
            continue
        lines.append(
            f"| {label} | {p['draws']} | {p['combo_payout_yen']:,}円 | "
            f"{p['baseline_payout_yen']:,}円 | {100*p['combo_roi']:.2f}% | "
            f"{100*p['baseline_roi']:.2f}% | "
            f"{p['roi_delta_percentage_points']:+.2f}pt |"
        )
    lines += ["", "## 年別の回収率", "",
              "| 年 | 回数 | AI ROI | 順位順 ROI | 差額 |",
              "|---|---:|---:|---:|---:|"]
    for year,p in report["annual"].items():
        if p["valid"]:
            lines.append(
                f"| {year} | {p['draws']} | {100*p['combo_roi']:.2f}% | "
                f"{100*p['baseline_roi']:.2f}% | {p['payout_delta_yen']:+,}円 |"
            )
    trained=report["periods"]["trained_101_plus"]
    lines+= [
        "", "## 収益の偏りと採用ゲート", "",
        f"- 第101回以降の払戻差額：**{trained.get('payout_delta_yen', 0):+,}円**",
        f"- プラス寄与の大きい4回の合計：**{trained.get('largest_four_positive_gain_rounds_yen', 0):,}円**",
        f"- 上記4回のプラス寄与を除いた差額：**{trained.get('delta_excluding_four_largest_positive_gain_rounds_yen', 0):+,}円**",
        f"- 回収率優先の頑健性ゲート：**{'通過' if report['cashflow_checks_all_pass'] else '不通過'}**",
        "- ゲートは履歴分析の参考条件です。通過しても未来の収益は保証されず、本番Championの昇格を許可しません。",
        "- 1等確率は公正抽せんなら5/10,295,472で固定です。",
        "",
    ]
    return "\n".join(lines)


__all__ = ["VERSION", "PRIMARY_KPI", "TICKET_COST_YEN", "TICKETS_PER_ROUND",
           "evaluate_roi_first", "roi_markdown", "paired_signflip_yen"]
