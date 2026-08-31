import v4_status as status


def test_strict_evidence_lines_show_paired_metrics():
    rec = {
        "trusted_draws": 8,
        "random_trusted_draws": 8,
        "matched_trusted_draws": 8,
        "sum_delta": 0.8,
        "random_sum_delta": 0.4,
        "matched_sum_delta": 1.2,
        "wins": 5,
        "random_wins": 6,
        "matched_wins": 7,
        "strict_random_valid": True,
        "strict_matched_valid": True,
        "champion_e_value_raw": 45.0,
        "random_e_value_raw": 52.0,
        "matched_e_value_raw": 47.0,
        "family_adjusted_e_value": 22.5,
        "required_raw_e_value": 40.0,
    }
    text = "\n".join(status.strict_evidence_lines(rec))
    assert "8回** / Random比較 trusted: **8回" in text
    assert "Matched比較 trusted: **8回" in text
    assert "+0.1000 / +0.0500 / +0.1500" in text
    assert "62.5% / 75.0% / 87.5%" in text
    assert "45.0000" in text
    assert "52.0000" in text
    assert "47.0000" in text
    assert "22.5000" in text
    assert "40.00" in text
    assert "Random reference valid: **YES**" in text
    assert "Matched reference valid: **YES**" in text


def test_strict_evidence_lines_do_not_mislabel_legacy_only_evidence():
    rec = {
        "trusted_draws": 1,
        "sum_delta": 0.0,
        "wins": 0,
        "e_value": 1.0,
    }
    text = "\n".join(status.strict_evidence_lines(rec))
    assert "移行済み・次回採点待ち" in text
    assert "Random比較 trusted: **0回**" in text
    assert "Matched比較 trusted: **0回**" in text
    assert "まだ3-way strict採点なし" in text


def test_holdout_lines_render_progress_and_three_references():
    holdout = {
        "status": "active",
        "locked_candidate_version": "candidate-v1",
        "trusted_draws": 4,
        "matched_trusted_draws": 4,
        "horizon_trusted_draws": 26,
        "sum_delta_vs_champion": 0.8,
        "sum_delta_vs_random": -0.4,
        "sum_delta_vs_matched": 0.2,
        "wins_vs_champion": 3,
        "wins_vs_random": 2,
        "wins_vs_matched": 3,
        "champion_e_value": 1.4,
        "random_e_value": 0.9,
        "matched_e_value": 1.2,
    }
    registry = {"target_round": 697, "matched_reference_frozen_at_jst": "2026-09-01T10:00:00+09:00"}
    text = "\n".join(status.holdout_lines(holdout, registry))
    assert "4/26 trusted draws" in text
    assert "Matched **4/26**" in text
    assert "第697回" in text
    assert "+0.2000 / -0.1000 / +0.0500" in text
    assert "75.0% / 50.0% / 75.0%" in text
    assert "1.4000 / 0.9000 / 1.2000" in text
    assert "Matched reference frozen: **YES**" in text


def test_formal_lines_show_multiplicity_threshold():
    formal = {
        "candidate_version": "candidate-v1",
        "block_id": "block",
        "block_start_target_round": 693,
        "trusted_draws_so_far": 0,
        "minimum_trusted_draws": 8,
        "formal_block_index": 2,
        "family_weight": 1 / 6,
        "required_raw_e_value": 120.0,
    }
    registry = {"target_round": 693, "promotion_candidate_count": 1}
    text = "\n".join(status.formal_lines(formal, registry))
    assert "strict block index: **2**" in text
    assert "0/8回" in text
    assert "120.00" in text
    assert "matched permutation" in text
