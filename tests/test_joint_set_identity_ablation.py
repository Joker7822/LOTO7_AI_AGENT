from __future__ import annotations

import numpy as np
import pytest

from joint_set_identity_ablation import (
    N_NUMBERS,
    ObservedRound,
    apply_label_permutation,
    empirical_upper_tail_p,
    geometry_signature,
    label_permutation,
    permutation_test,
    permute_tickets,
)
from joint_set_v2_model import portfolio_metrics


def test_label_permutation_is_deterministic_bijection() -> None:
    a = label_permutation(12345)
    b = label_permutation(12345)
    assert np.array_equal(a, b)
    assert sorted(a.tolist()) == list(range(1, N_NUMBERS + 1))


def test_permutation_preserves_ticket_geometry() -> None:
    tickets = (
        (1, 2, 3, 4, 5, 6, 7),
        (1, 8, 9, 10, 11, 12, 13),
        (2, 8, 14, 15, 16, 17, 18),
    )
    mapping = label_permutation(9876)
    permuted = permute_tickets(tickets, mapping)
    assert geometry_signature(permuted) == geometry_signature(tickets)


def test_identity_mapping_preserves_values() -> None:
    mapping = np.arange(1, N_NUMBERS + 1, dtype=int)
    values = (1, 7, 13, 37)
    assert apply_label_permutation(values, mapping) == values


def test_invalid_mapping_rejected() -> None:
    bad = np.ones(N_NUMBERS, dtype=int)
    with pytest.raises(ValueError, match="permutation"):
        apply_label_permutation((1, 2, 3), bad)


def test_empirical_upper_tail_has_plus_one_correction() -> None:
    null = np.array([0.0, 1.0, 2.0])
    assert empirical_upper_tail_p(null, 3.0) == pytest.approx(0.25)
    assert empirical_upper_tail_p(null, 1.0) == pytest.approx(0.75)


def test_permutation_test_keeps_observed_values_and_is_deterministic() -> None:
    tickets = (
        (1, 2, 3, 4, 5, 6, 7),
        (8, 9, 10, 11, 12, 13, 14),
        (15, 16, 17, 18, 19, 20, 21),
        (22, 23, 24, 25, 26, 27, 28),
        (29, 30, 31, 32, 33, 34, 35),
    )
    actual = (1, 2, 3, 8, 9, 15, 22)
    pm = portfolio_metrics(tickets, set(actual))
    row = ObservedRound(
        round_index=1,
        actual=actual,
        top7=(1, 2, 3, 4, 5, 6, 7),
        tickets=tickets,
        top7_hits=3.0,
        portfolio_score=float(pm["score"]),
    )
    a = permutation_test([row], "test", "abc123", 99, portfolio_metrics)
    b = permutation_test([row], "test", "abc123", 99, portfolio_metrics)
    assert a == b
    assert a["top7_hits"]["observed"] == 3.0
    assert a["portfolio_score"]["observed"] == pytest.approx(float(pm["score"]))
    assert 0.0 < a["top7_hits"]["empirical_upper_tail_p"] <= 1.0
    assert 0.0 < a["portfolio_score"]["empirical_upper_tail_p"] <= 1.0
