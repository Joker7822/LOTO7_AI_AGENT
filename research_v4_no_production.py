#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import formal_challenger
import loto7_v4_runner as v4
import matched_ensemble_rank_diagnostics as matched_rank
import matched_ensemble_score_vector_audit as matched_audit
import matched_permutation_ensemble as matched_ensemble
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
    # - preserve the original single geometry-matched permutation for audit telemetry,
    # - use a pre-frozen 32-member geometry-matched permutation ensemble as the
    #   production signal-isolation gate,
    # - record percentile / Monte-Carlo permutation-p rank diagnostics without using
    #   them as an extra Production promotion gate,
    # - precommit hashes of the 32 frozen portfolios and persist the exact realized
    #   32-score vector plus SHA-256 after grading for independent replay,
    # - spend e-capital across sequential challenger blocks,
    # - maintain a separate fixed 26-trusted-draw prospective holdout.
    strict_oos.install(v4)
    matched_oos.install(v4)
    matched_ensemble.install(v4)
    matched_rank.install(v4)
    matched_audit.install(v4)
    strict_oos_migration.migrate(v4)
    strict_oos.bootstrap_before_main(v4)
    matched_oos.bootstrap_before_main(v4)
    matched_ensemble.bootstrap_before_main(v4)
    matched_rank.bootstrap_before_main(v4)
    matched_audit.bootstrap_before_main(v4)
    rc = v4.main()
    strict_oos.finalize_after_main(v4, formal_challenger)
    matched_oos.finalize_after_main(v4)
    matched_ensemble.finalize_after_main(v4)
    matched_rank.finalize_after_main(v4)
    matched_audit.finalize_after_main(v4)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
