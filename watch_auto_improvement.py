#!/usr/bin/env python3
"""Automatically investigate operational WATCH items without changing frozen models.

This is a bounded research-only repair lane. In particular it exposes a NEW,
versioned, wide-integer pair_context candidate. The historical/Production
expert and registered prospective vectors MUST remain byte-for-byte untouched.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

import agent_role_council as council
from joint_set_v2_signal_oos_guard import validate_trusted_source
from loto7_evolving_agent import (
    expert_probabilities, make_history, read_csv_flexible, zsoftmax,
)

VERSION = "watch-auto-improvement-research-v1"
ALGORITHM = "pair-context-wide-int-v2-research-only"
REPORT_FILE = "watch_auto_improvement_report.json"
MARKDOWN_FILE = "watch_auto_improvement_report.md"
MAX_BACKTEST_ROUNDS = 120
FIRST_PREDICTION_PREFIX = 100
EPSILON = 1e-15


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def wide_pair_context(hist: np.ndarray) -> np.ndarray:
    """Versioned fix: accumulate co-occurrences in int64 BEFORE matmul.

    All other expert distributions, Production config, hyperparameters,
    published tickets and preregistered future predictions stay unchanged.
    """
    h = np.asarray(hist)
    if (h.ndim != 2 or h.shape[1] != 37
            or not np.issubdtype(h.dtype, np.integer)
            or h.shape[0] < 20
            or not np.all((h == 0) | (h == 1))
            or not np.all(h.sum(axis=1) == 7)):
        raise ValueError("require >=20 valid historical 7-of-37 binary draws")
    wide = h.astype(np.int64, copy=False)
    co = wide.T @ wide
    denom = wide.sum(axis=0).astype(float)
    last = np.flatnonzero(wide[-1])
    pair = np.array([
        np.mean([co[j, k] / max(denom[k], 1.0) for k in last])
        for j in range(37)
    ], dtype=float)
    q = zsoftmax(pair, 1.40)
    if (q.shape != (37,) or not np.all(np.isfinite(q))
            or np.any(q < 0) or not np.isclose(q.sum(), 1)):
        raise ValueError("corrected expert did not produce a valid distribution")
    return q


def compare_prefixes(x: np.ndarray, n: int = MAX_BACKTEST_ROUNDS) -> dict:
    """Retrospective diagnostics ONLY: each forecast sees prefix [:t] not x[t].

    Current method choice was selected using the same historical dataset;
    this is not an independent prospective prediction contest.
    """
    if type(n) is not int or not 1 <= n <= MAX_BACKTEST_ROUNDS:
        raise ValueError("invalid bounded retrospective diagnostics window")
    if len(x) < FIRST_PREDICTION_PREFIX + 1:
        return {"rounds": 0, "status": "insufficient_history",
                "independent_oos": False}
    hits_old, hits_new, log_old, log_new, deltas = [], [], [], [], []
    start = max(FIRST_PREDICTION_PREFIX, len(x) - n)
    for t in range(start, len(x)):
        hist = x[:t]
        old = expert_probabilities(hist)["pair_context"]
        new = wide_pair_context(hist)
        truth = np.flatnonzero(x[t])
        if truth.size != 7:
            raise ValueError("invalid seven-number draw in diagnostics")
        hits_old.append(int(np.isin(np.argsort(-old, kind="stable")[:7], truth).sum()))
        hits_new.append(int(np.isin(np.argsort(-new, kind="stable")[:7], truth).sum()))
        # Marginal ranking pseudo-logscore, NOT 7-of-37 joint likelihood.
        log_old.append(float(np.mean(np.log(np.maximum(old[truth], EPSILON)))))
        log_new.append(float(np.mean(np.log(np.maximum(new[truth], EPSILON)))))
        deltas.append(float(np.max(np.abs(old - new))))
    return {
        "rounds": len(hits_old),
        "first_historical_round": start + 1,
        "last_historical_round": len(x),
        "legacy_mean_top7_hits": round(float(np.mean(hits_old)), 6),
        "wide_v2_mean_top7_hits": round(float(np.mean(hits_new)), 6),
        "delta_mean_top7_hits": round(float(np.mean(hits_new) - np.mean(hits_old)), 6),
        "legacy_mean_marginal_logscore": round(float(np.mean(log_old)), 8),
        "wide_v2_mean_marginal_logscore": round(float(np.mean(log_new)), 8),
        "delta_marginal_logscore": round(float(np.mean(log_new) - np.mean(log_old)), 8),
        "max_absolute_expert_probability_change": round(max(deltas), 10),
        "independent_oos": False,
        "retrospective_optimized_model_selection_authorized": False,
    }


def evaluate(root: Path, *, now: datetime | None = None) -> dict:
    root = root.resolve()
    out = root / "loto7_agent_output"
    watch_file = out / "agent_role_council_summary.json"
    source_file = out / "source_validation.json"
    guard_file = out / "research_cycle_guard.json"
    csv = root / "loto7.csv"
    champion = out / "model_champion.json"
    selected = [csv, watch_file, source_file, guard_file, champion,
                root / "loto7_evolving_agent.py",
                root / "agent_role_council.py",
                root / "watch_auto_improvement.py"]
    before = {str(path.relative_to(root)): sha(path) for path in selected}
    source = json.loads(source_file.read_text(encoding="utf-8"))
    watch = json.loads(watch_file.read_text(encoding="utf-8"))
    guard = json.loads(guard_file.read_text(encoding="utf-8"))
    model = json.loads(champion.read_text(encoding="utf-8"))
    x, clean = make_history(read_csv_flexible(csv))
    latest = council.round_id(clean["回別"].iloc[-1])
    if (watch.get("latest_resolved_round") != latest
            or not isinstance(watch.get("handoff_tasks"), list)
            or guard.get("data_sha256") != before["loto7.csv"]):
        raise ValueError("stale council or research guard; no automatic repair claim")
    codes = [t.get("issue_code") for t in watch["handoff_tasks"]]
    if len(codes) != len(set(codes)):
        raise ValueError("duplicate operational WATCH action")
    if any(not isinstance(t, dict) or t.get("priority") not in {"watch", "block"}
           for t in watch["handoff_tasks"]):
        raise ValueError("malformed operational watch handoff")
    trust = False
    if (source.get("status") == "ok"
            and source.get("verification") == "verified_two_result_sources"
            and source.get("verification_provenance", {}).get("draw_csv_sha256")
                == before["loto7.csv"]):
        attestation = validate_trusted_source(csv, source_file)
        trust = attestation.get("trusted") is True and attestation.get("round") == latest
    issues = []
    pair_count = council.pair_context_overflow_count(x)
    if "PAIR_CONTEXT_INT8_OVERFLOW" in codes or pair_count:
        if pair_count == 0 and "PAIR_CONTEXT_INT8_OVERFLOW" in codes:
            raise ValueError("stale pair overflow alert")
        current = wide_pair_context(x)
        exact = x.astype(np.int64).T @ x.astype(np.int64)
        legacy = x.T @ x
        if np.count_nonzero(exact != legacy.astype(np.int64)) != pair_count:
            raise ValueError("wide integer verification disagrees with independent audit")
        # Candidate numerical validation is safe on all historical inputs.
        # No scoring against untrusted real outcomes.
        diagnostic = compare_prefixes(x) if trust else {
            "status": "awaiting_independent_source", "rounds": 0,
            "independent_oos": False,
        }
        issues.append({
            "code": "PAIR_CONTEXT_INT8_OVERFLOW",
            "legacy_corrupted_cooccurrence_cells": pair_count,
            "resolution": "separately_versioned_research_candidate_validated",
            "candidate_algorithm_version": ALGORITHM,
            "candidate_software_sha256": before["watch_auto_improvement.py"],
            "corrected_distribution_sum": round(float(current.sum()), 12),
            "candidate_numerical_overflow_cells": 0,
            "current_champion_remains_unchanged": True,
            "production_fix_deployed": False,
            "requires_independent_future_oos_before_promotion": True,
            "historical_diagnostics": diagnostic,
        })
    if "NO_EARLY_PORTFOLIO_CLAIM" in codes:
        issues.append({
            "code": "NO_EARLY_PORTFOLIO_CLAIM",
            "resolution": "expected_wait_for_genuinely_future_verified_draws",
            "automatic_backfill_allowed": False,
            "automatic_model_promotion_allowed": False,
            "does_not_count_as_broken_software": True,
        })
    for code in codes:
        if code not in {"PAIR_CONTEXT_INT8_OVERFLOW", "NO_EARLY_PORTFOLIO_CLAIM"}:
            issues.append({
                "code": code,
                "resolution": "safety_escalation_not_automatically_resolved",
                "automatic_model_or_production_change_allowed": False,
            })
    if {str(path.relative_to(root)): sha(path) for path in selected} != before:
        raise ValueError("concurrent protected source modification")
    if not issues:
        status = "no_outstanding_watch_items"
    elif any(i["resolution"] == "safety_escalation_not_automatically_resolved"
             for i in issues):
        status = "needs_existing_workflow_or_human_review"
    elif trust:
        status = "research_fix_checked_only_not_production_resolved"
    else:
        status = "awaiting_independent_draw_verification"
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("timezone-aware audit time required")
    return {
        "version": VERSION,
        "checked_at_utc": now.astimezone(timezone.utc).isoformat(timespec="seconds"),
        "source_round": latest,
        "source_two_result_verified": trust,
        "guard_mode": guard["mode"],
        "same_data_trials_used": guard.get("signal_trials_this_data"),
        "same_data_trials_limit": guard.get("max_signal_trials_per_data"),
        "champion_version": model["model_version"],
        "status": status,
        "watched_incident_codes": codes,
        "issues": issues,
        "source_files_sha256": before,
        "new_optimizer_trials": 0,
        "past_frozen_vectors_recomputed": False,
        "registered_future_oos_modified": False,
        "production_modified": False,
        "champion_modified": False,
        "fully_automatic_promotion_authorized": False,
        "verified_predictive_edge": False,
    }


def markdown(result: dict) -> str:
    lines = [
        "# Autonomous WATCH improvement (research-only, auditable)",
        "",
        f"- Time UTC: {result['checked_at_utc']}",
        f"- Result: **{result['status']}**",
        f"- Trusted source: {result['source_two_result_verified']}; round #{result['source_round']}",
        f"- Champion (unchanged): `{result['champion_version']}`",
        f"- Budget: {result['guard_mode']} / {result['same_data_trials_used']}/{result['same_data_trials_limit']}",
        "",
    ]
    for item in result["issues"]:
        lines += [
            f"## {item['code']}",
            f"- Research action: **{item['resolution']}**",
        ]
        if "legacy_corrupted_cooccurrence_cells" in item:
            d = item["historical_diagnostics"]
            lines.append(f"- Exact legacy int8 overflow: {item['legacy_corrupted_cooccurrence_cells']} cells")
            lines.append(f"- Corrected version: {item['candidate_algorithm_version']}")
            lines.append(f"- Prior-only retrospective rounds: {d.get('rounds', 0)}")
            if d.get("rounds"):
                lines.append(f"- Top7 hit change (descriptive): {d['delta_mean_top7_hits']:+.6f}")
                lines.append(f"- Marginal logscore change (descriptive): {d['delta_marginal_logscore']:+.8f}")
            lines.append("- Separate versioned candidate only; existing model NOT corrected in Production.")
        else:
            lines.append("- Waiting cannot be solved by inventing future lottery results.")
        lines.append("")
    lines += [
        "No automatic Champion promotion, retroactive freeze, optimizer budget",
        "override or alteration of real prior forecasts. Historical replay does",
        "NOT establish a predictive edge; separate prospective validation required.",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Bounded safe handling of operational watch items")
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--out-dir", type=Path, default=Path("loto7_agent_output"))
    args = parser.parse_args()
    result = evaluate(args.repo_root)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / REPORT_FILE).write_text(
        json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    (args.out_dir / MARKDOWN_FILE).write_text(markdown(result), encoding="utf-8")
    print(json.dumps({"status": result["status"], "incidents": result["watched_incident_codes"],
                      "champion_modified": False}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
