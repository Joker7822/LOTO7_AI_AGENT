#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from typing import Dict, List, Sequence, Tuple

import numpy as np

import separated_optimizer as so
from loto7_evolving_agent import N_NUMBERS, PICKS, expert_probabilities

MODEL_VERSION = "regularized-signal-meta-v1"
UNIFORM = np.full(N_NUMBERS, 1.0 / N_NUMBERS, dtype=float)


@dataclass(frozen=True)
class MetaConfig:
    name: str
    learning_rate: float
    l2: float
    forget: float
    uniform_mix: float
    max_abs_weight: float = 3.0

    def version(self) -> str:
        payload = json.dumps(asdict(self), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return f"{self.name}-{hashlib.sha256(payload.encode()).hexdigest()[:10]}"


# Fixed, deliberately small family. Historical results never mutate this family.
PREDECLARED_CONFIGS: Tuple[MetaConfig, ...] = (
    MetaConfig("meta-conservative", learning_rate=0.025, l2=0.030, forget=0.9995, uniform_mix=0.35),
    MetaConfig("meta-balanced", learning_rate=0.050, l2=0.020, forget=0.9990, uniform_mix=0.25),
    MetaConfig("meta-adaptive", learning_rate=0.085, l2=0.025, forget=0.9975, uniform_mix=0.20),
)


def _standardize_columns(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    centered = x - x.mean(axis=0, keepdims=True)
    sd = centered.std(axis=0, keepdims=True)
    sd = np.where(sd < 1e-9, 1.0, sd)
    z = centered / sd
    return np.clip(z, -4.0, 4.0)


def _gap_ratio(hist: np.ndarray) -> np.ndarray:
    t = len(hist)
    gap_now = np.zeros(N_NUMBERS, dtype=float)
    mean_gap = np.full(N_NUMBERS, N_NUMBERS / PICKS, dtype=float)
    for j in range(N_NUMBERS):
        idx = np.flatnonzero(hist[:, j])
        gap_now[j] = (t - 1 - idx[-1]) if len(idx) else t
        if len(idx) >= 3:
            mean_gap[j] = float(np.diff(idx).mean())
    return gap_now / np.maximum(mean_gap, 1e-9)


def feature_matrix(hist: np.ndarray) -> Tuple[np.ndarray, List[str]]:
    """Create target-time features from history only.

    Each column is standardized across the 37 numbers at the current target time.
    This makes the meta learner combine *relative* number signals and avoids a free
    global intercept (which is unidentified under a 37-way softmax anyway).
    """
    hist = np.asarray(hist, dtype=float)
    if hist.ndim != 2 or hist.shape[1] != N_NUMBERS or len(hist) < 20:
        raise ValueError("hist must be [draws, 37] with at least 20 past draws")

    experts = expert_probabilities(hist)
    cols: List[np.ndarray] = []
    names: List[str] = []
    for key, q in experts.items():
        q = np.maximum(np.asarray(q, dtype=float), 1e-15)
        cols.append(np.log(q / (1.0 / N_NUMBERS)))
        names.append(f"expert_log_{key}")

    cols.append(hist[-1].astype(float))
    names.append("was_in_last_draw")
    cols.append(_gap_ratio(hist))
    names.append("gap_ratio")

    short = hist[-min(12, len(hist)):].mean(axis=0)
    medium = hist[-min(48, len(hist)):].mean(axis=0)
    cols.append(short - medium)
    names.append("freq_12_minus_48")

    x = np.column_stack(cols)
    return _standardize_columns(x), names


def softmax(scores: np.ndarray) -> np.ndarray:
    scores = np.asarray(scores, dtype=float)
    z = np.clip(scores - float(np.max(scores)), -40.0, 0.0)
    e = np.exp(z)
    return e / e.sum()


def predict_from_features(features: np.ndarray, weights: np.ndarray, uniform_mix: float) -> np.ndarray:
    features = np.asarray(features, dtype=float)
    weights = np.asarray(weights, dtype=float)
    if features.ndim != 2 or weights.shape != (features.shape[1],):
        raise ValueError("feature/weight shape mismatch")
    base = softmax(features @ weights)
    mix = min(0.95, max(0.0, float(uniform_mix)))
    q = (1.0 - mix) * base + mix * UNIFORM
    return q / q.sum()


def update_weights(features: np.ndarray, actual_idx: Sequence[int], weights: np.ndarray,
                   config: MetaConfig) -> np.ndarray:
    """One online cross-entropy update after the target result is observed."""
    features = np.asarray(features, dtype=float)
    w = np.asarray(weights, dtype=float)
    base = softmax(features @ w)
    y = np.zeros(N_NUMBERS, dtype=float)
    idx = np.asarray(list(actual_idx), dtype=int)
    if len(idx) != PICKS:
        raise ValueError("actual_idx must contain exactly seven indices")
    y[idx] = 1.0 / PICKS
    grad = features.T @ (base - y) + float(config.l2) * w
    updated = float(config.forget) * w - float(config.learning_rate) * grad
    return np.clip(updated, -float(config.max_abs_weight), float(config.max_abs_weight))


def precompute_features(x: np.ndarray, min_train: int) -> Tuple[List[np.ndarray], List[str]]:
    x = np.asarray(x, dtype=float)
    if len(x) <= min_train:
        raise ValueError("not enough draws for walk-forward replay")
    matrices: List[np.ndarray] = []
    names: List[str] = []
    for t in range(min_train, len(x)):
        mat, current_names = feature_matrix(x[:t])
        if names and current_names != names:
            raise RuntimeError("feature schema changed during replay")
        names = current_names
        matrices.append(mat)
    return matrices, names


def replay_config(x: np.ndarray, config: MetaConfig, min_train: int = 100,
                  features: Sequence[np.ndarray] | None = None) -> Dict[str, object]:
    x = np.asarray(x, dtype=float)
    if features is None:
        features, names = precompute_features(x, min_train)
    else:
        features = list(features)
        _, names = feature_matrix(x[:min_train])
    if len(features) != len(x) - min_train:
        raise ValueError("precomputed feature count mismatch")

    weights = np.zeros(np.asarray(features[0]).shape[1], dtype=float)
    rows: List[Dict[str, float]] = []
    qs: List[np.ndarray] = []
    weight_norms: List[float] = []
    for offset, t in enumerate(range(min_train, len(x))):
        f = np.asarray(features[offset], dtype=float)
        q = predict_from_features(f, weights, config.uniform_mix)
        actual_idx = np.flatnonzero(x[t])
        rows.append(so.signal_row(q, actual_idx))
        qs.append(q.copy())
        weight_norms.append(float(np.linalg.norm(weights)))
        weights = update_weights(f, actual_idx, weights, config)

    windows: Dict[str, Dict[str, float]] = {"full": so.aggregate_signal(rows)}
    for n in (120, 60, 30):
        windows[str(n)] = so.aggregate_signal(rows[-min(n, len(rows)):])
    return {
        "model_version": MODEL_VERSION,
        "config": asdict(config),
        "version": config.version(),
        "feature_names": names,
        "windows": windows,
        "rows": rows,
        "qs": qs,
        "final_weights": {names[i]: float(weights[i]) for i in range(len(names))},
        "max_weight_abs": float(np.max(np.abs(weights))),
        "mean_weight_norm": float(np.mean(weight_norms)),
    }


def selector_score(rows: Sequence[Dict[str, float]]) -> float:
    """Signal-only model-selection score using already-scored past predictions."""
    if not rows:
        return -1e9
    recent = so.aggregate_signal(rows[-min(120, len(rows)):])
    full = so.aggregate_signal(rows)
    # Log/Brier dominate. Top-7 is deliberately a small secondary term.
    return float(
        0.60 * recent["log_edge_vs_uniform"]
        + 0.25 * full["log_edge_vs_uniform"]
        + 18.0 * (0.60 * recent["brier_edge_vs_uniform"] + 0.40 * full["brier_edge_vs_uniform"])
        + 0.03 * recent["top7_hits_delta_vs_uniform"]
    )


def nested_select(results: Sequence[Dict[str, object]], last_n: int = 120) -> Dict[str, object]:
    if not results:
        raise ValueError("results must be non-empty")
    lengths = {len(r["rows"]) for r in results}
    if len(lengths) != 1:
        raise ValueError("all replay results must have the same row count")
    total = lengths.pop()
    start = max(0, total - int(last_n))
    selected_rows: List[Dict[str, float]] = []
    selected_qs: List[np.ndarray] = []
    selected_versions: List[str] = []
    counts: Dict[str, int] = {}

    for i in range(start, total):
        # Crucial: selection for row i can inspect only rows strictly before i.
        scored = []
        for r in results:
            prior_rows = r["rows"][:i]
            scored.append((selector_score(prior_rows), str(r["version"]), r))
        _, version, chosen = max(scored, key=lambda z: (z[0], z[1]))
        selected_rows.append(chosen["rows"][i])
        selected_qs.append(np.asarray(chosen["qs"][i], dtype=float))
        selected_versions.append(version)
        counts[version] = counts.get(version, 0) + 1

    return {
        "last_n": len(selected_rows),
        "start_index": start,
        "rows": selected_rows,
        "qs": selected_qs,
        "selected_versions": selected_versions,
        "selected_counts": counts,
        "signal": so.aggregate_signal(selected_rows),
    }


def block_bootstrap_mean_ci(values: Sequence[float], seed: int, reps: int = 4000,
                            block_len: int = 8) -> Dict[str, float]:
    x = np.asarray(values, dtype=float)
    n = len(x)
    if n == 0:
        return {"mean": 0.0, "low95": 0.0, "high95": 0.0, "block_len": float(block_len), "reps": float(reps)}
    b = max(1, min(int(block_len), n))
    starts = np.arange(max(1, n - b + 1))
    blocks = [x[s:s + b] for s in starts]
    rng = np.random.default_rng(int(seed))
    means = np.empty(int(reps), dtype=float)
    need = int(math.ceil(n / b))
    for i in range(int(reps)):
        picked = rng.integers(0, len(blocks), size=need)
        sample = np.concatenate([blocks[j] for j in picked])[:n]
        means[i] = float(sample.mean())
    return {
        "mean": float(x.mean()),
        "low95": float(np.quantile(means, 0.025)),
        "high95": float(np.quantile(means, 0.975)),
        "block_len": float(b),
        "reps": float(reps),
    }
