#!/usr/bin/env python3
"""Prospective v2: bounded numeric replay, immutable audit, no backfill.

Do not edit the SHA-registered online_learning_boost_v2.py or its
research/online_learning_v2/state.json past events. The registered validator
still authenticates the event hash chain, source prefix, draw date, grades,
algorithm fingerprint and publication order. The wrapper only normalizes
sub-5e-13 float rounding in previously committed predictions and scores.
"""
from __future__ import annotations

import argparse
import json
import platform
from datetime import datetime
from pathlib import Path

import numpy as np

import online_learning_boost_v2 as registered
from online_v3_replay_runtime import ABS_REPLAY_TOL, _compare_recursively


def _frozen_maps(events: list[dict]) -> tuple[dict[int, dict], dict[int, dict]]:
    freezes, grades = {}, {}
    for event in events:
        target = event.get("target_round")
        if type(target) is not int:
            raise ValueError("v2 audit target malformed")
        if event.get("kind") == "freeze":
            if target in freezes:
                raise ValueError("v2 duplicate frozen target")
            freezes[target] = event
        elif event.get("kind") == "grade":
            if target in grades:
                raise ValueError("v2 duplicate graded target")
            grades[target] = event
        else:
            raise ValueError("v2 unexpected audit event kind")
    return freezes, grades


def _compatible(frozen: dict, regenerated: dict, label: str) -> dict:
    """Only float roundoff is compatible; all categorical fields are exact.

    Returning the saved object lets the registered SHA-chain verifier compare
    precisely to the pre-draw vector that was actually frozen. The raw ledger
    cannot be changed by this wrapper.
    """
    changes, maximum = _compare_recursively(frozen, regenerated, label)
    if changes:
        print(f"[V2-NUMERIC-REPLAY] {label}: {changes} float fields differ "
              f"by <= {ABS_REPLAY_TOL:g}; max={maximum:.17g}. "
              "Reusing ONLY immutable sealed evidence.")
    return frozen


def replay_adapters(events: list[dict], original_predict, original_assess):
    freezes, grades = _frozen_maps(events)

    def predict(prior, expert_scores, meta_scores, graded_edges):
        generated = original_predict(prior, expert_scores, meta_scores, graded_edges)
        target = len(prior) + 1
        sealed = freezes.get(target)
        if sealed is None:
            # First prediction for a genuinely future draw: never reuse an
            # earlier target's result or prediction.
            return generated
        saved = sealed["prediction"]
        if (saved.get("prefix_sha256") != generated.get("prefix_sha256")
                or saved.get("top7") != generated.get("top7")
                or saved.get("drift_guard_active") != generated.get("drift_guard_active")):
            raise ValueError("v2 MATERIAL replay change: prefix/top7/drift")
        return _compatible(saved, generated, f"freeze_{target:04d}")

    def assess(freeze, actual):
        generated = original_assess(freeze, actual)
        target = freeze.get("target_round")
        prior = grades.get(target)
        if prior is None:
            # A trusted grade is being issued for the first time.
            return generated
        return _compatible(prior["grade"], generated, f"grade_{target:04d}")

    return predict, assess


def run(root: Path, output: Path | None = None, source_report: Path | None = None,
        *, now: datetime | None = None) -> dict:
    root = root.resolve()
    output = (output or root / registered.DESTINATION).resolve()
    source_report = (source_report or root / "loto7_agent_output/source_validation.json").resolve()
    original_predict = registered.prediction
    original_assess = registered.assessment
    if output.exists():
        sealed = json.loads(output.read_text(encoding="utf-8"))
        registered.prediction, registered.assessment = replay_adapters(
            sealed.get("events", []), original_predict, original_assess)
    try:
        # All normative registration, chronology, trusted source and SHA
        # checks still run unchanged in the preregistered implementation.
        result = registered.run(root, output, source_report, now=now)
    finally:
        registered.prediction = original_predict
        registered.assessment = original_assess
    return {
        **result, "numeric_replay_policy": "strict_except_float_abs_5e-13",
        "registered_algorithm_modified": False,
        "frozen_past_events_rewritten": False,
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
        },
    }


def main() -> None:
    args = argparse.ArgumentParser()
    args.add_argument("--repo-root", type=Path, default=Path("."))
    args.add_argument("--state-file", type=Path,
                      default=Path(registered.DESTINATION))
    args.add_argument("--source-report", type=Path,
                      default=Path("loto7_agent_output/source_validation.json"))
    parsed = args.parse_args()
    root = parsed.repo_root.resolve()
    print(json.dumps(run(root, root / parsed.state_file,
                         root / parsed.source_report), indent=2,
                     ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
