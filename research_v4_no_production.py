#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import formal_challenger
import loto7_v4_runner as v4
import matched_permutation_oos as matched_oos
import strict_oos_governance as strict_oos
import strict_oos_migration


def _skip_production_outputs(*args, **kwargs):
    return {
        "cached": True,
        "skipped": True,
        "reason": "weekly_production_published_only_at_friday_17_jst",
    }


def main() -> int:
    # Research/OOS processing may update the Champion state, but must never publish
    # or overwrite the frozen weekly Production forecast.
    v4.ensure_production_outputs = _skip_production_outputs

    # Tighten Future-OOS governance without changing retrospective Research ranking:
    # - archive legacy one-sided OOS evidence at the migration boundary,
    # - compare each formal challenger with pre-frozen Champion and equal-budget Random,
    # - add a geometry-matched label-permutation null to isolate number-selection signal,
    # - spend e-capital across sequential challenger blocks,
    # - maintain a separate fixed 26-trusted-draw prospective holdout.
    strict_oos.install(v4)
    matched_oos.install(v4)
    strict_oos_migration.migrate(v4)
    strict_oos.bootstrap_before_main(v4)
    matched_oos.bootstrap_before_main(v4)
    rc = v4.main()
    strict_oos.finalize_after_main(v4, formal_challenger)
    matched_oos.finalize_after_main(v4)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
