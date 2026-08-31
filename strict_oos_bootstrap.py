#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional, Sequence

import loto7_v4_runner as v4
import matched_ensemble_rank_diagnostics as matched_rank
import matched_permutation_ensemble as matched_ensemble
import matched_permutation_oos as matched
import strict_oos_governance as strict
import strict_oos_migration


def run(argv: Optional[Sequence[str]] = None) -> dict:
    args = strict._cli_context(argv)
    migration = strict_oos_migration.migrate(v4, argv)
    bootstrap = strict.bootstrap_before_main(v4, argv)
    matched_bootstrap = matched.bootstrap_before_main(v4, argv)
    ensemble_bootstrap = matched_ensemble.bootstrap_before_main(v4, argv)
    rank_bootstrap = matched_rank.bootstrap_before_main(v4, argv)

    registry = strict.load_json(args.shadow_registry, {})
    target_round = int(registry.get("target_round", -1)) if registry else -1
    latest_round = int(bootstrap.get("latest_round", -1))
    future_registry_ready = bool(registry) and target_round > latest_round

    status = "ok"
    reasons = []
    if future_registry_ready and not bootstrap.get("random_ready"):
        status = "failed"
        reasons.append("future_random_reference_not_frozen")
    if future_registry_ready and not matched_bootstrap.get("matched_ready"):
        status = "failed"
        reasons.append("future_matched_permutation_reference_not_frozen")
    if future_registry_ready and not ensemble_bootstrap.get("matched_ensemble_ready"):
        status = "failed"
        reasons.append("future_matched_permutation_ensemble_not_frozen")
    if future_registry_ready and not bootstrap.get("holdout_ready"):
        status = "failed"
        reasons.append("future_holdout_not_frozen")
    if future_registry_ready and not matched_bootstrap.get("holdout_matched_ready"):
        status = "failed"
        reasons.append("future_holdout_matched_reference_not_frozen")
    if future_registry_ready and not ensemble_bootstrap.get("holdout_matched_ensemble_ready"):
        status = "failed"
        reasons.append("future_holdout_matched_ensemble_not_frozen")

    result = {
        "version": strict.VERSION,
        "matched_reference_version": matched.VERSION,
        "matched_ensemble_version": matched_ensemble.VERSION,
        "matched_ensemble_size": matched_ensemble.ENSEMBLE_SIZE,
        "matched_ensemble_rank_diagnostics_version": matched_rank.VERSION,
        "matched_ensemble_rank_minimum_possible_p": rank_bootstrap.get("minimum_possible_p"),
        "matched_ensemble_rank_promotion_role": rank_bootstrap.get("promotion_role"),
        "status": status,
        "latest_round": latest_round,
        "target_round": target_round,
        "future_registry_ready": future_registry_ready,
        "random_ready": bool(bootstrap.get("random_ready")),
        "matched_ready": bool(matched_bootstrap.get("matched_ready")),
        "matched_ensemble_ready": bool(ensemble_bootstrap.get("matched_ensemble_ready")),
        "holdout_ready": bool(bootstrap.get("holdout_ready")),
        "holdout_matched_ready": bool(matched_bootstrap.get("holdout_matched_ready")),
        "holdout_matched_ensemble_ready": bool(ensemble_bootstrap.get("holdout_matched_ensemble_ready")),
        "promotion_intersection": "champion_and_uniform_random_and_matched_ensemble32",
        "migration": migration,
        "reasons": reasons,
        "checked_at_jst": v4.now_jst(),
    }
    strict.write_json(args.out_dir / "strict_oos_bootstrap_state.json", result)
    return result


def main(argv: Optional[Sequence[str]] = None) -> int:
    result = run(argv if argv is not None else sys.argv[1:])
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
