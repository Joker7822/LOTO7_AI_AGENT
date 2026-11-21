#!/usr/bin/env python3
"""Production-safe ranked35 combination optimizer with strong fair-null shrinkage.

Applies deterministic positive-gain swaps only among Champion-selected top 35.
Training reads preceding verified history only. Does not claim predictive skill.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence
import numpy as np
from balanced_uniform_portfolio import validate_portfolio

@dataclass(frozen=True)
class AgentConfig:
    lookback: int = 160
    half_life: float = 60.0
    prior_equivalent_draws: float = 300.0
    max_swaps: int = 18
    min_improvement: float = 1e-12


def _validate_ranking(ranking: Sequence[int]) -> None:
    if len(ranking) != 37 or any(type(n) is not int for n in ranking):
        raise ValueError("ranking requires exactly 37 integer labels")
    if sorted(ranking) != list(range(1, 38)):
        raise ValueError("ranking must contain every number 1..37 once")


def fit_pairwise_edges(history: np.ndarray, cfg: AgentConfig) -> tuple[np.ndarray, dict]:
    """Learn empirical deviations from the known fair-draw pair frequency.

    The prior is centered exactly on P(i,j both drawn) = (7/37)*(6/36).
    Shrinkage accounts for effective exponentially decayed sample size; no
    target-row observations or any model output are accessed here.
    """
    h = np.asarray(history)
    if (h.ndim != 2 or h.shape[1] != 37 or len(h) < 100
            or not np.all((h == 0) | (h == 1))
            or not np.all(h.sum(axis=1) == 7)):
        raise ValueError("combination agent requires at least 100 valid past draws")
    if (cfg.lookback < 100 or cfg.half_life <= 0
            or cfg.prior_equivalent_draws <= 0 or cfg.max_swaps < 0):
        raise ValueError("invalid combination agent training configuration")
    past = h[-cfg.lookback:].astype(float, copy=False)
    ages = np.arange(len(past) - 1, -1, -1, dtype=float)
    weight = np.power(0.5, ages / cfg.half_life)
    n_eff = float(weight.sum() ** 2 / np.sum(weight ** 2))
    posterior_weight = n_eff / (n_eff + cfg.prior_equivalent_draws)
    observed_pair = past.T @ (past * weight[:, None]) / weight.sum()
    fair_pair = (7 * 6) / (37 * 36)
    edge = (observed_pair - fair_pair) * posterior_weight
    edge = 0.5 * (edge + edge.T)
    np.fill_diagonal(edge, 0.0)
    if edge.shape != (37, 37) or not np.all(np.isfinite(edge)):
        raise RuntimeError("non-finite combination agent pair edges")
    return edge, {
        "lookback_used": len(past),
        "effective_sample_size": n_eff,
        "posterior_data_weight": posterior_weight,
        "fair_draw_pair_probability": fair_pair,
        "pair_edge_frobenius_norm": float(np.linalg.norm(edge)),
    }


def pair_objective(groups: np.ndarray, edge: np.ndarray) -> float:
    total = 0.0
    for group in groups:
        square = edge[np.ix_(group, group)]
        total += float(np.triu(square, 1).sum())
    return total


def optimize_partition(
    ranking: Sequence[int], edges: np.ndarray, cfg: AgentConfig,
) -> tuple[list[tuple[int, ...]], dict]:
    """Find bounded positive-gain cross-group swaps with stable tie handling.

    This improves *past-data affinity only*, never proof of future wins.
    """
    _validate_ranking(ranking)
    e = np.asarray(edges, dtype=float)
    if e.shape != (37, 37) or not np.all(np.isfinite(e)):
        raise ValueError("pair matrix must contain finite 37x37 scores")
    if not np.allclose(e, e.T, atol=1e-12, rtol=0):
        raise ValueError("pair matrix must be symmetric")
    if not np.allclose(np.diag(e), 0, atol=1e-12, rtol=0):
        raise ValueError("pair matrix diagonal must be zero")
    if cfg.max_swaps < 0 or cfg.min_improvement < 0:
        raise ValueError("invalid optimizer limits")
    # Positions are rank slots; groups are seven-slot blocks.
    assigned = np.asarray(ranking[:35], dtype=int) - 1
    original = assigned.copy()
    group_ids = np.arange(35) // 7
    pi, pj = np.triu_indices(35, k=1)
    mask = group_ids[pi] != group_ids[pj]
    pi, pj = pi[mask], pj[mask]
    gi, gj = group_ids[pi], group_ids[pj]
    before = pair_objective(original.reshape(5,7), e)
    moves = []
    for _ in range(cfg.max_swaps):
        group_sums = e[:, assigned.reshape(5, 7)].sum(axis=2)
        ai, aj = assigned[pi], assigned[pj]
        # When swapping ai from group gi and aj from group gj:
        # delta = sum over the two affected group-pair edges only.
        deltas = (
            group_sums[aj, gi] - group_sums[ai, gi]
            + group_sums[ai, gj] - group_sums[aj, gj]
            - 2.0 * e[ai, aj]
        )
        best = int(np.argmax(deltas))
        delta = float(deltas[best])
        if delta <= cfg.min_improvement:
            break
        i, j = int(pi[best]), int(pj[best])
        number_i, number_j = int(assigned[i])+1, int(assigned[j])+1
        assigned[i], assigned[j] = assigned[j], assigned[i]
        moves.append({
            "from_group": i // 7 + 1, "to_group": j // 7 + 1,
            "swapped_number_a": number_i, "swapped_number_b": number_j,
            "training_objective_delta": delta,
        })
    after = pair_objective(assigned.reshape(5, 7), e)
    if after + 1e-9 < before:
        raise AssertionError("combination agent decreased its training objective")
    output = [
        tuple(sorted(int(n)+1 for n in group))
        for group in assigned.reshape(5, 7)
    ]
    validate_portfolio(output)
    if sorted(n for row in output for n in row) != sorted(ranking[:35]):
        raise AssertionError("combination agent changed the selected 35 numbers")
    return output, {
        "training_objective_before": before,
        "training_objective_after": after,
        "training_objective_gain": after-before,
        "swap_count": len(moves),
        "moves": moves,
    }


def candidate_from_history(
    history: np.ndarray, ranking: Sequence[int], cfg: AgentConfig,
) -> tuple[list[tuple[int, ...]], dict]:
    edges, learned = fit_pairwise_edges(history, cfg)
    tickets, optimized = optimize_partition(ranking, edges, cfg)
    return tickets, {**learned, **optimized}


