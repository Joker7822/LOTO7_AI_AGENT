#!/usr/bin/env python3
"""Strictly prequential ROI-first shadow strategy.

Each target's decision uses only *earlier* fully settled draws from two
precommitted, equally priced portfolios.  This is a counterfactual shadow
evaluation. It does not change issued Production forecasts or authorize buys.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Mapping, Sequence
import math

import numpy as np

from roi_first_governance import ROUND_COST_YEN

VERSION = "roi-first-prequential-shadow-v1"


@dataclass(frozen=True)
class SelectionConfig:
    lookback: int = 104
    min_settled: int = 52
    min_positive_deltas: int = 5
    min_gain_yen: int = 3000
    max_top_wins: int = 4


def _integer(row: Mapping, key: str) -> int:
    value = row.get(key)
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"invalid {key}") from exc
    if not math.isfinite(number) or not number.is_integer() or number < 0:
        raise ValueError(f"invalid {key}")
    return int(number)


def _bool(row: Mapping, key: str) -> bool:
    flag = row.get(key)
    if flag in (True, "True", "true"):
        return True
    if flag in (False, "False", "false"):
        return False
    raise ValueError(f"invalid {key}")


def choose_from_prefix(
    settled_prior_rows: Sequence[Mapping], config: SelectionConfig = SelectionConfig()
) -> dict:
    """Deterministic selection using ONLY settled earlier rows.

    High-variance cash returns require two disjoint past-window halves to
    improve and remain positive after removing the largest few wins. This
    should not be understood as a statistically significant test.
    """
    if (config.lookback < config.min_settled or config.min_settled < 26
            or config.max_top_wins < 0 or config.min_positive_deltas < 1
            or config.min_gain_yen < 0):
        raise ValueError("invalid ROI shadow selection config")
    past = list(settled_prior_rows)[-config.lookback:]
    deltas = []
    previous = None
    for row in past:
        r = _integer(row, "round")
        if previous is not None and r != previous+1:
            raise ValueError("noncontiguous previous draw sequence")
        previous = r
        if not (_bool(row,"public_payout_complete")
                and _bool(row,"baseline_payout_complete")):
            return {
                "choice": "incumbent", "reason": "incomplete_prior_payout",
                "settled_draws": len(deltas),
            }
        d = _integer(row,"public_payout_yen")-_integer(row,"baseline_payout_yen")
        deltas.append(d)
    if len(deltas) < config.min_settled:
        return {"choice": "incumbent", "reason": "insufficient_past_settlements",
                "settled_draws": len(deltas)}
    mid = len(deltas)//2
    gains = sorted((d for d in deltas if d > 0),reverse=True)
    trimmed = sum(deltas)-sum(gains[:config.max_top_wins])
    positive = sum(d > 0 for d in deltas)
    ok = (
        sum(deltas) >= config.min_gain_yen
        and sum(deltas[:mid]) > 0
        and sum(deltas[mid:]) > 0
        and trimmed > 0
        and positive >= config.min_positive_deltas
    )
    return {
        "choice": "combination" if ok else "incumbent",
        "reason": "past_cashflow_robustness_pass" if ok else "past_cashflow_robustness_fail",
        "settled_draws": len(deltas),
        "past_delta_yen": sum(deltas),
        "past_early_half_delta_yen": sum(deltas[:mid]),
        "past_late_half_delta_yen": sum(deltas[mid:]),
        "past_gain_after_top_wins_yen": trimmed,
        "past_positive_difference_draws": positive,
    }


def backtest_shadow(
    rounds: Sequence[Mapping], config: SelectionConfig = SelectionConfig(),
    *, initial_round: int = 101
) -> dict:
    """Strict prefix chronological simulator; no information from target outcomes.

    For each round, freeze the decision FIRST, then score that target and append
    its payout to prior settlements. Incomplete amounts invalidate evaluation.
    """
    if type(initial_round) is not int or initial_round < 2:
        raise ValueError("initial round must be >=2")
    if not rounds:
        raise ValueError("empty replay")
    prior: list[Mapping] = []
    reports: list[dict] = []
    prev = None
    for row in rounds:
        round_no = _integer(row,"round")
        if prev is None and round_no != 2:
            raise ValueError("full contiguous rounds from 2 required")
        if prev is not None and round_no != prev+1:
            raise ValueError("noncontiguous replay rounds")
        prev = round_no
        # Train solely with earlier settled >= initial_round targets; initial
        # 2-100 data is not evidence for a trained combination policy.
        decision = choose_from_prefix(prior,config)
        if not (_bool(row,"public_payout_complete")
                and _bool(row,"baseline_payout_complete")):
            raise ValueError(f"unknown payout at round {round_no}")
        combo = _integer(row,"public_payout_yen")
        baseline = _integer(row,"baseline_payout_yen")
        if round_no < initial_round:
            choice = "incumbent"
            reason = "untrained_startup"
        else:
            choice = decision["choice"]
            reason = decision["reason"]
        selected = combo if choice == "combination" else baseline
        reports.append({
            "round": round_no, "choice": choice, "reason": reason,
            "prefix_trained_rounds": decision["settled_draws"],
            "selected_payout_yen": selected,
            "incumbent_payout_yen": baseline,
            "always_combination_payout_yen": combo,
            "selected_minus_incumbent_yen": selected-baseline,
            "purchase_cost_yen": ROUND_COST_YEN,
            "prefix_cashflow_delta_yen": decision.get("past_delta_yen"),
        })
        if round_no >= initial_round:
            prior.append(row)
    n=len(reports)
    cost=n*ROUND_COST_YEN
    selected=sum(row["selected_payout_yen"] for row in reports)
    incumbent=sum(row["incumbent_payout_yen"] for row in reports)
    combo=sum(row["always_combination_payout_yen"] for row in reports)
    return {
        "version": VERSION, "evaluation": "research_only_retrospective_nested_strict_prefix",
        "configuration": asdict(config), "initial_trained_round":initial_round,
        "rounds":n, "start_round":reports[0]["round"],
        "end_round":reports[-1]["round"],
        "cost_yen_per_arm":cost,
        "selected_payout_yen":selected, "incumbent_payout_yen":incumbent,
        "always_combination_payout_yen":combo,
        "selected_roi":selected/cost, "incumbent_roi":incumbent/cost,
        "always_combination_roi":combo/cost,
        "selected_minus_incumbent_yen":selected-incumbent,
        "combination_chosen_draws":sum(r["choice"]=="combination" for r in reports),
        "policy_decisions":reports,
        "production_tickets_modified":False, "buying_authorized":False,
        "signal_skill_confirmed":False,
        "future_oos_required":True,
    }


def shadow_markdown(report: Mapping) -> str:
    return "\n".join([
        "# 回収率優先の逐次選択AI（研究専用）",
        "",
        "- 各回の選択は、その回より前に確定した払戻だけで行います。後知恵の最適選択はしません。",
        "- 生成済み本番5口の並べ替え・再発行・購入注文は実行しません。",
        "- 過去データで閾値も設計されているため、将来の予測優位性は未確認です。",
        "",
        "| 方式 | 仮想払戻金 | 仮想購入費 | 回収率 |",
        "|---|---:|---:|---:|",
        f"| 逐次ROI選択 | {report['selected_payout_yen']:,}円 | {report['cost_yen_per_arm']:,}円 | {100*report['selected_roi']:.2f}% |",
        f"| 従来順位順 | {report['incumbent_payout_yen']:,}円 | {report['cost_yen_per_arm']:,}円 | {100*report['incumbent_roi']:.2f}% |",
        f"| 常時組合せAI | {report['always_combination_payout_yen']:,}円 | {report['cost_yen_per_arm']:,}円 | {100*report['always_combination_roi']:.2f}% |",
        "",
        f"- 過去結果を見ずに組合せAIを選択した回数：**{report['combination_chosen_draws']}回**",
        "- 回収率だけで自動購入・Production昇格は許可しません。",
        "",
    ])
