#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import numpy as np

import loto7_v2_runner as v2
import signal_expert_attribution_oos as attr
from loto7_evolving_agent import N_NUMBERS


_ORIGINAL_CHAMPION_SNAPSHOT = attr.champion_snapshot


def stable_champion_snapshot(
    x: np.ndarray,
    cfg: v2.ModelConfig,
    min_train: int = attr.MIN_TRAIN,
):
    """Return the attribution snapshot with the canonical Champion q.

    signal_expert_attribution_oos decomposes the Champion distribution from the
    expert mixture.  That decomposition is mathematically equivalent to
    v2._score_distribution, but a different floating-point accumulation order
    can change .17g canonical strings and therefore SHA-256.  Champion
    calibration freezes the v2._score_distribution result, so use that exact
    path as the canonical final_q while retaining and checking the expert
    decomposition.
    """
    snap = _ORIGINAL_CHAMPION_SNAPSHOT(x, cfg, min_train=min_train)
    keys = list(snap["keys"])
    logw = np.asarray(snap["log_weights"], dtype=float)
    direct = np.asarray(v2._score_distribution(x, keys, logw, cfg), dtype=float)

    uniform = np.ones(N_NUMBERS, dtype=float) / N_NUMBERS
    reconstructed = uniform + np.sum(
        np.stack([np.asarray(snap["contributions"][k], dtype=float) for k in keys], axis=0),
        axis=0,
    )
    decomposition_error = float(np.max(np.abs(reconstructed - direct)))
    if decomposition_error > 2e-15:
        raise RuntimeError("expert contribution decomposition does not reproduce canonical v2 Champion q")

    snap["final_q"] = direct
    snap["decomposition_max_abs_error"] = decomposition_error
    return snap


def main() -> int:
    # freeze_reference resolves champion_snapshot from its module globals at call
    # time, so patch only the workflow entrypoint without weakening the existing
    # same-target hash guard.
    attr.champion_snapshot = stable_champion_snapshot
    return attr.main()


if __name__ == "__main__":
    raise SystemExit(main())
