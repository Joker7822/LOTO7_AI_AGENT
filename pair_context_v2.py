#!/usr/bin/env python3
"""Pair-context v2: numerically exact, versioned, research-only replacement.

Do not substitute this mathematical rule under an old Champion model ID.
The historical v1 int8 rule is kept byte-for-byte for prefrozen forecasts and
legacy reproducibility; a separate prospective registration is required before
v2 can influence any Production or Future-OOS result.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from loto7_evolving_agent import (
    N_NUMBERS, PICKS, fingerprint_file, make_history, read_csv_flexible, zsoftmax,
)

VERSION = "pair-context-v2-int64-prospective-candidate"
DEFAULT_WINDOW = 60


def validated_history(history: np.ndarray) -> np.ndarray:
    data = np.asarray(history)
    if (data.ndim != 2 or data.shape[1] != N_NUMBERS
            or not np.issubdtype(data.dtype, np.integer) or len(data) < 20):
        raise ValueError("pair-context-v2 requires >=20 integer 37-column draws")
    if (not np.all((data == 0) | (data == 1))
            or not np.all(data.sum(axis=1, dtype=np.int64) == PICKS)):
        raise ValueError("each draw must have exactly seven binary outcomes")
    # Convert BEFORE multiplication. Casting the wrapped result afterwards
    # cannot recover counts that overflowed int8 at >=128 observations.
    return data.astype(np.int64, copy=False)


def exact_cooccurrence(history: np.ndarray) -> np.ndarray:
    x = validated_history(history)
    return x.T @ x


def probability(history: np.ndarray) -> np.ndarray:
    """Reproduce v1 pair-context formula, except use exact wide arithmetic."""
    x = validated_history(history)
    co = x.T @ x
    last = np.flatnonzero(x[-1])
    den = np.maximum(x.sum(axis=0, dtype=np.int64).astype(float)[last], 1.0)
    pair = (co[:, last].astype(float) / den).mean(axis=1)
    p = zsoftmax(pair, 1.40)
    if (p.shape != (N_NUMBERS,) or not np.all(np.isfinite(p))
            or np.any(p <= 0) or not np.isclose(p.sum(), 1.0, atol=1e-12)):
        raise ArithmeticError("invalid corrected pair-context distribution")
    return p


def legacy_probability(history: np.ndarray) -> np.ndarray:
    """Pure compatibility reference; NEVER used as the corrected candidate."""
    x = validated_history(history).astype(np.int8)
    co = x.T @ x
    last = np.flatnonzero(x[-1])
    den = np.maximum(x.sum(axis=0).astype(float)[last], 1.0)
    return zsoftmax((co[:, last].astype(float) / den).mean(axis=1), 1.40)


def diagnostics(csv_path: Path, last_n: int = DEFAULT_WINDOW) -> dict:
    history, clean = make_history(read_csv_flexible(csv_path))
    if last_n < 1 or len(history) < last_n + 20:
        raise ValueError("too few rounds for chronological evaluation")
    x = validated_history(history)
    co_exact = x.T @ x
    legacy = x.astype(np.int8).T @ x.astype(np.int8)
    overflow = int(np.count_nonzero(co_exact != legacy.astype(np.int64)))
    q = probability(history)
    legacy_q = legacy_probability(history)
    edges, corrected_hits, legacy_hits = [], [], []
    # Every scored draw t is excluded from its forecast; this is a reused
    # historical *diagnostic*, not a prospective or independent result.
    for t in range(len(x) - last_n, len(x)):
        old = legacy_probability(x[:t])
        new = probability(x[:t])
        actual = np.flatnonzero(x[t])
        edges.append(float(np.log(new[actual]).sum() - np.log(old[actual]).sum()))
        corrected_hits.append(int(np.intersect1d(np.argsort(new)[-7:], actual).size))
        legacy_hits.append(int(np.intersect1d(np.argsort(old)[-7:], actual).size))
    module_path = Path(__file__).resolve()
    return {
        "version": VERSION,
        "model_family": "pair_context",
        "data_sha256": fingerprint_file(csv_path),
        "implementation_sha256": hashlib.sha256(module_path.read_bytes()).hexdigest(),
        "history_draws": len(x),
        "latest_draw_date": clean["抽せん日"].iloc[-1].date().isoformat(),
        "int8_corrupted_cooccurrence_cells": overflow,
        "int64_corrupted_cooccurrence_cells": 0,
        "last_n": last_n,
        "evaluated_rounds": list(range(len(x) - last_n + 1, len(x) + 1)),
        "chronological_prior_only": True,
        "independent_evidence": False,
        "historical_selection_only": True,
        "prospective_edge_confirmed": False,
        "production_changed": False,
        "future_oos_changed": False,
        "promotion_authorized": False,
        "historical_mean_log_delta_v2_minus_v1": float(np.mean(edges)),
        "historical_mean_top7_hits_v2": float(np.mean(corrected_hits)),
        "historical_mean_top7_hits_v1": float(np.mean(legacy_hits)),
        "latest_v1_v2_probability_l1": float(np.abs(q - legacy_q).sum()),
        "latest_v2_p_sha256": hashlib.sha256(q.astype("<f8").tobytes()).hexdigest(),
        "legacy_runtime_still_uses_v1": True,
        "migration_required": "separate versioned model ID and new prefrozen prospective registration",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path, default=Path("loto7.csv"))
    parser.add_argument("--out", type=Path, default=Path("loto7_agent_output/pair_context_v2_validation.json"))
    parser.add_argument("--last-n", type=int, default=DEFAULT_WINDOW)
    args = parser.parse_args()
    result = diagnostics(args.csv, args.last_n)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "version": VERSION, "data_sha256": result["data_sha256"],
        "legacy_overflow": result["int8_corrupted_cooccurrence_cells"],
        "corrected_overflow": 0, "promotion_authorized": False,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
