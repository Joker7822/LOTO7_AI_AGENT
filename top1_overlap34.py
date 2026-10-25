#!/usr/bin/env python3
"""Research-only 34-number geometry with exactly one shared anchor in two tickets.

The anchor may be supplied by an earlier-history signal, but a historical
ranking is not evidence that its future lottery inclusion probability is high.
Never changes the locked 35-number candidate or its prospective registry.
"""
from __future__ import annotations

import itertools
import math

import numpy as np

from balanced_uniform_portfolio import (
    NUMBERS, PICKS, TICKETS, UNIVERSE_SIZE, exact_disjoint_null,
)

VERSION = "legacy-top1-two-tickets-34-v1"
COVERAGE = 34
COMMON_COPIES = 2


def validate_tickets(tickets: list[tuple[int, ...]], top1: int) -> None:
    """Exactly the first two tickets share top1; no other number overlaps."""
    if not isinstance(top1, (int, np.integer)) or not 1 <= int(top1) <= NUMBERS:
        raise ValueError("top1 must be a number from 1 to 37")
    if len(tickets) != TICKETS:
        raise ValueError("exactly five tickets are required")
    occurrences: dict[int, int] = {}
    for ticket in tickets:
        if (len(ticket) != PICKS or len(set(ticket)) != PICKS
                or any(not isinstance(n, (int, np.integer)) or not 1 <= int(n) <= NUMBERS
                       for n in ticket)):
            raise ValueError("invalid seven-number ticket")
        for n in ticket:
            occurrences[int(n)] = occurrences.get(int(n), 0) + 1
    if (len(occurrences) != COVERAGE
            or occurrences.get(int(top1)) != COMMON_COPIES
            or any(count != 1 for n, count in occurrences.items() if n != int(top1))
            or top1 not in tickets[0] or top1 not in tickets[1]
            or any(top1 in t for t in tickets[2:])):
        raise ValueError("expected only top1 duplicated across tickets 1 and 2")


def make_portfolio(top1: int, seed: int) -> list[tuple[int, ...]]:
    """Use top1 twice; allocate the other 33 slots from 36 labels exactly once.

    First two tickets: top1 + six unique numbers each.
    Last three: seven other unique numbers each.
    Exactly three labels are omitted. The target outcome is never an input.
    """
    if not isinstance(top1, (int, np.integer)) or not 1 <= int(top1) <= NUMBERS:
        raise ValueError("top1 must be a number from 1 to 37")
    if not isinstance(seed, (int, np.integer)):
        raise TypeError("seed must be integer")
    top1 = int(top1)
    rng = np.random.default_rng(int(seed))
    remaining = np.array([n for n in range(1, NUMBERS + 1) if n != top1])
    shuffled = rng.permutation(remaining)
    tickets = [
        tuple(sorted((top1, *map(int, shuffled[:6])))),
        tuple(sorted((top1, *map(int, shuffled[6:12])))),
        tuple(sorted(map(int, shuffled[12:19]))),
        tuple(sorted(map(int, shuffled[19:26]))),
        tuple(sorted(map(int, shuffled[26:33]))),
    ]
    validate_tickets(tickets, top1)
    return tickets


def exact_fair_null() -> dict[str, float | int | bool]:
    """Exact null probabilities for shared1 + unique6,6,7,7,7 + omitted3.

    This is independent of which top1 was chosen (all labels are symmetric
    under a fair conditional draw). Enumeration uses integer combination
    counts and checks total mass C(37,7), not Monte Carlo approximation.
    """
    maximum_sum = hit_total = ge3_sum = ge4_sum = score_cents = mass = 0
    groups = (6, 6, 7, 7, 7)
    for shared in range(2):
        for counts in itertools.product(range(PICKS + 1), repeat=TICKETS):
            if any(k > group for k, group in zip(counts, groups)):
                continue
            omitted = PICKS - shared - sum(counts)
            if omitted < 0 or omitted > 3:
                continue
            weight = math.comb(3, omitted)
            for size, hits in zip(groups, counts):
                weight *= math.comb(size, hits)
            matches = (shared + counts[0], shared + counts[1], *counts[2:])
            maximum = max(matches)
            ge3 = int(maximum >= 3)
            ge4 = int(maximum >= 4)
            total = sum(matches)
            mass += weight
            maximum_sum += weight * maximum
            hit_total += weight * total
            ge3_sum += weight * ge3
            ge4_sum += weight * ge4
            score_cents += weight * (100 * maximum + 35 * ge3 + 75 * ge4 + 2 * total)
    if mass != UNIVERSE_SIZE:
        raise ArithmeticError("null enumeration fails 7-of-37 mass conservation")
    d = UNIVERSE_SIZE
    return {
        "exact": True,
        "total_possible_draws": d,
        "distinct_numbers": COVERAGE,
        "shared_number_copies": COMMON_COPIES,
        "max_hits": maximum_sum / d,
        "mean_hits": hit_total / (TICKETS * d),
        "ge3": ge3_sum / d,
        "ge4": ge4_sum / d,
        "score": score_cents / (100 * d),
        "first_prize_probability": TICKETS / d,
    }


def theory_report() -> dict:
    candidate = exact_fair_null()
    disjoint = exact_disjoint_null()
    return {
        "version": VERSION,
        "candidate": candidate,
        "disjoint_baseline": disjoint,
        "score_difference_vs_disjoint": candidate["score"] - disjoint["score"],
        "ge3_difference_vs_disjoint": candidate["ge3"] - disjoint["ge3"],
        "model_top1_advantage_under_fair_draw": 0.0,
        "no_forecast_skill_claimed": True,
        "research_only": True,
        "production_changed": False,
        "existing_future_oos_changed": False,
        "promotion_authorized": False,
    }
