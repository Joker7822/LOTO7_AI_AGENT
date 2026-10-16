#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import math
from typing import Dict, Sequence, Tuple

import numpy as np

from joint_set_v2_model import (
    UNIFORM_P,
    UNIFORM_TOP7_HITS,
    ForecastBundle,
    JointSetV2Config,
    project_inclusion,
)

PORTFOLIO_RANK_GATE_VERSION = "joint-set-v2.1-rank-gate-v1"
PORTFOLIO_RANK_GATE_CEILING = 0.35
PORTFOLIO_RANK_EDGE_SCALE = 0.20
PORTFOLIO_RANK_Z_SCALE = 2.0
ZERO_VARIANCE_Z = 8.0


def portfolio_rank_gate(
    calibration_rows: Sequence[Dict[str, float]],
    regime: np.ndarray,
    cfg: JointSetV2Config,
) -> Tuple[float, Dict[str, float]]:
    """Prior-only ordinal evidence gate used only for portfolio construction.

    The calibrated Bernoulli inclusion probabilities remain unchanged. This gate
    only controls how strongly the ticket scenario/proposal generator is allowed
    to use the already-fixed raw ranking when ordinal Top-7 evidence is positive.
    """
    rows = list(calibration_rows[-max(30, int(cfg.gate_window)):])
    if len(rows) < 30:
        return 0.0, {
            "n": float(len(rows)),
            "rank_edge": 0.0,
            "rank_z": 0.0,
            "rank_gate": 0.0,
        }

    hits = np.asarray([float(r["top7_hits"]) for r in rows], dtype=float)
    edge = float(hits.mean() - UNIFORM_TOP7_HITS)
    sd = float(hits.std(ddof=1)) if len(hits) > 1 else 0.0
    if sd > 1e-12:
        se = sd / math.sqrt(len(hits))
        z = edge / se
    elif edge > 0.0:
        z = ZERO_VARIANCE_Z
    elif edge < 0.0:
        z = -ZERO_VARIANCE_Z
    else:
        z = 0.0

    if edge <= 0.0 or z <= 0.0:
        gate = 0.0
    else:
        edge_strength = min(1.0, edge / PORTFOLIO_RANK_EDGE_SCALE)
        z_strength = 1.0 - math.exp(-z / PORTFOLIO_RANK_Z_SCALE)
        gate = PORTFOLIO_RANK_GATE_CEILING * edge_strength * z_strength

    volatile = float(regime[2])
    gate *= max(0.35, 1.0 - 0.65 * volatile)
    gate = float(np.clip(gate, 0.0, PORTFOLIO_RANK_GATE_CEILING))
    return gate, {
        "n": float(len(rows)),
        "rank_edge": edge,
        "rank_z": float(z),
        "rank_gate": gate,
    }


def portfolio_forecast_bundle(
    calibrated: ForecastBundle,
    calibration_rows: Sequence[Dict[str, float]],
    cfg: JointSetV2Config,
) -> Tuple[ForecastBundle, Dict[str, float]]:
    """Build a portfolio-only bundle without altering calibrated probabilities."""
    rank_gate, diag = portfolio_rank_gate(calibration_rows, calibrated.regime, cfg)
    portfolio_gate = max(float(calibrated.gate), float(rank_gate))
    p = (1.0 - portfolio_gate) * UNIFORM_P + portfolio_gate * calibrated.raw_inclusion_p
    p = project_inclusion(p)

    pair_multiplier = portfolio_gate / max(float(calibrated.gate), 1e-9)
    pair_strength = float(calibrated.effective_pair_strength) * pair_multiplier
    pair_strength = float(np.clip(pair_strength, -abs(cfg.pair_strength), abs(cfg.pair_strength)))

    bundle = ForecastBundle(
        inclusion_p=p,
        raw_inclusion_p=calibrated.raw_inclusion_p,
        pair_matrix=calibrated.pair_matrix,
        regime=calibrated.regime,
        gate=portfolio_gate,
        effective_pair_strength=pair_strength,
        gate_diagnostics={
            **calibrated.gate_diagnostics,
            "calibrated_probability_gate": float(calibrated.gate),
            "portfolio_rank_gate": float(rank_gate),
            "portfolio_gate": float(portfolio_gate),
            "rank_edge": float(diag["rank_edge"]),
            "rank_z": float(diag["rank_z"]),
        },
    )
    return bundle, bundle.gate_diagnostics
