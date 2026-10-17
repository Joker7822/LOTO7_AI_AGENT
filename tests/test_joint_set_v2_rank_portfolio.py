#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import numpy as np

from joint_set_v2_model import ForecastBundle, expected_utility_portfolio, project_inclusion
from joint_set_v2_rank_portfolio import (
    RankPolicy,
    build_policy_portfolios,
    candidate_policies,
    robust_policy_score,
    select_policy,
)


def make_bundle() -> ForecastBundle:
    raw = project_inclusion(np.linspace(-0.15, 0.55, 37))
    calibrated = project_inclusion(0.35 * raw + 0.65 * np.full(37, 7.0 / 37.0))
    return ForecastBundle(
        inclusion_p=calibrated,
        raw_inclusion_p=raw,
        pair_matrix=np.zeros((37, 37), dtype=float),
        regime=np.array([0.8, 0.15, 0.05], dtype=float),
        gate=0.35,
        effective_pair_strength=0.0,
        gate_diagnostics={"n": 60.0, "z": 1.0, "quality_mean": 0.01},
    )


def test_unrestricted_reproduces_existing_optimizer() -> None:
    bundle = make_bundle()
    seed = 876543
    expected, expected_diag = expected_utility_portfolio(
        bundle, seed=seed, scenarios=96, candidate_count=40
    )
    got = build_policy_portfolios(
        bundle, candidate_policies(), seed=seed, scenarios=96, candidate_count=40
    )["unrestricted"]
    assert got["tickets"] == expected
    assert abs(got["diagnostics"]["expected_utility"] - expected_diag["expected_utility"]) < 1e-12


def test_rank_policies_enforce_ticket_exposure() -> None:
    bundle = make_bundle()
    result = build_policy_portfolios(
        bundle, candidate_policies(), seed=99127, scenarios=96, candidate_count=48
    )
    order = np.argsort(bundle.raw_inclusion_p)[::-1]
    top7 = set((order[:7] + 1).tolist())
    top10 = set((order[:10] + 1).tolist())
    by_name = {p.name: p for p in candidate_policies()}
    assert "unrestricted" in result
    for name, payload in result.items():
        policy = by_name[name]
        for ticket in payload["tickets"]:
            values = set(ticket)
            assert len(values & top7) >= policy.min_top7_per_ticket
            assert len(values & top10) >= policy.min_top10_per_ticket


def test_negative_prior_edge_keeps_unrestricted() -> None:
    policies = [RankPolicy("unrestricted"), RankPolicy("top7-ge2", 2, 2)]
    histories = {
        "unrestricted": [{"delta_vs_unrestricted": 0.0}] * 60,
        "top7-ge2": [{"delta_vs_unrestricted": -0.2}] * 60,
    }
    selected, score = select_policy(policies, histories, [p.name for p in policies], 60)
    assert selected.name == "unrestricted"
    assert score == 0.0


def test_positive_stable_prior_edge_can_select_rank_policy() -> None:
    policies = [RankPolicy("unrestricted"), RankPolicy("top7-ge2", 2, 2)]
    histories = {
        "unrestricted": [{"delta_vs_unrestricted": 0.0}] * 60,
        "top7-ge2": [{"delta_vs_unrestricted": 0.15}] * 60,
    }
    selected, score = select_policy(policies, histories, [p.name for p in policies], 60)
    assert selected.name == "top7-ge2"
    assert score > 0.0


def test_insufficient_history_cannot_activate_rank_policy() -> None:
    rows = [{"delta_vs_unrestricted": 10.0}] * 29
    assert robust_policy_score(rows, 120) < -1e8


def test_portfolios_are_deterministic() -> None:
    bundle = make_bundle()
    a = build_policy_portfolios(bundle, candidate_policies(), seed=4411, scenarios=64, candidate_count=32)
    b = build_policy_portfolios(bundle, candidate_policies(), seed=4411, scenarios=64, candidate_count=32)
    assert a == b
