#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional, Sequence

import loto7_v4_runner as v4
import strict_oos_governance as strict
import strict_oos_migration


def run(argv: Optional[Sequence[str]] = None) -> dict:
    args = strict._cli_context(argv)
    migration = strict_oos_migration.migrate(v4, argv)
    bootstrap = strict.bootstrap_before_main(v4, argv)

    registry = strict.load_json(args.shadow_registry, {})
    target_round = int(registry.get("target_round", -1)) if registry else -1
    latest_round = int(bootstrap.get("latest_round", -1))
    future_registry_ready = bool(registry) and target_round > latest_round

    status = "ok"
    reasons = []
    if future_registry_ready and not bootstrap.get("random_ready"):
        status = "failed"
        reasons.append("future_random_reference_not_frozen")
    if future_registry_ready and not bootstrap.get("holdout_ready"):
        status = "failed"
        reasons.append("future_holdout_not_frozen")

    result = {
        "version": strict.VERSION,
        "status": status,
        "latest_round": latest_round,
        "target_round": target_round,
        "future_registry_ready": future_registry_ready,
        "random_ready": bool(bootstrap.get("random_ready")),
        "holdout_ready": bool(bootstrap.get("holdout_ready")),
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
