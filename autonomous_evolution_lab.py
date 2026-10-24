#!/usr/bin/env python3
"""Bounded, evidence-gated autonomous *research* evolution for LOTO7.

The agent automatically observes, proposes, tests, remembers and replans.
It NEVER edits historical draws, frozen prospective forecasts, model champion,
Production predictions, source verification or the official research budget.
It is not a self-modifying AGI and does not claim lottery prediction advantage.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

from joint_set_v2_signal_oos_guard import validate_trusted_source
from loto7_evolving_agent import N_NUMBERS, PICKS, fingerprint_file, make_history, read_csv_flexible
from loto7_v4_runner import parse_round

VERSION = "autonomous-evolution-lab-v1"
STATE = "autonomous_evolution_state.json"
LEDGER = "autonomous_evolution_journal.jsonl"
REPORT = "autonomous_evolution_report.md"
GENESIS = "GENESIS"
MAX_TRIALS_PER_DRAW_SHA = 4
EVAL_ROUNDS = 48
MIN_TRAIN = 100
P0 = PICKS / N_NUMBERS
JST = timezone(timedelta(hours=9))


def canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False)


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def load_required(path: Path) -> dict:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("required JSON object: " + str(path))
    return raw


def atomic_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix="." + path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            out.write(content)
            out.flush()
            os.fsync(out.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def read_chain(path: Path) -> list[dict]:
    if not path.exists():
        return []
    chain = []
    previous = GENESIS
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            raise ValueError("blank autonomous ledger record")
        rec = json.loads(line)
        if not isinstance(rec, dict):
            raise ValueError("non-object autonomous ledger record")
        signed = {k: v for k, v in rec.items() if k != "record_sha256"}
        if (rec.get("sequence") != len(chain) + 1
                or rec.get("previous_record_sha256") != previous
                or digest(canonical(signed).encode("utf-8")) != rec.get("record_sha256")):
            raise ValueError("autonomous evolution ledger integrity mismatch")
        chain.append(rec)
        previous = rec["record_sha256"]
    return chain


def inspect(root: Path) -> tuple[dict, np.ndarray]:
    """Fail closed for inconsistent guards, histories or claimed source trust."""
    out = root / "loto7_agent_output"
    csv = root / "loto7.csv"
    guard = load_required(out / "research_cycle_guard.json")
    source = load_required(out / "source_validation.json")
    sha = fingerprint_file(csv)
    if guard.get("data_sha256") != sha:
        raise ValueError("research guard belongs to a different draw-history SHA")
    mode = guard.get("mode")
    if mode not in ("SEARCH", "VALIDATION_ONLY", "WAIT_FOR_NEW_DATA"):
        raise ValueError("unknown research guard mode")
    if guard.get("search_enabled") is not (mode == "SEARCH"):
        raise ValueError("research guard mode/enable flag mismatch")
    used, cap = guard.get("signal_trials_this_data"), guard.get("max_signal_trials_per_data")
    if (type(used) is not int or type(cap) is not int or
            used < 0 or cap <= 0 or used > cap or cap > 800):
        raise ValueError("invalid registered research trial budget")
    x, cleaned = make_history(read_csv_flexible(csv))
    if len(x) < MIN_TRAIN + EVAL_ROUNDS:
        raise ValueError("insufficient prior-only evaluation history")
    latest = parse_round(cleaned["回別"].iloc[-1])
    if latest is None or latest != len(x):
        raise ValueError("draw CSV round sequence inconsistent")
    reported = source.get("latest") or {}
    if (reported.get("round") != latest or
            str(reported.get("date")) != cleaned["抽せん日"].iloc[-1].date().isoformat()):
        raise ValueError("source latest round/date conflicts with draw history")
    explicitly_trusted = (
        source.get("status") == "ok"
        and source.get("verification") == "verified_two_result_sources"
    )
    trusted = False
    if explicitly_trusted:
        check = validate_trusted_source(csv, out / "source_validation.json")
        if not check.get("trusted") or not check.get("secondary"):
            raise ValueError("independent result verification missing")
        trusted = True
    return {
        "data_sha256": sha, "latest_round": latest, "research_mode": mode,
        "trusted": trusted, "official_trials_used": used, "official_trial_limit": cap,
    }, x


def propose(trials: list[dict]) -> dict:
    """Predeclared bounded mutations. Prior diagnostic scores affect only trial 4."""
    plans = (
        {"window": 30, "prior": 100, "blend": 0.25},
        {"window": 70, "prior": 180, "blend": 0.35},
        {"window": 140, "prior": 300, "blend": 0.50},
    )
    n = len(trials)
    if n < len(plans):
        return dict(plans[n])
    best = max(trials, key=lambda v: (v["diagnostic"]["mean_log_edge"], -v["trial"]))
    p = best["config"]
    return {
        "window": min(180, max(20, int(round(p["window"] * 0.75)))),
        "prior": min(400, max(50, int(round(p["prior"] * 1.20)))),
        "blend": round(min(0.80, float(p["blend"]) + 0.10), 4),
    }


def prior_probabilities(prefix: np.ndarray, config: dict) -> np.ndarray:
    """Posterior-smoothed inclusion weights using ONLY preceding rounds."""
    if prefix.ndim != 2 or prefix.shape[1] != N_NUMBERS or len(prefix) < MIN_TRAIN:
        raise ValueError("insufficient prior history")
    n = min(int(config["window"]), len(prefix))
    s = prefix[-n:].astype(np.int64, copy=False).sum(axis=0)
    prior = int(config["prior"])
    blend = float(config["blend"])
    if not 20 <= n <= 180 or not 50 <= prior <= 400 or not 0 <= blend <= 0.8:
        raise ValueError("candidate out of predeclared search bounds")
    posterior = (s + prior * P0) / (n + prior)
    q = (1.0 - blend) * posterior + blend * P0
    if (not np.all(np.isfinite(q)) or not np.all((q > 0) & (q < 1))
            or not math.isclose(float(q.sum()), PICKS, abs_tol=1e-10)):
        raise ValueError("invalid inclusion probability vector")
    return q


def score_candidate(x: np.ndarray, config: dict) -> dict:
    """Chronological 48-draw diagnostic; there is NO future OOS evidence here."""
    logs, hits = [], []
    for t in range(len(x) - EVAL_ROUNDS, len(x)):
        q = prior_probabilities(x[:t], config)
        y = x[t].astype(np.int64, copy=False)
        edge = (y * np.log(q / P0) + (1 - y) * np.log((1 - q) / (1 - P0)))
        logs.append(float(edge.mean()))
        ranking = np.argsort(-q, kind="stable")[:PICKS]
        hits.append(int(y[ranking].sum()))
    blocks = [float(np.mean(logs[i:i + 16])) for i in (0, 16, 32)]
    return {
        "evaluated_historical_draws": EVAL_ROUNDS,
        "mean_log_edge": float(np.mean(logs)),
        "mean_top7_hits": float(np.mean(hits)),
        "uniform_expected_top7_hits": PICKS * PICKS / N_NUMBERS,
        "chronological_block_log_edges": blocks,
        "historical_only": True,
        "independent_future_evidence": False,
        "production_eligible": False,
    }


def next_action(info: dict, trials: list[dict]) -> str:
    if not info["trusted"]:
        return "WAIT_FOR_INDEPENDENT_RESULT_SOURCE"
    if info["research_mode"] != "SEARCH":
        return "WAIT_FOR_NEW_DATA_OR_VALIDATION"
    if info["official_trials_used"] >= info["official_trial_limit"]:
        return "WAIT_FOR_RESEARCH_BUDGET"
    if len(trials) >= MAX_TRIALS_PER_DRAW_SHA:
        return "WAIT_FOR_NEW_VERIFIED_HISTORY"
    # Do not bypass the official remaining trial envelope with sandbox trials.
    if info["official_trials_used"] + len(trials) >= info["official_trial_limit"]:
        return "WAIT_FOR_RESEARCH_BUDGET"
    return "EVALUATE_SANDBOX_MUTATION"


def commit_event(path: Path, chain: list[dict], event: dict) -> dict:
    rec = {
        "sequence": len(chain) + 1,
        "previous_record_sha256": chain[-1]["record_sha256"] if chain else GENESIS,
        **event,
    }
    rec["record_sha256"] = digest(canonical(rec).encode("utf-8"))
    new_content = "".join(canonical(row) + "\n" for row in (*chain, rec))
    atomic_text(path, new_content)
    return rec


def render(info: dict, trials: list[dict], action: str, leader: str | None) -> str:
    return "\n".join([
        "# Autonomous Evolution — Research Sandbox",
        "",
        f"- Last recorded round: **{info['latest_round']}**",
        f"- Independently verified source: **{info['trusted']}**",
        f"- Registered research mode: **{info['research_mode']}**",
        f"- Action: **{action}**",
        f"- Bounded diagnostic mutations this history: **{len(trials)}/{MAX_TRIALS_PER_DRAW_SHA}**",
        f"- Diagnostic leader (not Production): **{leader or 'none'}**",
        "",
        "| Trial | Prior window | Smoothing | Uniform blend | Historical log edge |",
        "|---:|---:|---:|---:|---:|",
        *(f"| {rec['trial']} | {rec['config']['window']} | {rec['config']['prior']} | "
          f"{rec['config']['blend']:.2f} | {rec['diagnostic']['mean_log_edge']:+.7f} |"
          for rec in trials),
        "",
        "**RESEARCH ONLY.** Same historical data were used for choosing the diagnostic leader.",
        "No independent prospective validation, no evidence of superior lottery odds,",
        "no automatic Production model promotion, no code self-modification,",
        "and no rewriting of registered Future-OOS or pre-draw forecasts.",
        "",
    ]) + "\n"


def run(root: Path) -> dict:
    root = root.resolve()
    info, history = inspect(root)  # All external-state validation precedes writes.
    out = root / "loto7_agent_output"
    journal = out / LEDGER
    state_file = out / STATE
    report_file = out / REPORT
    chain = read_chain(journal)
    state = load_required(state_file) if state_file.exists() else None
    if (bool(chain) != bool(state) or
            (state is not None and (
                state.get("version") != VERSION
                or state.get("sequence") != len(chain)
                or state.get("last_record_sha256") != chain[-1]["record_sha256"]
                or state.get("data_sha256") != chain[-1]["data_sha256"]))):
        raise ValueError("autonomous state/ledger continuity mismatch")
    trials = [] if state is None or state["data_sha256"] != info["data_sha256"] else list(state["trials"])
    if (len(trials) > MAX_TRIALS_PER_DRAW_SHA
            or [t.get("trial") for t in trials] != list(range(1, len(trials) + 1))
            or len({canonical(t["config"]) for t in trials}) != len(trials)):
        raise ValueError("invalid bounded trial history")
    action = next_action(info, trials)
    config = None
    metrics = None
    if action == "EVALUATE_SANDBOX_MUTATION":
        config = propose(trials)
        if canonical(config) in {canonical(t["config"]) for t in trials}:
            raise ValueError("repeated autonomous mutation; fail closed")
        metrics = score_candidate(history, config)
        trials.append({
            "trial": len(trials) + 1,
            "candidate_id": digest((info["data_sha256"] + "|" + canonical(config)).encode())[:20],
            "config": config, "diagnostic": metrics,
        })
    next_decision = next_action(info, trials)
    leader = (max(trials, key=lambda v: (v["diagnostic"]["mean_log_edge"], -v["trial"]))["candidate_id"]
              if trials else None)
    event = {
        "data_sha256": info["data_sha256"],
        "latest_round": info["latest_round"],
        "action": action,
        "next_action": next_decision,
        "trusted_source": info["trusted"],
        "research_mode": info["research_mode"],
        "trial": trials[-1] if config is not None else None,
        "diagnostic_leader": leader,
    }
    # Do not create hourly commit churn if evidence and decision are unchanged.
    if chain:
        last = chain[-1]
        prior = {k: last[k] for k in event}
        if canonical(prior) == canonical(event):
            return state
    record = commit_event(journal, chain, event)
    result = {
        "version": VERSION,
        "sequence": record["sequence"],
        "last_record_sha256": record["record_sha256"],
        "data_sha256": info["data_sha256"],
        "latest_round": info["latest_round"],
        "trusted_source": info["trusted"],
        "research_mode": info["research_mode"],
        "last_action": action,
        "next_action": next_decision,
        "diagnostic_leader": leader,
        "trials": trials,
        "authority": {
            "automated_historical_diagnostics": True,
            "self_modifying_code": False,
            "research_budget_override": False,
            "production_or_champion_update": False,
            "retrospective_future_freeze_or_grade": False,
        },
    }
    atomic_text(state_file, json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    atomic_text(report_file, render(info, trials, next_decision, leader))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Fail-closed research-only self-evolution controller")
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    args = parser.parse_args()
    result = run(args.repo_root)
    print(canonical({
        "last_action": result["last_action"],
        "next_action": result["next_action"],
        "sandbox_trials": len(result["trials"]),
        "trusted_source": result["trusted_source"],
        "production_modified": result["authority"]["production_or_champion_update"],
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
