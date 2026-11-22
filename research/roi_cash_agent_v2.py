#!/usr/bin/env python3
"""Research-only directly payout-trained combination model (candidate v2).

The approved Champion selects the same 35 labels. Candidate v2 trains only on
draws earlier than the requested target, searching for ticket assignments with
better *historical realized* public payout. This may overfit random lottery
outcomes; it is NOT evidence of future ROI gains or a Production promotion.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Sequence

import numpy as np

from balanced_uniform_portfolio import validate_portfolio
from combination_agent35_core import _validate_ranking

VERSION = "research-roi-cash-trained-ranked35-v2"

# Cash rewards are clipped: a single rare large winner cannot dominate
# the optimization. All parameters are fixed BEFORE evaluation.
@dataclass(frozen=True)
class CashAgentConfig:
    lookback: int = 104
    half_life: float = 52.0
    max_swaps: int = 8
    payout_cap_yen: int = 6000
    min_gain_yen_per_draw: float = 0.5
    min_history: int = 100


def _validate_inputs(
    history: np.ndarray, bonus_history: np.ndarray,
    payout_history: np.ndarray, ranking: Sequence[int], cfg: CashAgentConfig,
) -> tuple[np.ndarray,np.ndarray,np.ndarray]:
    _validate_ranking(ranking)
    h=np.asarray(history)
    b=np.asarray(bonus_history)
    p=np.asarray(payout_history)
    if (h.ndim!=2 or h.shape[1]!=37 or len(h)<cfg.min_history
            or b.shape!=h.shape or p.shape!=(len(h),7)):
        raise ValueError("cash agent requires matching 37-label draws, bonuses, and 7-column payout tables")
    if (not np.all((h==0)|(h==1)) or not np.all(h.sum(axis=1)==7)
            or not np.all((b==0)|(b==1)) or not np.all(b.sum(axis=1)==2)
            or np.any((h!=0)&(b!=0))):
        raise ValueError("invalid or overlapping main/bonus draw history")
    if not np.all(np.isfinite(p)) or not np.all((p>=0)|(p==-1)):
        raise ValueError("cash agent requires nonnegative public amounts or -1 for unknown")
    if (cfg.lookback<cfg.min_history or cfg.half_life<=0 or cfg.max_swaps<0
            or cfg.payout_cap_yen<=0 or cfg.min_gain_yen_per_draw<0):
        raise ValueError("invalid training config")
    return h[-cfg.lookback:].astype(np.int8,copy=False), b[-cfg.lookback:].astype(np.int8,copy=False), p[-cfg.lookback:].astype(float,copy=False)


def _public_cash(hits:np.ndarray, bonus_hits:np.ndarray, payouts:np.ndarray, cap:int) -> np.ndarray:
    """Broadcast ticket hit counts (candidate,draw) to the correct historical draw grade."""
    grade=np.zeros_like(hits,dtype=np.int8)
    grade[(hits==3)&(bonus_hits>=1)]=1
    grade[hits==4]=2
    grade[hits==5]=3
    grade[hits==6]=4
    grade[(hits==6)&(bonus_hits>=1)]=5
    grade[hits==7]=6
    values=payouts[np.arange(payouts.shape[0])[None,:],grade]
    return np.where(values<0,np.nan,np.minimum(values,cap))


def candidate_from_cash_history(
    history:np.ndarray, bonus_history:np.ndarray, payout_history:np.ndarray,
    ranking:Sequence[int], config:CashAgentConfig=CashAgentConfig()
) -> tuple[list[tuple[int,...]],dict]:
    """Causal training using only earlier public outcomes; never touches target row.

    History payout layout [zero, sixth, fifth, fourth, third, second, first].
    A -1 means unknown published payout. Such candidate swaps are rejected,
    rather than making up prize values.
    """
    h,b,p=_validate_inputs(history,bonus_history,payout_history,ranking,config)
    weights=0.5**(np.arange(len(h)-1,-1,-1,dtype=float)/config.half_life)
    weights/=weights.sum()
    group_ids=np.arange(35)//7
    pi,pj=np.triu_indices(35,k=1)
    mask=group_ids[pi]!=group_ids[pj]
    pi,pj=pi[mask],pj[mask]
    gi,gj=group_ids[pi],group_ids[pj]
    assigned=np.asarray(ranking[:35],dtype=int)-1
    n_swaps=0
    improvements=[]
    stopped="no_positive_cash_improvement"
    for _ in range(config.max_swaps):
        groups=assigned.reshape(5,7)
        current_h=h[:,groups].sum(axis=2).T  # 5 x prior draws
        current_b=b[:,groups].sum(axis=2).T
        current_cash=_public_cash(current_h,current_b,p,config.payout_cap_yen)
        if not np.all(np.isfinite(current_cash)):
            stopped="missing_historical_public_payout"
            break
        ai=assigned[pi]
        aj=assigned[pj]
        new_hi=current_h[gi]+h[:,aj].T-h[:,ai].T
        new_hj=current_h[gj]+h[:,ai].T-h[:,aj].T
        new_bi=current_b[gi]+b[:,aj].T-b[:,ai].T
        new_bj=current_b[gj]+b[:,ai].T-b[:,aj].T
        new_i=_public_cash(new_hi,new_bi,p,config.payout_cap_yen)
        new_j=_public_cash(new_hj,new_bj,p,config.payout_cap_yen)
        # Any unavailable historical prize invalidates that candidate swap.
        delta=np.sum((new_i+new_j-current_cash[gi]-current_cash[gj])*weights,axis=1)
        delta=np.where(np.isfinite(delta),delta,-np.inf)
        index=int(np.argmax(delta))
        gain=float(delta[index])
        if gain<=config.min_gain_yen_per_draw:
            break
        i,j=int(pi[index]),int(pj[index])
        assigned[i],assigned[j]=assigned[j],assigned[i]
        n_swaps+=1
        improvements.append(gain)
    tickets=[tuple(sorted((assigned.reshape(5,7)[j]+1).tolist())) for j in range(5)]
    validate_portfolio(tickets)
    if sorted(v for group in tickets for v in group)!=sorted(ranking[:35]):
        raise AssertionError("ROI training changed the chosen 35 numbers")
    return tickets, {
        "candidate_version":VERSION,
        "configuration":asdict(config),
        "history_rows":int(len(history)),
        "lookback_used":len(h),
        "cash_objective":"recency_weighted_mean_capped_published_draw_payout_yen",
        "swaps":n_swaps,
        "training_cash_objective_gain_yen_per_draw":float(sum(improvements)),
        "training_cash_swaps_gain":improvements,
        "stop_reason":stopped,
        "production_modified":False,
    }
