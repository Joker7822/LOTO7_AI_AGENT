#!/usr/bin/env python3
"""Budget and risk diagnostics, not a purchase executor or positive-EV estimator."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Mapping, Sequence
import math

from roi_first_governance import ROUND_COST_YEN

VERSION = "roi-first-budget-risk-v1"


@dataclass(frozen=True)
class BudgetLimits:
    max_tickets_per_draw: int = 5
    ticket_price_yen: int = 300
    warning_four_draw_spend_yen: int = 6000
    warning_thirteen_draw_spend_yen: int = 19500


def _validate(config: BudgetLimits) -> None:
    if (type(config.max_tickets_per_draw) is not int
            or type(config.ticket_price_yen) is not int
            or type(config.warning_four_draw_spend_yen) is not int
            or type(config.warning_thirteen_draw_spend_yen) is not int
            or not 1 <= config.max_tickets_per_draw <= 5
            or config.ticket_price_yen != 300
            or config.warning_four_draw_spend_yen < 0
            or config.warning_thirteen_draw_spend_yen < 0):
        raise ValueError("invalid risk budget")


def _rollup(cash: list[int], length: int) -> dict:
    if not cash:
        raise ValueError("risk metrics need confirmed historical rounds")
    k=min(length,len(cash))
    values=[sum(cash[i-k:i]) for i in range(k,len(cash)+1)]
    return {
        "window_rounds":k,
        "worst_net_yen":min(values),
        "best_net_yen":max(values),
        "last_net_yen":values[-1],
    }


def evaluate_budget_risk(
    rounds: Sequence[Mapping],
    roi_report: Mapping,
    selection_report: Mapping,
    config: BudgetLimits = BudgetLimits(),
) -> dict:
    """Read-only. No real spending amounts or user bankroll are assumed."""
    _validate(config)
    if not rounds or not isinstance(roi_report,dict) or not isinstance(selection_report,dict):
        raise ValueError("missing audited cashflow evidence")
    n=len(rounds)
    if (roi_report["periods"]["all_2_plus"]["draws"] != n
            or selection_report["rounds"] != n):
        raise ValueError("mismatched cashflow horizons")
    cash=[]
    last_round=1
    for i,row in enumerate(rounds):
        round_no=int(row["round"])
        if round_no != last_round+1:
            raise ValueError("noncontiguous audit rounds")
        last_round=round_no
        if row.get("public_payout_complete") not in (True,"True","true") or row.get("baseline_payout_complete") not in (True,"True","true"):
            raise ValueError("missing prize amounts must fail closed")
        earned=int(row["public_payout_yen"])
        if earned < 0:
            raise ValueError("invalid negative historical payout")
        cash.append(earned-ROUND_COST_YEN)
    total_cost=n*ROUND_COST_YEN
    combo_total=sum(cash)+total_cost
    if combo_total != roi_report["periods"]["all_2_plus"]["combo_payout_yen"]:
        raise ValueError("cashflow does not reconcile with ROI-first summary")
    if selection_report["cost_yen_per_arm"] != total_cost:
        raise ValueError("selection cost does not reconcile")
    per_round=config.ticket_price_yen*config.max_tickets_per_draw
    limits_breached={
        "per_draw_limit": per_round>ROUND_COST_YEN,
        "four_draw_warning_limit": 4*per_round>config.warning_four_draw_spend_yen,
        "thirteen_draw_warning_limit":13*per_round>config.warning_thirteen_draw_spend_yen,
    }
    return {
        "version":VERSION,
        "purpose":"research_risk_disclosure_not_a_purchase_instruction",
        "budget_config":asdict(config),
        "current_ticket_cost_yen":ROUND_COST_YEN,
        "hypothetical_max_per_draw_yen":per_round,
        "hypothetical_four_draw_spend_yen":4*per_round,
        "hypothetical_thirteen_draw_spend_yen":13*per_round,
        "historical_rounds":n,
        "historical_combination_total_spend_yen":total_cost,
        "historical_combination_total_payout_yen":combo_total,
        "historical_combination_net_yen":combo_total-total_cost,
        "historical_combination_roi":combo_total/total_cost,
        "worst_four_draw_cash_window":_rollup(cash,4),
        "worst_thirteen_draw_cash_window":_rollup(cash,13),
        "limits_breached":limits_breached,
        "expected_future_roi":"not_verified",
        "verified_positive_expected_value":False,
        "automated_purchase_enabled":False,
        "purchase_recommended":False,
        "production_tickets_modified":False,
        "registered_future_oos_modified":False,
        "commentary":(
            "Past cash returns are highly variable and do not imply profitable "
            "future purchases. Estimates of personal affordability or expected "
            "future payout are unavailable without independent evidence."
        ),
    }


def risk_markdown(report: Mapping) -> str:
    return "\n".join([
        "# LOTO7 投資・回収率リスク監査（自動購入なし）",
        "",
        f"- 1回5口の参考支出：**{report['current_ticket_cost_yen']:,}円**",
        f"- 4回継続購入時の参考支出：**{report['hypothetical_four_draw_spend_yen']:,}円**",
        f"- 13回継続購入時の参考支出：**{report['hypothetical_thirteen_draw_spend_yen']:,}円**",
        f"- 過去全期間の仮想純損益：**{report['historical_combination_net_yen']:,}円**",
        f"- 最悪の連続4回の仮想損益：**{report['worst_four_draw_cash_window']['worst_net_yen']:,}円**",
        f"- 最悪の連続13回の仮想損益：**{report['worst_thirteen_draw_cash_window']['worst_net_yen']:,}円**",
        "- 過去データから将来の黒字を確認できません。**自動購入は無効**です。",
        "- 発行予測や凍結台帳は変更しません。",
        "",
    ])
