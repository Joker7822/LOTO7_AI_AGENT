#!/usr/bin/env python3
"""Fair-lottery five-ticket geometry: exact null scores and disjoint coverage.

Research-only. This is NOT a predictor of which seven numbers will be drawn.
For fair 7-of-37, five distinct tickets have the same aggregate 1st-prize
probability regardless of their geometry. Disjoint tickets can improve the
chance of a >=3-hit ticket and the diagnostic max-hit score.
"""
from __future__ import annotations

import itertools
import math

import numpy as np

NUMBERS = 37
PICKS = 7
TICKETS = 5
UNIVERSE_SIZE = math.comb(NUMBERS, PICKS)
VERSION = "fair-uniform-disjoint-five-ticket-geometry-v1"


def disjoint_portfolio(seed: int) -> list[tuple[int, ...]]:
    """Sample 35 distinct numbers, split into five nonoverlapping tickets.

    All 37 labels are exchangeable under the null, so a seeded uniform
    permutation avoids anchoring outcomes to historically lucky numbers.
    """
    if not isinstance(seed, (int, np.integer)):
        raise TypeError("seed must be integer")
    rng = np.random.default_rng(int(seed))
    numbers = rng.permutation(NUMBERS) + 1
    tickets = [
        tuple(sorted(int(n) for n in ticket))
        for ticket in numbers[:TICKETS * PICKS].reshape(TICKETS, PICKS)
    ]
    validate_portfolio(tickets)
    return tickets


def validate_portfolio(portfolio: list[tuple[int, ...]]) -> None:
    if len(portfolio) != TICKETS:
        raise ValueError("five tickets required")
    seen = set()
    for ticket in portfolio:
        if (len(ticket) != PICKS or len(set(ticket)) != PICKS or
                any(not isinstance(n, (int, np.integer)) or n < 1 or n > NUMBERS
                    for n in ticket)):
            raise ValueError("invalid ticket")
        if seen.intersection(ticket):
            raise ValueError("tickets must not overlap")
        seen.update(ticket)
    if len(seen) != TICKETS * PICKS:
        raise ValueError("expected coverage of exactly 35 numbers")


def exact_disjoint_null() -> dict[str, float | int]:
    """Exact hypergeometric enumeration for 5 blocks of 7 plus 2 omitted.

    Each five-component hit vector (k1..k5) with 0<=ki<=7 and
    r = 7-sum(ki) in [0,2] has:
      weight = C(2,r) * PRODUCT_i C(7,ki)
    equally likely seven-number combinations. No RNG or historical data.
    """
    numerator = {
        "max_hits": 0,
        "total_hits": 0,
        "ge3": 0,
        "ge4": 0,
        "score_cents": 0,
        "probability_mass": 0,
    }
    for counts in itertools.product(range(PICKS + 1), repeat=TICKETS):
        chosen = sum(counts)
        omitted = PICKS - chosen
        if not 0 <= omitted <= NUMBERS - TICKETS * PICKS:
            continue
        weight = math.comb(2, omitted)
        for k in counts:
            weight *= math.comb(PICKS, k)
        maximum = max(counts)
        ge3 = int(maximum >= 3)
        ge4 = int(maximum >= 4)
        # Existing composite score: maximum + 0.35 ge3 + 0.75 ge4
        # + 0.10 average hit count = (... + 2 * total_hits)/100.
        numerator["max_hits"] += weight * maximum
        numerator["total_hits"] += weight * chosen
        numerator["ge3"] += weight * ge3
        numerator["ge4"] += weight * ge4
        numerator["score_cents"] += weight * (
            100 * maximum + 35 * ge3 + 75 * ge4 + 2 * chosen)
        numerator["probability_mass"] += weight
    if numerator["probability_mass"] != UNIVERSE_SIZE:
        raise ArithmeticError("exact disjoint null probability does not sum to one")
    d = UNIVERSE_SIZE
    return {
        "exact": True,
        "total_possible_draws": d,
        "covered_distinct_numbers": TICKETS * PICKS,
        "max_hits": numerator["max_hits"] / d,
        "mean_hits": numerator["total_hits"] / (TICKETS * d),
        "ge3": numerator["ge3"] / d,
        "ge4": numerator["ge4"] / d,
        "score": numerator["score_cents"] / (100 * d),
        "any_first_prize_probability": TICKETS / d,
    }


def exact_independent_random_null() -> dict[str, float | int]:
    """Independent uniform random tickets, with replacement, analytical null.

    This is the mathematically exact independent-sampling comparator, not a
    claim that 5 distinct lottery tickets are independent. Duplicate tickets
    have a tiny nonzero probability; disjoint tickets are always distinct.
    """
    denom = UNIVERSE_SIZE
    pmf = [
        math.comb(PICKS, k) * math.comb(NUMBERS - PICKS, PICKS - k) / denom
        for k in range(PICKS + 1)
    ]
    cdf = np.cumsum(pmf)
    expected_max = sum(1.0 - float(cdf[k - 1]) ** TICKETS
                       for k in range(1, PICKS + 1))
    ge3 = 1.0 - float(cdf[2]) ** TICKETS
    ge4 = 1.0 - float(cdf[3]) ** TICKETS
    mean_hits = PICKS * PICKS / NUMBERS
    return {
        "exact": True,
        "sampling": "independent_uniform_tickets_with_replacement",
        "max_hits": float(expected_max),
        "mean_hits": float(mean_hits),
        "ge3": float(ge3),
        "ge4": float(ge4),
        "score": float(expected_max + 0.35 * ge3 + 0.75 * ge4 +
                       0.10 * mean_hits),
        "any_first_prize_probability": float(
            1.0 - (1.0 - 1.0 / denom) ** TICKETS
        ),
    }


def theory_report() -> dict:
    disjoint = exact_disjoint_null()
    random = exact_independent_random_null()
    return {
        "version": VERSION,
        "assumption": "independent_conditionally_fair_seven_of_37_drawing",
        "portfolio_strategy": "five_pairwise_disjoint_tickets_covering_35_numbers",
        "disjoint_exact": disjoint,
        "independent_random_exact": random,
        "score_gain_vs_independent_random": (
            disjoint["score"] - random["score"]
        ),
        "ge3_gain_vs_independent_random": (
            disjoint["ge3"] - random["ge3"]
        ),
        "no_predictive_signal_claim": True,
        "production_changed": False,
        "promotion_authorized": False,
        "note": (
            "Geometry can improve a >=3-hit event without predicting number "
            "frequencies or increasing the first-prize probability of five "
            "distinct tickets. The independent comparator samples with "
            "replacement and permits extremely rare duplicates."
        ),
    }
