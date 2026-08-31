#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import copy
import sys
from pathlib import Path
from typing import Optional, Sequence

import strict_oos_governance as strict

MIGRATION_VERSION = "strict-oos-evidence-boundary-v1"


def _args(argv: Optional[Sequence[str]] = None):
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--csv", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, default=Path("loto7_agent_output"))
    ap.add_argument("--shadow-registry", type=Path, default=Path("loto7_agent_output/shadow_registry.json"))
    args, _ = ap.parse_known_args(list(argv) if argv is not None else sys.argv[1:])
    return args


def migrate(v4, argv: Optional[Sequence[str]] = None):
    args = _args(argv)
    df = v4.read_csv_flexible(args.csv)
    x, clean = v4.make_history(df)
    round_text = str(clean["回別"].iloc[-1]) if "回別" in clean.columns else ""
    latest_round = v4.parse_round(round_text) or int(len(x))

    registry = strict.load_json(args.shadow_registry, {})
    formal_path = args.out_dir / "formal_challenger_state.json"
    oos_path = args.out_dir / "oos_candidate_state.json"
    formal = strict.load_json(formal_path, {})
    oos = strict.load_json(oos_path, {})
    if not registry or not formal or not oos:
        return {"migrated": False, "reason": "state_not_ready"}
    if oos.get("strict_evidence_migration") == MIGRATION_VERSION:
        return {"migrated": False, "reason": "already_migrated"}

    target_round = int(registry.get("target_round", -1))
    if target_round <= int(latest_round):
        return {"migrated": False, "reason": "no_future_boundary"}

    candidate = str(formal.get("candidate_version", ""))
    champion = str(formal.get("champion_version", registry.get("champion_version", "")))
    evidence = oos.get("evidence") if isinstance(oos.get("evidence"), dict) else {}
    key = v4.e_key(candidate, champion) if candidate and champion else ""
    rec = evidence.get(key, {}) if key else {}
    trusted = int(rec.get("trusted_draws", 0) or 0) if isinstance(rec, dict) else 0
    random_trusted = int(rec.get("random_trusted_draws", 0) or 0) if isinstance(rec, dict) else 0

    if trusted > 0 and random_trusted == 0:
        oos["legacy_pre_strict_evidence"] = {
            "archived_at_jst": v4.now_jst(),
            "candidate_version": candidate,
            "champion_version": champion,
            "through_round": rec.get("last_round") if isinstance(rec, dict) else None,
            "snapshot": copy.deepcopy(rec),
            "reason": "paired_random_reference_not_prefrozen_for_legacy_draws",
        }
        evidence.pop(key, None)
        oos["evidence"] = evidence
        formal["trusted_draws_so_far"] = 0
        formal["last_observed_round"] = None
        formal["strict_evidence_start_target_round"] = target_round
        formal["strict_evidence_reset_at_jst"] = v4.now_jst()
        reset = True
    else:
        reset = False

    oos["strict_evidence_migration"] = MIGRATION_VERSION
    oos["strict_evidence_start_target_round"] = target_round
    oos["strict_evidence_legacy_draws_discarded_from_promotion"] = trusted if reset else 0
    strict.write_json(formal_path, formal)
    strict.write_json(oos_path, oos)
    return {
        "migrated": True,
        "evidence_reset": reset,
        "legacy_trusted_draws": trusted if reset else 0,
        "strict_start_target_round": target_round,
    }
