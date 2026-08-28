#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from typing import Dict, List, Sequence, Tuple

import numpy as np

N_NUMBERS = 37
PICKS = 7
UNIFORM_Q = np.full(N_NUMBERS, 1.0 / N_NUMBERS, dtype=float)
UNIFORM_TOP7_HITS = PICKS * PICKS / N_NUMBERS
UNIFORM_ACTUAL_MASS = PICKS / N_NUMBERS
UNIFORM_LOG_PROB = math.log(1.0 / N_NUMBERS)
MODEL_VERSION = "joint-set-research-v1"


@dataclass(frozen=True)
class JointSetConfig:
    name: str
    marginal_uniform_mix: float = 0.28
    pair_rank: int = 4
    pair_half_life: float = 80.0
    pair_strength: float = 0.20
    pair_shrinkage: float = 80.0
    regime_strength: float = 0.30
    gate_window: int = 90
    gate_ceiling: float = 0.88
    gate_slope: float = 1.25
    gate_center_z: float = 0.75
    metadata_strength: float = 0.10
    portfolio_candidates: int = 96
    portfolio_scenarios: int = 512

    def version(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return f"{self.name}-{hashlib.sha256(payload.encode()).hexdigest()[:10]}"


def candidate_configs() -> List[JointSetConfig]:
    """Small, predeclared family. Null calibration uses exactly the same family."""
    return [
        JointSetConfig(
            name="joint-conservative", marginal_uniform_mix=0.36, pair_rank=3,
            pair_half_life=110.0, pair_strength=0.11, pair_shrinkage=120.0,
            regime_strength=0.20, gate_ceiling=0.72, metadata_strength=0.06,
        ),
        JointSetConfig(
            name="joint-balanced", marginal_uniform_mix=0.28, pair_rank=4,
            pair_half_life=80.0, pair_strength=0.20, pair_shrinkage=80.0,
            regime_strength=0.30, gate_ceiling=0.88, metadata_strength=0.10,
        ),
        JointSetConfig(
            name="joint-structural", marginal_uniform_mix=0.26, pair_rank=5,
            pair_half_life=65.0, pair_strength=0.30, pair_shrinkage=65.0,
            regime_strength=0.28, gate_ceiling=0.88, metadata_strength=0.12,
        ),
        JointSetConfig(
            name="joint-fast-regime", marginal_uniform_mix=0.31, pair_rank=4,
            pair_half_life=48.0, pair_strength=0.18, pair_shrinkage=95.0,
            regime_strength=0.48, gate_window=60, gate_ceiling=0.82,
            metadata_strength=0.08,
        ),
        JointSetConfig(
            name="joint-slow-regime", marginal_uniform_mix=0.30, pair_rank=4,
            pair_half_life=140.0, pair_strength=0.17, pair_shrinkage=110.0,
            regime_strength=0.16, gate_window=120, gate_ceiling=0.84,
            metadata_strength=0.08,
        ),
    ]


def _softmax(logits: np.ndarray) -> np.ndarray:
    z = np.asarray(logits, dtype=float)
    z = z - np.max(z)
    e = np.exp(np.clip(z, -60.0, 60.0))
    s = float(e.sum())
    return e / s if s > 0 else UNIFORM_Q.copy()


def _zscore(v: np.ndarray) -> np.ndarray:
    arr = np.asarray(v, dtype=float)
    sd = float(arr.std())
    if sd < 1e-12:
        return np.zeros_like(arr)
    return (arr - arr.mean()) / sd


def _weighted_frequency(hist: np.ndarray, half_life: float) -> np.ndarray:
    h = np.asarray(hist, dtype=float)
    ages = np.arange(len(h) - 1, -1, -1, dtype=float)
    w = np.power(0.5, ages / max(float(half_life), 1e-6))
    f = (h * w[:, None]).sum(axis=0)
    f += 0.35  # symmetric Dirichlet shrinkage
    return f / f.sum()


def _overdue_distribution(hist: np.ndarray) -> np.ndarray:
    h = np.asarray(hist, dtype=float)
    gaps = np.zeros(N_NUMBERS, dtype=float)
    expected = np.full(N_NUMBERS, N_NUMBERS / PICKS, dtype=float)
    for j in range(N_NUMBERS):
        idx = np.flatnonzero(h[:, j])
        gaps[j] = len(h) - 1 - idx[-1] if len(idx) else len(h)
        if len(idx) >= 4:
            expected[j] = max(1.0, float(np.diff(idx).mean()))
    return _softmax(_zscore(gaps / expected) / 1.8)


def _momentum_distribution(hist: np.ndarray) -> np.ndarray:
    h = np.asarray(hist, dtype=float)
    short = h[-min(18, len(h)):].mean(axis=0)
    long = h[-min(120, len(h)):].mean(axis=0)
    return _softmax(_zscore(short - long) / 1.8)


def _shift_observation(hist: np.ndarray) -> float:
    h = np.asarray(hist, dtype=float)
    if len(h) < 45:
        return 0.0
    recent = h[-10:].mean(axis=0)
    prior = h[-45:-10].mean(axis=0)
    return float(np.linalg.norm(recent - prior))


def regime_posterior(hist: np.ndarray) -> np.ndarray:
    """Three-state prior-only HMM filter: stable / shift / volatile."""
    h = np.asarray(hist, dtype=float)
    if len(h) < 65:
        return np.array([0.70, 0.20, 0.10], dtype=float)
    start = max(45, len(h) - 140)
    obs = np.array([_shift_observation(h[:t]) for t in range(start, len(h) + 1)], dtype=float)
    if len(obs) < 4 or float(obs.std()) < 1e-12:
        return np.array([0.70, 0.20, 0.10], dtype=float)
    z = (obs - obs.mean()) / obs.std()
    transition = np.array([
        [0.92, 0.07, 0.01],
        [0.12, 0.82, 0.06],
        [0.05, 0.15, 0.80],
    ], dtype=float)
    means = np.array([-0.65, 0.25, 1.15], dtype=float)
    sigma = 0.85
    p = np.array([0.70, 0.20, 0.10], dtype=float)
    for value in z:
        p = p @ transition
        likelihood = np.exp(-0.5 * ((value - means) / sigma) ** 2)
        p *= likelihood
        p /= max(float(p.sum()), 1e-15)
    return p


def dynamic_marginal(hist: np.ndarray, cfg: JointSetConfig, regime: np.ndarray) -> np.ndarray:
    h = np.asarray(hist, dtype=float)
    f8 = _weighted_frequency(h, 8.0)
    f20 = _weighted_frequency(h, 20.0)
    f50 = _weighted_frequency(h, 50.0)
    f120 = _weighted_frequency(h, 120.0)
    overdue = _overdue_distribution(h)
    momentum = _momentum_distribution(h)

    stable, shift, volatile = [float(x) for x in regime]
    short_boost = cfg.regime_strength * (shift + 0.35 * volatile)
    long_boost = cfg.regime_strength * stable
    weights = np.array([
        0.20 + 0.25 * short_boost,
        0.23 + 0.15 * short_boost,
        0.19 + 0.10 * long_boost,
        0.14 + 0.20 * long_boost,
        0.11,
        0.13 + 0.20 * short_boost,
    ], dtype=float)
    weights /= weights.sum()
    parts = [f8, f20, f50, f120, overdue, momentum]
    q = sum(float(weights[i]) * parts[i] for i in range(len(parts)))
    q /= q.sum()
    uniform_mix = min(0.75, max(0.0, cfg.marginal_uniform_mix + 0.16 * volatile))
    q = (1.0 - uniform_mix) * q + uniform_mix * UNIFORM_Q
    return q / q.sum()


def low_rank_pair_matrix(hist: np.ndarray, cfg: JointSetConfig) -> np.ndarray:
    h = np.asarray(hist, dtype=float)
    window = h[-min(260, len(h)):]
    n = len(window)
    if n < 35:
        return np.zeros((N_NUMBERS, N_NUMBERS), dtype=float)
    ages = np.arange(n - 1, -1, -1, dtype=float)
    w = np.power(0.5, ages / max(cfg.pair_half_life, 1e-6))
    sw = float(w.sum())
    p = (window * w[:, None]).sum(axis=0) / sw
    centered = window - p[None, :]
    cov = (centered * w[:, None]).T @ centered / sw
    scale = np.sqrt(np.maximum(p * (1.0 - p), 1e-5))
    corr = cov / np.maximum(scale[:, None] * scale[None, :], 1e-5)
    np.fill_diagonal(corr, 0.0)
    n_eff = float(sw * sw / max(float(np.sum(w * w)), 1e-12))
    corr *= n_eff / (n_eff + max(cfg.pair_shrinkage, 1e-6))
    vals, vecs = np.linalg.eigh((corr + corr.T) * 0.5)
    rank = max(1, min(int(cfg.pair_rank), N_NUMBERS - 1))
    idx = np.argsort(np.abs(vals))[-rank:]
    low = (vecs[:, idx] * vals[idx][None, :]) @ vecs[:, idx].T
    low = (low + low.T) * 0.5
    np.fill_diagonal(low, 0.0)
    off = low[~np.eye(N_NUMBERS, dtype=bool)]
    sd = float(off.std()) if len(off) else 0.0
    if sd > 1e-12:
        low = np.clip(low / sd, -3.0, 3.0)
    else:
        low[:] = 0.0
    return low


def signal_metrics(q: np.ndarray, actual_idx: np.ndarray) -> Dict[str, float]:
    prob = np.maximum(np.asarray(q, dtype=float), 1e-15)
    prob /= prob.sum()
    actual = np.asarray(actual_idx, dtype=int)
    y = np.zeros(N_NUMBERS, dtype=float)
    y[actual] = 1.0 / PICKS
    top = set(np.argsort(prob)[-PICKS:].tolist())
    aset = set(actual.tolist())
    uniform_brier = float(np.sum((UNIFORM_Q - y) ** 2))
    return {
        "top7_hits": float(len(top & aset)),
        "actual_mass": float(prob[actual].sum()),
        "log_edge": float(np.mean(np.log(prob[actual])) - UNIFORM_LOG_PROB),
        "brier_edge": float(uniform_brier - np.sum((prob - y) ** 2)),
    }


def signal_quality(row: Dict[str, float]) -> float:
    return float(
        row["log_edge"]
        + 25.0 * row["brier_edge"]
        + 2.0 * (row["actual_mass"] - UNIFORM_ACTUAL_MASS)
        + 0.10 * (row["top7_hits"] - UNIFORM_TOP7_HITS)
    )


def dynamic_uniform_gate(
    calibration_rows: Sequence[Dict[str, float]],
    regime: np.ndarray,
    cfg: JointSetConfig,
) -> Tuple[float, Dict[str, float]]:
    rows = list(calibration_rows[-max(20, int(cfg.gate_window)):])
    if len(rows) < 20:
        return 0.10, {"n": float(len(rows)), "z": 0.0, "quality_mean": 0.0}
    values = np.array([signal_quality(r) for r in rows], dtype=float)
    mean = float(values.mean())
    sd = float(values.std(ddof=1)) if len(values) > 1 else 0.0
    se = sd / math.sqrt(len(values)) if sd > 1e-12 else 1.0
    z = mean / max(se, 1e-8)
    logistic = 1.0 / (1.0 + math.exp(-cfg.gate_slope * (z - cfg.gate_center_z)))
    gate = cfg.gate_ceiling * logistic
    mean_log = float(np.mean([r["log_edge"] for r in rows]))
    mean_brier = float(np.mean([r["brier_edge"] for r in rows]))
    if mean_log <= 0.0:
        gate *= 0.65
    if mean_brier <= 0.0:
        gate *= 0.55
    volatile = float(regime[2])
    gate *= max(0.35, 1.0 - 0.55 * volatile)
    if mean_log < 0.0 and mean_brier < 0.0 and z < -0.5:
        gate = 0.0
    gate = float(np.clip(gate, 0.0, cfg.gate_ceiling))
    return gate, {
        "n": float(len(rows)), "z": float(z), "quality_mean": mean,
        "mean_log_edge": mean_log, "mean_brier_edge": mean_brier,
    }


@dataclass
class ForecastBundle:
    q: np.ndarray
    raw_q: np.ndarray
    pair_matrix: np.ndarray
    regime: np.ndarray
    gate: float
    effective_pair_strength: float
    gate_diagnostics: Dict[str, float]
    metadata_diagnostics: Dict[str, float]


def forecast(
    hist: np.ndarray,
    cfg: JointSetConfig,
    calibration_rows: Sequence[Dict[str, float]],
    metadata_adjustment: np.ndarray | None = None,
    metadata_diagnostics: Dict[str, float] | None = None,
) -> ForecastBundle:
    regime = regime_posterior(hist)
    marginal = dynamic_marginal(hist, cfg, regime)
    pair = low_rank_pair_matrix(hist, cfg)
    pair_node = _zscore(pair @ marginal)
    pair_scale = 0.70 + 0.55 * float(regime[1]) - 0.35 * float(regime[2])
    logits = np.log(np.maximum(marginal, 1e-15)) + cfg.pair_strength * pair_scale * pair_node
    md_diag = dict(metadata_diagnostics or {"active": 0.0, "coverage": 0.0, "norm": 0.0})
    if metadata_adjustment is not None:
        adj = np.asarray(metadata_adjustment, dtype=float)
        if adj.shape == (N_NUMBERS,) and np.any(np.abs(adj) > 1e-12):
            logits += cfg.metadata_strength * adj
    raw_q = _softmax(logits)
    gate, gate_diag = dynamic_uniform_gate(calibration_rows, regime, cfg)
    q = (1.0 - gate) * UNIFORM_Q + gate * raw_q
    q /= q.sum()
    effective_pair_strength = float(gate * cfg.pair_strength * pair_scale)
    return ForecastBundle(
        q=q, raw_q=raw_q, pair_matrix=pair, regime=regime, gate=gate,
        effective_pair_strength=effective_pair_strength,
        gate_diagnostics=gate_diag, metadata_diagnostics=md_diag,
    )


def sample_joint_sets(
    bundle: ForecastBundle,
    n_samples: int,
    seed: int,
    temperature: float = 1.0,
) -> np.ndarray:
    rng = np.random.default_rng(int(seed))
    q = np.maximum(bundle.q, 1e-15)
    pair = bundle.pair_matrix
    strength = float(bundle.effective_pair_strength)
    out = np.empty((max(0, int(n_samples)), PICKS), dtype=np.int16)
    for s in range(len(out)):
        selected: List[int] = []
        available = np.ones(N_NUMBERS, dtype=bool)
        for _ in range(PICKS):
            logits = np.log(q).copy()
            if selected and abs(strength) > 1e-12:
                logits += strength * pair[:, selected].sum(axis=1)
            logits /= max(float(temperature), 1e-6)
            logits[~available] = -1e9
            probs = _softmax(logits)
            probs[~available] = 0.0
            probs /= probs.sum()
            j = int(rng.choice(np.arange(N_NUMBERS), p=probs))
            selected.append(j)
            available[j] = False
        out[s] = np.array(sorted(j + 1 for j in selected), dtype=np.int16)
    return out


def _sets_to_binary(sets: np.ndarray) -> np.ndarray:
    arr = np.asarray(sets, dtype=int)
    out = np.zeros((len(arr), N_NUMBERS), dtype=np.int8)
    for i, row in enumerate(arr):
        out[i, np.asarray(row, dtype=int) - 1] = 1
    return out


def utility_from_max_hits(max_hits: np.ndarray) -> np.ndarray:
    h = np.asarray(max_hits, dtype=float)
    return (
        h
        + 0.35 * (h >= 3)
        + 0.75 * (h >= 4)
        + 1.50 * (h >= 5)
        + 3.00 * (h >= 6)
        + 8.00 * (h >= 7)
    )


def expected_utility_portfolio(
    bundle: ForecastBundle,
    seed: int,
    n_tickets: int = 5,
    scenarios: int | None = None,
    candidate_count: int | None = None,
    local_passes: int = 2,
) -> Tuple[List[Tuple[int, ...]], Dict[str, float]]:
    scenarios_n = int(scenarios or 512)
    candidates_n = int(candidate_count or 96)
    scenario_sets = sample_joint_sets(bundle, scenarios_n, seed=seed + 11)
    candidate_draws = sample_joint_sets(bundle, max(candidates_n * 8, 512), seed=seed + 29)
    unique, counts = np.unique(candidate_draws, axis=0, return_counts=True)
    order = np.argsort(counts)[::-1]
    candidate_sets = unique[order[:min(candidates_n, len(unique))]]
    if len(candidate_sets) < n_tickets:
        raise RuntimeError("joint sampler produced too few unique candidate tickets")

    scen_bin = _sets_to_binary(scenario_sets)
    cand_bin = _sets_to_binary(candidate_sets)
    hits = scen_bin @ cand_bin.T
    selected: List[int] = []
    current = np.zeros(len(scenario_sets), dtype=np.int8)
    for _ in range(n_tickets):
        best_idx = -1
        best_value = -1e100
        for j in range(len(candidate_sets)):
            if j in selected:
                continue
            new_max = np.maximum(current, hits[:, j])
            value = float(np.mean(utility_from_max_hits(new_max)))
            if value > best_value:
                best_value = value
                best_idx = j
        selected.append(best_idx)
        current = np.maximum(current, hits[:, best_idx])

    for _ in range(max(0, int(local_passes))):
        improved = False
        for pos in range(len(selected)):
            keep = selected[:pos] + selected[pos + 1:]
            base = np.max(hits[:, keep], axis=1) if keep else np.zeros(len(scenario_sets), dtype=np.int8)
            old_value = float(np.mean(utility_from_max_hits(np.maximum(base, hits[:, selected[pos]]))))
            best_idx = selected[pos]
            best_value = old_value
            for j in range(len(candidate_sets)):
                if j in keep:
                    continue
                value = float(np.mean(utility_from_max_hits(np.maximum(base, hits[:, j]))))
                if value > best_value + 1e-12:
                    best_value = value
                    best_idx = j
            if best_idx != selected[pos]:
                selected[pos] = best_idx
                improved = True
        if not improved:
            break

    final_max = np.max(hits[:, selected], axis=1)
    tickets = [tuple(int(v) for v in candidate_sets[j].tolist()) for j in selected]
    diagnostics = {
        "expected_utility": float(np.mean(utility_from_max_hits(final_max))),
        "expected_max_hits": float(np.mean(final_max)),
        "scenario_ge3": float(np.mean(final_max >= 3)),
        "scenario_ge4": float(np.mean(final_max >= 4)),
        "scenario_ge5": float(np.mean(final_max >= 5)),
        "scenario_count": float(len(scenario_sets)),
        "candidate_count": float(len(candidate_sets)),
    }
    return tickets, diagnostics


def portfolio_metrics(portfolio: Sequence[Sequence[int]], actual_set: set[int]) -> Dict[str, float]:
    hits = [len(set(int(v) for v in ticket) & actual_set) for ticket in portfolio]
    max_hits = float(max(hits))
    mean_hits = float(np.mean(hits))
    ge3 = float(any(h >= 3 for h in hits))
    ge4 = float(any(h >= 4 for h in hits))
    score = max_hits + 0.35 * ge3 + 0.75 * ge4 + 0.10 * mean_hits
    return {
        "max_hits": max_hits, "mean_hits": mean_hits, "ge3": ge3, "ge4": ge4,
        "score": float(score),
    }
