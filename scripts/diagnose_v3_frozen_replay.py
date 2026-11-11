#!/usr/bin/env python3
"""Forensic, nonmutating replay diagnosis of v3's frozen future forecast.

Emits only scalar numerical deviation summaries and public hash identity.
It never edits the registered forecast or invents lottery results.
"""
from __future__ import annotations
import json
import math
from pathlib import Path
import numpy as np
import advanced_online_v3 as v3
from loto7_evolving_agent import make_history, read_csv_flexible


def leaves(obj, prefix=""):
    if isinstance(obj, dict):
        for key, val in obj.items():
            yield from leaves(val, f"{prefix}.{key}" if prefix else key)
    elif isinstance(obj, list):
        for n, val in enumerate(obj):
            yield from leaves(val, f"{prefix}[{n}]")
    else:
        yield prefix, obj


def main():
    root = Path(".")
    registration = json.loads((root / v3.REGISTRATION).read_text())
    state = json.loads((root / v3.STATE).read_text())
    x, frame = make_history(read_csv_flexible(root / "loto7.csv"))
    last = state["events"][-1]
    target = last["target_round"]
    exact = last["prediction"]
    es, ms, ts, edges, wealth = v3.empty_scores()
    actual = v3.model_forecast(x[:target - 1], es, ms, ts, edges)
    actual["e_process_values_before"] = list(wealth)
    table_expected = dict(leaves(exact))
    table_actual = dict(leaves(actual))
    if set(table_expected) != set(table_actual):
        raise ValueError("forecast schema mismatch")
    bad = []
    max_err = 0.0
    biggest = None
    count = 0
    for key in table_expected:
        a, b = table_expected[key], table_actual[key]
        if type(a) in (float,int) and type(b) in (float,int) and type(a) is not bool:
            if not math.isfinite(float(a)) or not math.isfinite(float(b)):
                raise ValueError("non-finite numeric prediction")
            delta = abs(a - b)
            max_err = max(max_err, delta)
            if delta and (biggest is None or delta > biggest[1]):
                biggest = (key, delta)
            if delta:
                count += 1
            if delta > 1e-12:
                bad.append((key, a, b, delta))
        elif a != b:
            bad.append((key, a, b, "non-numeric mismatch"))
    print(json.dumps({
        "registered_algorithm_manifest_unchanged":
            v3.manifest(root) == registration["algorithm_manifest"],
        "frozen_target": target,
        "frozen_sha256": last["event_sha256"],
        "frozen_prefix_matches_recomputed":
            exact["prefix_sha256"] == actual["prefix_sha256"],
        "exact_dict_equal": exact == actual,
        "numerical_values_changed": count,
        "max_absolute_difference": max_err,
        "largest_difference": biggest,
        "material_mismatches": bad[:12],
        "material_mismatch_total": len(bad),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
