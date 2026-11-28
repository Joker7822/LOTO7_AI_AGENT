"""Explicit operator-selected v4 Production adapter, targets 706+ only.

No statistical promotion, purchase, or change to existing freezes. Retain
the exact research v2->v3->v4 algorithm and configuration.
"""
import hashlib
import json
from dataclasses import asdict
from production_disjoint35_policy import ROI_COOCCURRENCE_VERSION
from production_roi_cash35_v2 import candidate_from_canonical_rows as cash_v2, training_arrays_from_canonical_rows, CashAgentConfig
from research import roi_cash_robust_v3 as v3
from research import roi_cash_cooccurrence_v4 as v4

ALGORITHM_VERSION=v4.VERSION
SELECTION_AUTHORITY="explicit_user_instruction_2026-11-28_no_proven_future_roi"
CONFIG={
    "v2":asdict(CashAgentConfig()),
    "v3":{"lookback":v3.LOOKBACK,"min_history":v3.MIN_HISTORY,"round_cap_yen":v3.ROUND_CAP_YEN,
          "concentration_weight_yen":v3.CONCENTRATION_WEIGHT_YEN,"max_swaps":v3.MAX_SWAPS,
          "min_gain_per_draw":v3.MIN_GAIN_PER_DRAW},
    "v4":{"pair_prior":v4.PAIR_PRIOR,"triple_prior":v4.TRIPLE_PRIOR,
          "triple_weight":v4.TRIPLE_WEIGHT,"max_swaps":v4.MAX_SWAPS,"min_gain":v4.MIN_GAIN},
}


def candidate_from_canonical_rows(rows, ranking):
    # Enforce v2's strict historical prize availability guard first.
    cash_v2(rows,ranking)
    h,b,p=training_arrays_from_canonical_rows(rows)
    start,m3=v3.refine(h,b,p,ranking)
    tickets,m4=v4.refine_cooccurrence(h,b,p,ranking,start=start)
    return tickets,{"v3_swaps":m3["swaps"],"v4_swaps":m4["swaps"],
                    "half_interaction_gains":m4["half_interaction_gains"]}


def provenance(*, target_round, data_sha, champion_version, ranking, tickets, meta):
    if type(target_round) is not int or target_round < 706:
        raise ValueError("v4 cannot issue before round 706")
    payload={"target_round":target_round,"source_sha256":data_sha,"champion":champion_version,
             "ranking":list(ranking),"tickets":[list(t) for t in tickets],
             "algorithm_version":ALGORITHM_VERSION,"policy":ROI_COOCCURRENCE_VERSION,
             "authority":SELECTION_AUTHORITY,"config":CONFIG,"diagnostics":meta}
    digest=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
    return {"production_roi_cooccurrence_v4_algorithm_version":ALGORITHM_VERSION,
            "production_roi_cooccurrence_v4_config":CONFIG,
            "production_roi_cooccurrence_v4_training_rows":target_round-1,
            "production_roi_cooccurrence_v4_training_data_sha256":data_sha,
            "production_roi_cooccurrence_v4_selection_authority":SELECTION_AUTHORITY,
            "production_roi_cooccurrence_v4_target_outcome_used":False,
            "production_roi_cooccurrence_v4_diagnostics":meta,
            "production_roi_cooccurrence_v4_layout_sha256":digest}
