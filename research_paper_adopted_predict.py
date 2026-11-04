#!/usr/bin/env python3
"""Automatically serve a prospectively adopted *research* paper method.

Only a completed, SHA-chain-verified 26-draw forward study can select this
model. Output is read-only research telemetry; no purchasing or Production.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from joint_set_v2_signal_oos_guard import validate_trusted_source
from loto7_evolving_agent import fingerprint_file, make_history, read_csv_flexible
from loto7_v4_runner import parse_round
from paper_method_autonomy import REGISTRY as PAPER_REGISTRY
from paper_method_future_shadow import (
    HORIZON, REGISTRY as FUTURE_REGISTRY, assert_chain, next_probabilities,
)
from research_cycle_round2_replay import sha as digest

OUTPUT = "research/autonomous_paper_methods/adopted_model_preview.json"
VERSION = "paper-prospective-adopted-prediction-v1"
PICKS = 7


def choose_model(state: dict, candidate_registry: dict) -> dict | None:
    if (not state.get("research_adopted")
            or state.get("trusted_grades") != HORIZON
            or not state.get("anytime_e_value", 0) >= 40):
        return None
    reg = state.get("registration")
    if not isinstance(reg, dict) or reg.get("paper_experiments_reproduced") is not False:
        raise ValueError("paper method registration is missing or overclaims replication")
    options = candidate_registry.get("candidates") or [candidate_registry.get("candidate")]
    matches = [o for o in options if isinstance(o, dict)
               and o.get("doi") == reg.get("doi")
               and o.get("fulltext_sha256") == reg.get("paper_sha256")
               and o.get("candidate_expression_sha256") == reg.get("expression_sha256")
               and o.get("candidate_expression") == reg.get("expression")]
    if len(matches) != 1 or matches[0].get("eligible_for_future_only_shadow") is not True:
        raise ValueError("adopted paper model does not match audited full-text provenance")
    return matches[0]


def predict_research(root: Path) -> dict:
    root = root.resolve()
    csv_path = root / "loto7.csv"
    src_path = root / "loto7_agent_output/source_validation.json"
    if validate_trusted_source(csv_path, src_path).get("trusted") is not True:
        raise ValueError("lottery source is not independently corroborated")
    src = json.loads(src_path.read_text(encoding="utf-8"))
    if (src.get("verification_provenance", {}).get("draw_csv_sha256")
            != fingerprint_file(csv_path)):
        raise ValueError("draw history is not bound to trusted source SHA256")
    x, frame = make_history(read_csv_flexible(csv_path))
    if [parse_round(v) for v in frame["回別"]] != list(range(1, len(x) + 1)):
        raise ValueError("nonconsecutive draw IDs")
    study = root / FUTURE_REGISTRY
    if not study.exists():
        return {"status": "no_paper_future_study", "model_selected": False}
    state = json.loads(study.read_text(encoding="utf-8"))
    dates = [v.date().isoformat() for v in frame["抽せん日"]]
    assert_chain(state, x, dates)
    if not state.get("research_adopted"):
        return {"status": "future_evidence_not_yet_sufficient",
                "model_selected": False,
                "trusted_grades": state.get("trusted_grades", 0)}
    candidate = choose_model(
        state, json.loads((root / PAPER_REGISTRY).read_text(encoding="utf-8")))
    if candidate is None:
        raise ValueError("forward-study adoption has invalid proof")
    p = next_probabilities(x, candidate["candidate_expression"])
    tie = np.random.default_rng(20261104 + len(x)).random(37)
    tickets = sorted((np.lexsort((tie, -np.asarray(p)))[:PICKS] + 1).tolist())
    out = {
        "version": VERSION, "status": "automatically_adopted_research_model",
        "candidate_doi": candidate["doi"],
        "fulltext_sha256": candidate["fulltext_sha256"],
        "expression_sha256": candidate["candidate_expression_sha256"],
        "future_study_evidence_tip_sha256": state["events"][-1]["event_sha256"],
        "future_study_confirmed_draws": state["trusted_grades"],
        "future_study_e_value": state["anytime_e_value"],
        "target_round": len(x) + 1,
        "prior_history_sha256": digest([[int(v) for v in row] for row in x]),
        "probabilities_37": p, "top_seven_research_ticket": tickets,
        "production_or_champion_modified": False,
        "purchasing_authorized": False,
        "original_paper_experiments_reproduced": False,
    }
    path = root / OUTPUT
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(out, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if not path.exists() or path.read_text(encoding="utf-8") != text:
        path.write_text(text, encoding="utf-8")
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    args = parser.parse_args()
    out = predict_research(args.repo_root)
    print(json.dumps({"status": out["status"],
                      "model_selected": out["status"] == "automatically_adopted_research_model",
                      "target_round": out.get("target_round"),
                      "production_or_champion_modified": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()
