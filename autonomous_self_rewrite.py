#!/usr/bin/env python3
"""Autonomous self-rewrite of isolated research model code + promotion handoff.

The agent autonomously turns its learned historical leader into executable
versioned SOURCE CODE, validates and replaces that research-only source, and
records explicit evidence. Source is never loaded by the canonical Production
publisher. Active model promotion is already automated by the existing v4
strict, random and matched-ensemble Future-OOS gates.

No arbitrary LLM/code execution, untrusted source, SHA mismatch, retry of an
exhausted trial budget, retrospective OOS, or rule modification is permitted.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
from pathlib import Path

import autonomous_evolution_lab as lab
import loto7_v4_runner as v4
import matched_permutation_ensemble as ensemble

VERSION = "autonomous-research-source-rewrite-v1"
GENERATED = Path("research/autonomous_generated")
SOURCE = "research_model.py"
MANIFEST = "research_model_manifest.json"
REPORT = "autonomous_self_rewrite_report.md"
CONFIG_KEYS = ("window", "prior", "blend")


def stable_json(obj: object) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


def fingerprint(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def validate_model(config: dict) -> dict:
    if not isinstance(config, dict) or set(config) != set(CONFIG_KEYS):
        raise ValueError("unrecognized generated research config")
    w, p, b = config["window"], config["prior"], config["blend"]
    if (type(w) is not int or type(p) is not int
            or type(b) not in (int, float)
            or not 20 <= w <= 180 or not 50 <= p <= 400
            or not math.isfinite(b) or not 0 <= b <= 0.8):
        raise ValueError("generated research config outside bounded strategy space")
    return {k: config[k] for k in CONFIG_KEYS}


def generate_source(*, config: dict, candidate_id: str,
                    data_sha: str, source_state_sha: str) -> str:
    """Fixed-source template; NO external text, imports or expressions injected."""
    config = validate_model(config)
    for label, value in (
        ("candidate ID", candidate_id), ("draw data SHA", data_sha),
        ("state SHA", source_state_sha)
    ):
        if not isinstance(value, str) or (
            len(value) != (20 if label == "candidate ID" else 64)
            or any(c not in "0123456789abcdef" for c in value)
        ):
            raise ValueError("invalid source provenance for " + label)
    source = (
        "# GENERATED RESEARCH MODEL — NOT AN AUTHORIZED PRODUCTION CHAMPION\n"
        f"# {VERSION}; input draw sha256: {data_sha}\n"
        "from __future__ import annotations\n"
        "from autonomous_evolution_lab import prior_probabilities\n"
        f"CANDIDATE_ID = {candidate_id!r}\n"
        f"SOURCE_STATE_SHA256 = {source_state_sha!r}\n"
        f"DRAW_HISTORY_SHA256 = {data_sha!r}\n"
        f"CONFIG = {stable_json(config)}\n"
        "def probability_vector(prior_history):\n"
        "    # Uses history strictly BEFORE the target draw.\n"
        "    return prior_probabilities(prior_history, CONFIG)\n"
    )
    # The AST allowlist plus deterministic regeneration reject attempts to
    # embed unreviewed paper instructions or arbitrary executable code.
    tree = ast.parse(source)
    if [type(s).__name__ for s in tree.body] != [
        "ImportFrom", "ImportFrom", "Assign", "Assign",
        "Assign", "Assign", "FunctionDef"
    ]:
        raise ValueError("unexpected generated AST statements")
    import_stmt = tree.body[1]
    if (not isinstance(import_stmt, ast.ImportFrom)
            or import_stmt.module != "autonomous_evolution_lab"
            or [a.name for a in import_stmt.names] != ["prior_probabilities"]):
        raise ValueError("code generator changed its validated import")
    return source


def find_learned_state(root: Path, info: dict) -> tuple[dict | None, str]:
    state_path = root / "loto7_agent_output" / lab.STATE
    ledger_path = root / "loto7_agent_output" / lab.LEDGER
    chain = lab.read_chain(ledger_path)
    if not state_path.exists():
        if chain:
            raise ValueError("autonomous ledger exists without state")
        return None, "no_prior_autonomous_learning"
    state = lab.load_required(state_path)
    if (not chain or state.get("version") != lab.VERSION
            or state.get("sequence") != len(chain)
            or state.get("last_record_sha256") != chain[-1]["record_sha256"]
            or state.get("data_sha256") != chain[-1]["data_sha256"]):
        raise ValueError("autonomous learned state or hash ledger mismatched")
    if state.get("data_sha256") != info["data_sha256"]:
        return None, "research_learning_snapshot_stale"
    if state.get("latest_round") != info["latest_round"]:
        raise ValueError("learned state target round is inconsistent")
    if state.get("trusted_source") is not True:
        return None, "unverified_learning_source"
    trials = state.get("trials")
    if (not isinstance(trials, list) or len(trials) > lab.MAX_TRIALS_PER_DRAW_SHA
            or len({lab.canonical(t["config"]) for t in trials}) != len(trials)):
        raise ValueError("invalid learned trial history")
    for i, t in enumerate(trials, 1):
        cfg = validate_model(t["config"])
        if (t.get("trial") != i or t.get("candidate_id") !=
            lab.digest((info["data_sha256"] + "|" + lab.canonical(cfg)).encode())[:20]
            or t.get("diagnostic", {}).get("independent_future_evidence") is not False
            or t.get("diagnostic", {}).get("production_eligible") is not False):
            raise ValueError("learned trial provenance/authority mismatch")
    return state, "learned_state_verified"


def prospective_promotion_status(root: Path, info: dict) -> dict:
    """Read-only *diagnostic* of the EXISTING automated OOS promotion gates."""
    out = root / "loto7_agent_output"
    champion = lab.load_required(out / "model_champion.json")
    oos = lab.load_required(out / "oos_candidate_state.json")
    current = champion.get("model_version")
    if not isinstance(current, str) or not current:
        raise ValueError("missing production champion identity")
    if not info["trusted"]:
        matches = []
    else:
        matches = ensemble.promotion_candidates(v4, oos, current)
    eligible = []
    for rank, record in matches:
        cfg = v4.cfg_from_obj(record.get("config"))
        if (cfg is None or cfg.version() != record.get("candidate_version")
                or record.get("champion_version") != current
                or not record.get("strict_random_valid")
                or not record.get("strict_matched_ensemble_valid")):
            raise ValueError("inconsistent OOS promotion evidence")
        eligible.append({
            "candidate_version": cfg.version(),
            "trusted_future_draws": int(record["trusted_draws"]),
            "matched_trusted_draws": int(record["matched_ensemble_trusted_draws"]),
            "family_adjusted_e_value": float(record["family_adjusted_e_value"]),
            "rank": float(rank),
        })
    return {
        "current_champion": current,
        "eligible_existing_oos_candidates": eligible,
        "operational_promotion_path": "existing_research_v4_no_production_strict_oos",
        "automated_when_new_verified_draw_is_graded": True,
        "needs_new_verified_draw": True,
        "candidate_research_source_itself_eligible": False,
        "early_retroactive_promotion_allowed": False,
        "source_verified_for_current_read": info["trusted"],
    }


def plan(root: Path) -> tuple[dict, str | None]:
    root = root.resolve()
    info, history = lab.inspect(root)
    if len(history) < lab.MIN_TRAIN + lab.EVAL_ROUNDS:
        raise ValueError("need chronological learning history")
    state, reason = find_learned_state(root, info)
    result = {
        "version": VERSION, "latest_round": info["latest_round"],
        "draw_data_sha256": info["data_sha256"],
        "research_mode": info["research_mode"],
        "trusted_latest_source": info["trusted"],
        "official_trials_used": info["official_trials_used"],
        "official_trial_limit": info["official_trial_limit"],
        "existing_lab_reason": reason,
        "auto_research_source_rewrite": False,
        "new_experiment_trials": 0,
        "source_authority": "research_only_not_loaded_by_production",
        "promotion": prospective_promotion_status(root, info),
        "champion_changed": False,
        "frozen_future_oos_modified": False,
        "existing_production_tickets_modified": False,
        "authority": {
            "autonomous_research_code_template": True,
            "automatic_learned_trial_selection": True,
            "untrusted_paper_code_execution": False,
            "override_research_trial_budget": False,
            "overwrite_production_code": False,
            "rewrite_locked_future_forecasts": False,
            "promote_historical_winner_directly": False,
        },
    }
    # A stale, untrusted or empty laboratory cannot generate a program.
    if not info["trusted"] or state is None or not state["trials"]:
        result["decision"] = "WAIT_FOR_TRUSTED_RESEARCH_LEADER"
        return result, None
    winner = max(state["trials"], key=lambda t: (
        t["diagnostic"]["mean_log_edge"], -t["trial"]
    ))
    if state.get("diagnostic_leader") != winner["candidate_id"]:
        raise ValueError("learned leader mismatch")
    cfg = validate_model(winner["config"])
    # Deterministically recompute the stored retrospective statistics before
    # turning the selected model into a persistent program. Does NOT search
    # new configurations, reopen a research budget, or enter future OOS.
    actual = lab.score_candidate(history, cfg)
    stored = winner["diagnostic"]
    if (actual.keys() != stored.keys()
            or any(abs(float(a) - float(b)) > 1e-10
                   for k in ("mean_log_edge", "mean_top7_hits")
                   for a, b in [(actual[k], stored[k])])
            or actual["chronological_block_log_edges"] !=
               stored["chronological_block_log_edges"]):
        raise ValueError("historical learned result cannot be independently reproduced")
    state_sha = hashlib.sha256(
        (root / "loto7_agent_output" / lab.STATE).read_bytes()
    ).hexdigest()
    source = generate_source(config=cfg, candidate_id=winner["candidate_id"],
                             data_sha=info["data_sha256"], source_state_sha=state_sha)
    result.update({
        "decision": "GENERATE_RESEARCH_SOURCE_ONLY",
        "auto_research_source_rewrite": True,
        "learned_candidate_id": winner["candidate_id"],
        "source_sha256": fingerprint(source.encode("utf-8")),
        "source_state_sha256": state_sha,
        "learned_config": cfg,
        "historical_log_edge": actual["mean_log_edge"],
        "historical_only_not_independent": True,
    })
    return result, source


def apply(root: Path, output: Path) -> dict:
    report, source = plan(root)
    if source is None:
        return report
    output.mkdir(parents=True, exist_ok=True)
    path = output / SOURCE
    manifest = output / MANIFEST
    path.write_text(source, encoding="utf-8")
    manifest.write_text(
        json.dumps(report, ensure_ascii=False, sort_keys=True,
                   indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    if fingerprint(path.read_bytes()) != report["source_sha256"]:
        raise ValueError("generated source is not exactly reproducible")
    return report


def main() -> int:
    p = argparse.ArgumentParser(description="Autonomous learned research source rewrite")
    p.add_argument("--repo-root", type=Path, default=Path("."))
    p.add_argument("--out-dir", type=Path, default=GENERATED)
    args = p.parse_args()
    state = apply(args.repo_root, args.out_dir)
    print(stable_json({
        "action": state["decision"],
        "leader": state.get("learned_candidate_id"),
        "promotion_eligible": len(state["promotion"]["eligible_existing_oos_candidates"]),
        "new_optimizer_trials": state["new_experiment_trials"],
        "champion_changed": state["champion_changed"],
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
