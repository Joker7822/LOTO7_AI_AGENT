#!/usr/bin/env python3
"""Dependency-free fail-closed validator for issued Production 702+ tickets.

Legacy v1 is seeded uniform, prior ranked v1 is contiguous Champion ranks.
New unfrozen targets 705+ use the separately trained combination AI agent.
All older frozen versions remain valid in the append-only ledger:
publication policy is stricter than the historical issued-row validator.
"""
from __future__ import annotations

from typing import Mapping, Sequence

VERSION = "production-disjoint35-layout-v1"  # Immutable legacy policy (702+).
RANKED_VERSION = "production-ai-ranked-disjoint35-layout-v1"
COMBINATION_VERSION = "production-ai-ranked35-pairwise-combination-v1"
MIN_TARGET_ROUND = 702
RANKED_MIN_TARGET_ROUND = 705
COMBINATION_MIN_TARGET_ROUND = 705


def publication_policy_for_target(target_round: int) -> str:
    """New issuances only; never infer a frozen target's policy from its round."""
    if type(target_round) is not int or target_round < MIN_TARGET_ROUND:
        raise ValueError("disjoint35 publisher requires target 702+")
    return COMBINATION_VERSION if target_round >= COMBINATION_MIN_TARGET_ROUND else VERSION


def issued_policy(rows: Sequence[Mapping[str, object]], target_round: int) -> str:
    """Read the frozen policy rather than applying new publication rules retroactively."""
    if type(target_round) is not int or target_round < MIN_TARGET_ROUND:
        raise ValueError("disjoint35 issued-row validator requires target 702+")
    if not rows:
        raise ValueError("missing issued Production rows")
    models = {str(row.get("model_version", "")) for row in rows}
    if len(models) != 1:
        raise ValueError("mixed Production model versions violate disjoint35 policy")
    model = models.pop()
    if model.endswith("+" + VERSION):
        return VERSION
    if model.endswith("+" + RANKED_VERSION) and target_round >= RANKED_MIN_TARGET_ROUND:
        return RANKED_VERSION
    if model.endswith("+" + COMBINATION_VERSION) and target_round >= COMBINATION_MIN_TARGET_ROUND:
        return COMBINATION_VERSION
    raise ValueError("unknown or ineligible disjoint35 Production policy")


def validate_issued_rows(rows: Sequence[Mapping[str, object]], target_round: int) -> None:
    """Require five active, sorted, valid and pairwise-disjoint frozen tickets."""
    if type(target_round) is not int or target_round < MIN_TARGET_ROUND:
        raise ValueError("disjoint35 issued-row validator requires target 702+")
    if len(rows) != 5:
        raise ValueError("disjoint35 requires exactly five active Production tickets")
    try:
        ordered = sorted(rows, key=lambda row: int(row["ticket"]))
        if [int(row["ticket"]) for row in ordered] != [1, 2, 3, 4, 5]:
            raise ValueError("disjoint35 Production ticket positions are incomplete")
        issued_policy(ordered, target_round)
        used: set[int] = set()
        for row in ordered:
            raw = row.get("predicted_numbers", "")
            if not isinstance(raw, str):
                raise ValueError("invalid disjoint35 Production ticket numbers")
            tokens = raw.strip().split()
            if len(tokens) != 7 or any(not token.isdecimal() for token in tokens):
                raise ValueError("invalid disjoint35 Production ticket numbers")
            numbers = tuple(int(token) for token in tokens)
            if numbers != tuple(sorted(numbers)) or len(set(numbers)) != 7:
                raise ValueError("disjoint35 ticket has duplicate or unsorted numbers")
            if any(not 1 <= number <= 37 for number in numbers):
                raise ValueError("disjoint35 ticket number outside 1..37")
            if used.intersection(numbers):
                raise ValueError("disjoint35 Production tickets must not overlap")
            used.update(numbers)
        if len(used) != 35:
            raise ValueError("disjoint35 Production must cover exactly 35 distinct numbers")
    except (KeyError, TypeError, OverflowError) as exc:
        raise ValueError("malformed disjoint35 Production ledger") from exc
