#!/usr/bin/env python3
"""The operator-selected ROI-cash v2 model's strict published-draw adapter.

This adapter is shared by Production preparation and the independent freeze
auditor.  It never makes a purchase or edits a frozen ticket. The research
v2 candidate defines the exact optimization algorithm/configuration.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict
from datetime import date
from typing import Mapping, Sequence

import numpy as np

from research.roi_cash_agent_v2 import CashAgentConfig, VERSION as ALGORITHM_VERSION, candidate_from_cash_history

PRODUCTION_VERSION = "production-ai-ranked35-roi-cash-v2"
SELECTION_AUTHORITY = "explicit_user_instruction_2026-11-22_no_proven_future_roi"
REQUIRED_MIN_HISTORY = 100
MONEY = re.compile(r"\s*([0-9][0-9,]*)\s*円\s*\Z")
GRADES = ("6等", "5等", "4等", "3等", "2等", "1等")


def _draw_numbers(raw: object, *, count: int) -> list[int]:
    if not isinstance(raw, str):
        raise ValueError("invalid historical main/bonus draw numbers")
    tokens = raw.strip().split()
    if (len(tokens) != count
            or any(not token.isdecimal() or not 1 <= int(token) <= 37
                   for token in tokens)):
        raise ValueError("invalid historical main/bonus draw numbers")
    numbers = [int(token) for token in tokens]
    if len(set(numbers)) != count:
        raise ValueError("duplicate main or bonus numbers")
    return numbers


def training_arrays_from_canonical_rows(
    rows: Sequence[Mapping[str, object]],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (main, bonus, public prize) arrays, grades [none,6,5,4,3,2,1].

    Missing public payouts remain -1; the cash agent may NOT replace them with
    invented payouts. Draws must be exactly #1..#N in canonical source order.
    """
    if not isinstance(rows,(list,tuple)) or len(rows)<REQUIRED_MIN_HISTORY:
        raise ValueError("ROI v2 needs canonical past draw history of at least 100")
    n=len(rows)
    main=np.zeros((n,37),dtype=np.int8)
    bonus=np.zeros((n,37),dtype=np.int8)
    payouts=np.full((n,7),-1.,dtype=np.float64)
    payouts[:,0]=0
    previous_date=None
    for i,row in enumerate(rows):
        if not isinstance(row,Mapping) or row.get("回別")!=f"第{i+1}回":
            raise ValueError("ROI v2 history must be complete ordered draws #1..N")
        dt=date.fromisoformat(str(row.get("抽せん日","")))
        if previous_date is not None and dt<=previous_date:
            raise ValueError("ROI v2 historical draw chronology invalid")
        previous_date=dt
        winning=_draw_numbers(row.get("本数字"),count=7)
        extra=_draw_numbers(row.get("ボーナス数字"),count=2)
        if set(winning)&set(extra):
            raise ValueError("ROI v2 main and bonus draw numbers overlap")
        main[i,np.asarray(winning,dtype=int)-1]=1
        bonus[i,np.asarray(extra,dtype=int)-1]=1
        for j,grade in enumerate(GRADES,1):
            source=row.get(f"{grade}当選金額","")
            match=MONEY.fullmatch(str(source or ""))
            if match:
                value=int(match.group(1).replace(",",""))
                if value<0 or value>10**15:
                    raise ValueError("invalid or excessive public payout")
                payouts[i,j]=float(value)
    return main,bonus,payouts


def candidate_from_canonical_rows(
    rows:Sequence[Mapping[str,object]], ranking:Sequence[int],
    config:CashAgentConfig=CashAgentConfig(),
) -> tuple[list[tuple[int,...]],dict]:
    """Fit using source rows known before the next target; fail closed."""
    main,bonus,payouts=training_arrays_from_canonical_rows(rows)
    tickets,diag=candidate_from_cash_history(main,bonus,payouts,ranking,config)
    if diag["stop_reason"]=="missing_historical_public_payout":
        raise ValueError("missing necessary public payout in ROI v2 history")
    if diag["history_rows"]!=len(rows):
        raise AssertionError("ROI v2 training length mismatch")
    return tickets,diag


def layout_sha256(
    *, target_round:int, data_sha:str, champion_version:str,
    ranking:Sequence[int], tickets:Sequence[Sequence[int]],
    config:CashAgentConfig=CashAgentConfig(),
) -> str:
    obj={
        "target_round":target_round,"data_sha256":data_sha,
        "champion_version":champion_version,"production_policy":PRODUCTION_VERSION,
        "algorithm_version":ALGORITHM_VERSION,
        "ranking":list(ranking),"tickets":[list(t) for t in tickets],
        "config":asdict(config),
        "selection_authority":SELECTION_AUTHORITY,
    }
    return hashlib.sha256(json.dumps(
        obj,sort_keys=True,ensure_ascii=False,separators=(",",":"),allow_nan=False
    ).encode("utf-8")).hexdigest()
