#!/usr/bin/env python3
"""Audit registered research replay without touching predictions or grades.

This is an observational report, not proof of the historical root cause of
an intermittent failure. Reports exact environment and bounded float drift.
Throws on wrong hashes, source prefix, categorical changes or material drift.
"""
from __future__ import annotations

import json
import hashlib
import os
import platform
from pathlib import Path

import numpy as np
import pandas as pd

import online_learning_boost_v2 as v2
import advanced_online_v3 as v3
import online_v2_replay_runtime as v2runtime
import online_v3_replay_runtime as v3runtime
from loto7_evolving_agent import make_history, read_csv_flexible


def run(root: Path) -> dict:
    root = root.resolve()
    x, frame = make_history(read_csv_flexible(root / "loto7.csv"))
    status = {
        "latest_result_round": len(x),
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "OPENBLAS_NUM_THREADS": os.environ.get("OPENBLAS_NUM_THREADS"),
            "OMP_NUM_THREADS": os.environ.get("OMP_NUM_THREADS"),
            "MKL_NUM_THREADS": os.environ.get("MKL_NUM_THREADS"),
            "operational_file_sha256": {
                name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                for name in (
                    "online_v2_replay_runtime.py",
                    "online_v3_replay_runtime.py",
                    "requirements-online-research.lock",
                )
            },
        },
    }

    v2file = root / v2.DESTINATION
    if v2file.exists():
        ledger = json.loads(v2file.read_text(encoding="utf-8"))
        original_predict, original_assess = v2.prediction, v2.assessment
        v2.prediction, v2.assessment = v2runtime.replay_adapters(
            ledger.get("events", []), original_predict, original_assess)
        try:
            _a, _b, grades = v2.assert_ledger(ledger, root, x, frame)
        finally:
            v2.prediction, v2.assessment = original_predict, original_assess
        status["v2"] = {
            "registered_manifest_sha256": ledger["registration"]["manifest_sha256"],
            "events": len(ledger["events"]), "grades": len(grades),
            "target": ledger["events"][-1]["target_round"],
            "last_sha256": ledger["events"][-1]["event_sha256"],
            "audit": "chain_and_bounded_replay_verified",
        }

    v3file = root / v3.STATE
    if v3file.exists():
        ledger = json.loads(v3file.read_text(encoding="utf-8"))
        registration = json.loads((root / v3.REGISTRATION).read_text(encoding="utf-8"))
        if registration["algorithm_manifest"] != v3.manifest(root):
            raise ValueError("v3 registered algorithm manifest changed")
        original = v3.model_forecast
        v3.model_forecast = v3runtime.replay_adapter(ledger.get("events", []), original)
        try:
            es, ms, ts, edges, wealth = v3.validate_state(
                ledger, registration, root, x, frame)
        finally:
            v3.model_forecast = original
        status["v3"] = {
            "registered_manifest_sha256": registration["algorithm_manifest"]["manifest_sha256"],
            "events": len(ledger["events"]), "grades": len(edges),
            "target": ledger["events"][-1]["target_round"],
            "last_sha256": ledger["events"][-1]["event_sha256"],
            "audit": "chain_and_bounded_replay_verified",
        }
    return status


if __name__ == "__main__":
    print(json.dumps(run(Path(".")), ensure_ascii=False, indent=2))
