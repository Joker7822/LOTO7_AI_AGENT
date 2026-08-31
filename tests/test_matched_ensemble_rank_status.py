import matched_ensemble_status as status


def test_render_rank_diagnostics_after_one_trusted_draw():
    registry = {
        "target_round": 693,
        "matched_ensemble_version": "matched-permutation-ensemble-v1",
        "matched_ensemble_size": 32,
        "matched_ensemble_frozen_at_jst": "2026-08-31T20:08:29+09:00",
        "matched_reference_frozen_at_jst": "2026-08-31T15:59:33+09:00",
        "champion_version": "champion",
    }
    rec = {
        "candidate_version": "candidate",
        "champion_version": "champion",
        "matched_ensemble_trusted_draws": 1,
        "matched_ensemble_sum_delta": 0.1,
        "matched_ensemble_wins": 1,
        "matched_ensemble_e_value_raw": 1.1,
        "family_adjusted_e_value": 0.55,
        "matched_ensemble_rank_trusted_draws": 1,
        "matched_ensemble_rank_percentile_sum": 96.875,
        "matched_ensemble_rank_permutation_p_sum": 2.0 / 33.0,
        "last_matched_ensemble_rank_rank_round": 693,
        "last_matched_ensemble_rank_percentile_midrank": 96.875,
        "last_matched_ensemble_rank_permutation_p_upper": 2.0 / 33.0,
        "last_matched_ensemble_rank_midrank_from_top": 2.0,
        "last_matched_ensemble_rank_null_below": 31,
        "last_matched_ensemble_rank_null_equal": 0,
        "last_matched_ensemble_rank_null_above": 1,
        "matched_ensemble_rank_minimum_possible_p": 1.0 / 33.0,
    }
    oos = {
        "matched_ensemble_rank_diagnostics_version": "matched-ensemble-rank-diagnostics-v1",
        "evidence": {"k": rec},
    }
    formal = {"candidate_version": "candidate", "champion_version": "champion"}
    holdout = {
        "horizon_trusted_draws": 26,
        "matched_ensemble_rank_trusted_draws": 1,
        "matched_ensemble_rank_percentile_sum": 93.75,
        "matched_ensemble_rank_permutation_p_sum": 3.0 / 33.0,
        "last_matched_ensemble_rank_rank_round": 693,
        "last_matched_ensemble_rank_percentile_midrank": 93.75,
        "last_matched_ensemble_rank_permutation_p_upper": 3.0 / 33.0,
        "last_matched_ensemble_rank_midrank_from_top": 3.0,
    }
    holdout_registry = {"matched_ensemble_frozen_at_jst": "2026-08-31T20:08:29+09:00"}

    text = "\n".join(status.render(registry, oos, formal, holdout, holdout_registry))
    assert "Rank診断版: **matched-ensemble-rank-diagnostics-v1**" in text
    assert "diagnostic only" in text
    assert "0.0303" in text
    assert "96.88%" in text
    assert "0.0606" in text
    assert "2.0/33位相当" in text
    assert "31/0/1" in text
    assert "Holdout Rank診断: **1/26 trusted draws**" in text


def test_render_rank_diagnostics_before_first_draw():
    registry = {
        "target_round": 693,
        "matched_ensemble_version": "matched-permutation-ensemble-v1",
        "matched_ensemble_size": 32,
        "matched_ensemble_frozen_at_jst": "2026-08-31T20:08:29+09:00",
        "champion_version": "champion",
    }
    oos = {"matched_ensemble_rank_diagnostics_version": "matched-ensemble-rank-diagnostics-v1"}
    formal = {"candidate_version": "candidate", "champion_version": "champion"}
    holdout = {"horizon_trusted_draws": 26, "matched_ensemble_rank_minimum_possible_p": 1.0 / 33.0}
    text = "\n".join(status.render(registry, oos, formal, holdout, {}))
    assert "Rank診断 trusted OOS: **0/8回**" in text
    assert "未採点" in text
    assert "Holdout Rank診断: **0/26 trusted draws（未採点）**" in text
