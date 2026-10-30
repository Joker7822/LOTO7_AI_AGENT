#!/usr/bin/env python3
"""Dependency-free fail-closed validator for issued Production 702+ tickets.

This module intentionally imports only the Python standard library.
Sakura database synchronization must verify disjointness without requiring
NumPy, Pandas, the forecasting runtime or any model promotion permissions.
"""
from __future__ import annotations

from typing import Mapping, Sequence

VERSION = "production-disjoint35-layout-v1"
MIN_TARGET_ROUND = 702


def validate_issued_rows(rows: Sequence[Mapping[str, object]], target_round: int) -> None:
    """Require five active, sorted, individually valid, pairwise disjoint tickets."""
    if type(target_round) is not int or target_round < MIN_TARGET_ROUND:
        raise ValueError("disjoint35 issued-row validator requires target 702+")
    if len(rows) != 5:
        raise ValueError("disjoint35 requires exactly five active Production tickets")
    try:
        ordered = sorted(rows, key=lambda row: int(row["ticket"]))
        if [int(row["ticket"]) for row in ordered] != [1, 2, 3, 4, 5]:
            raise ValueError("disjoint35 Production ticket positions are incomplete")
        if any(not str(row.get("model_version", "")).endswith("+" + VERSION)
               for row in ordered):
            raise ValueError("disjoint35 Production model policy is missing or changed")

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
