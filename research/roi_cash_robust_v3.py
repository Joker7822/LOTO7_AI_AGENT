"""Research-only robust local refinement of the existing cash-v2 partition.

Keep the identical 35 ranked labels and five disjoint tickets. Do not change
the deployed v2 code, ranking, prediction ledger or promotion policy.
"""
from __future__ import annotations
import numpy as np
from balanced_uniform_portfolio import validate_portfolio
from research.roi_cash_agent_v2 import (
    CashAgentConfig, _validate_inputs, _public_cash, candidate_from_cash_history,
)

VERSION = "research-roi-cash-robust-combination-v3"
LOOKBACK = 104
MIN_HISTORY = 104
ROUND_CAP_YEN = 3000
CONCENTRATION_WEIGHT_YEN = 300
MAX_SWAPS = 4
MIN_GAIN_PER_DRAW = 0.5


def refine(history, bonus, payouts, ranking):
    # The v2 starting partition is fitted on the identical preceding prefix.
    start, v2_meta = candidate_from_cash_history(history, bonus, payouts, ranking)
    if len(history) < MIN_HISTORY:
        return start, {"version": VERSION, "swaps": 0, "status": "warmup_v2",
                       "half_gains": [0.0, 0.0], "history_rows": len(history)}
    h, b, p = _validate_inputs(history, bonus, payouts, ranking, CashAgentConfig())
    if len(h) != LOOKBACK:
        raise ValueError("robust optimizer needs 104 prior draws")
    assigned = np.asarray(start, dtype=int).reshape(-1) - 1
    ids = np.arange(35) // 7
    i, j = np.triu_indices(35, k=1)
    mask = ids[i] != ids[j]
    i, j = i[mask], j[mask]
    gi, gj = ids[i], ids[j]
    half_gains = np.zeros(2)
    swaps = 0
    status = "no_robust_gain"
    if v2_meta["stop_reason"] == "missing_historical_public_payout":
        return start, {"version":VERSION, "swaps":0, "status":"missing_payout",
                       "half_gains":[0.0,0.0], "history_rows":len(history)}
    for _ in range(MAX_SWAPS):
        groups = assigned.reshape(5, 7)
        hits = h[:, groups].sum(axis=2).T
        extras = b[:, groups].sum(axis=2).T
        cash = _public_cash(hits, extras, p, ROUND_CAP_YEN)
        if not np.all(np.isfinite(cash)):
            status = "missing_payout"
            break
        original_max = hits.max(axis=0)
        original_cash = np.minimum(cash.sum(axis=0), ROUND_CAP_YEN)
        ai, aj = assigned[i], assigned[j]
        hi = hits[gi] + h[:, aj].T - h[:, ai].T
        hj = hits[gj] + h[:, ai].T - h[:, aj].T
        bi = extras[gi] + b[:, aj].T - b[:, ai].T
        bj = extras[gj] + b[:, ai].T - b[:, aj].T
        ci = _public_cash(hi, bi, p, ROUND_CAP_YEN)
        cj = _public_cash(hj, bj, p, ROUND_CAP_YEN)
        other_max = np.zeros_like(hi)
        for group in range(5):
            other_max = np.maximum(other_max, np.where(
                ((gi != group) & (gj != group))[:, None], hits[group], 0))
        new_max = np.maximum(np.maximum(hi, hj), other_max)
        new_cash = np.minimum(cash.sum(axis=0) - cash[gi] - cash[gj] + ci + cj,
                              ROUND_CAP_YEN)
        # Converting booleans before subtraction is intentional.
        concentrated = (new_max >= 3).astype(int) - (original_max >= 3).astype(int)
        cash_delta = new_cash - original_cash
        objective = cash_delta + CONCENTRATION_WEIGHT_YEN * concentrated
        half = LOOKBACK // 2
        gains = np.stack([objective[:, :half].mean(axis=1),
                          objective[:, half:].mean(axis=1)], axis=1)
        # No improvement may be bought by worsening cash or the 3+ rate
        # in either of two nonoverlapping historical windows.
        eligible = (np.isfinite(gains).all(axis=1)
                    & (cash_delta[:, :half].sum(axis=1) >= 0)
                    & (cash_delta[:, half:].sum(axis=1) >= 0)
                    & (concentrated[:, :half].sum(axis=1) >= 0)
                    & (concentrated[:, half:].sum(axis=1) >= 0)
                    & (gains.min(axis=1) >= 0))
        merit = np.where(eligible, gains.min(axis=1) + 0.5*gains.mean(axis=1), -np.inf)
        idx = int(np.argmax(merit))
        if not np.isfinite(merit[idx]) or gains[idx].mean() <= MIN_GAIN_PER_DRAW:
            break
        x, y = int(i[idx]), int(j[idx])
        assigned[x], assigned[y] = assigned[y], assigned[x]
        half_gains += gains[idx]
        swaps += 1
        status = "refined"
    result = [tuple(sorted((row+1).tolist())) for row in assigned.reshape(5,7)]
    validate_portfolio(result)
    if sorted(n for row in result for n in row) != sorted(ranking[:35]):
        raise AssertionError("robust refinement changed selected labels")
    return result, {"version":VERSION, "swaps":swaps, "status":status,
                    "half_gains":half_gains.tolist(), "history_rows":len(history)}
