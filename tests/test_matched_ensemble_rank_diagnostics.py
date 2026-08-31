import csv
import json
from pathlib import Path

import loto7_v4_runner as v4
import matched_ensemble_rank_diagnostics as rank
import matched_permutation_ensemble as ensemble
import matched_permutation_oos as single


def sample_tickets():
    return [
        [1, 2, 3, 4, 5, 6, 7],
        [1, 2, 8, 9, 10, 11, 12],
        [1, 3, 8, 13, 14, 15, 16],
        [2, 4, 9, 13, 17, 18, 19],
        [5, 6, 10, 14, 17, 20, 21],
    ]


def test_rank_diagnostics_best_and_worst_resolution():
    best = rank.rank_diagnostics(100.0, list(range(32)))
    assert best["null_below"] == 32
    assert best["null_equal"] == 0
    assert best["null_above"] == 0
    assert best["candidate_midrank_from_top"] == 1.0
    assert best["percentile_midrank"] == 100.0
    assert abs(best["permutation_p_upper"] - 1.0 / 33.0) < 1e-12

    worst = rank.rank_diagnostics(-1.0, list(range(32)))
    assert worst["null_below"] == 0
    assert worst["null_equal"] == 0
    assert worst["null_above"] == 32
    assert worst["candidate_midrank_from_top"] == 33.0
    assert worst["percentile_midrank"] == 0.0
    assert worst["permutation_p_upper"] == 1.0


def test_rank_diagnostics_midrank_ties():
    null = [9.0] * 20 + [10.0] * 2 + [11.0] * 10
    d = rank.rank_diagnostics(10.0, null)
    assert d["null_below"] == 20
    assert d["null_equal"] == 2
    assert d["null_above"] == 10
    assert abs(d["percentile_midrank"] - 65.625) < 1e-12
    assert abs(d["candidate_midrank_from_top"] - 12.0) < 1e-12
    assert abs(d["permutation_p_upper"] - 13.0 / 33.0) < 1e-12


def test_rank_grade_records_csv_and_does_not_change_promotion_evidence(tmp_path: Path):
    out = tmp_path / "out"
    out.mkdir()
    result_path = out / "shadow_oos_results.csv"
    tickets = sample_tickets()
    members = ensemble._ensemble_for_tickets(tickets, ensemble.permutations_for_round(700))
    registry = {
        "target_round": 700,
        "champion_version": "champion",
        "matched_ensemble_frozen_at_jst": "2026-09-01T06:00:00+09:00",
        "matched_ensemble_by_candidate": {"candidate": members},
        "candidates": [{"version": "candidate", "tickets": tickets}],
    }
    key = v4.e_key("candidate", "champion")
    rec = {
        "candidate_version": "candidate",
        "champion_version": "champion",
        "family_adjusted_e_value": 12.345,
        "e_value": 12.345,
    }
    state = {"evidence": {key: rec}}

    rank._grade_rank(
        v4, registry, 700, "2026-10-23", set(range(1, 8)),
        "verified_two_result_sources", True, state, result_path,
    )
    updated = state["evidence"][key]
    assert updated["matched_ensemble_rank_trusted_draws"] == 1
    assert updated["matched_ensemble_rank_diagnostics_version"] == rank.VERSION
    assert 0.0 <= updated["last_matched_ensemble_rank_percentile_midrank"] <= 100.0
    assert 1.0 / 33.0 <= updated["last_matched_ensemble_rank_permutation_p_upper"] <= 1.0
    assert updated["family_adjusted_e_value"] == 12.345
    assert updated["e_value"] == 12.345
    assert state["matched_ensemble_rank_promotion_role"] == "diagnostic_only"

    csv_path = out / "matched_ensemble_rank_results.csv"
    assert csv_path.exists()
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))
    assert len(rows) == 1
    assert rows[0]["candidate_version"] == "candidate"
    assert rows[0]["ensemble_size"] == "32"


def test_holdout_rank_is_recorded_from_prefrozen_ensemble(tmp_path: Path):
    out = tmp_path / "out"
    out.mkdir()
    tickets = sample_tickets()
    members = ensemble._ensemble_for_tickets(tickets, ensemble.permutations_for_round(700))
    registry = {
        "target_round": 700,
        "holdout_tickets": tickets,
        "matched_ensemble_tickets": members,
        "matched_ensemble_frozen_at_jst": "2026-09-01T06:00:00+09:00",
    }
    state = {
        "locked_candidate_version": "candidate",
        "horizon_trusted_draws": 26,
    }
    (out / "future_holdout_registry.json").write_text(json.dumps(registry), encoding="utf-8")
    (out / "future_holdout_state.json").write_text(json.dumps(state), encoding="utf-8")

    rank._grade_holdout_rank(
        v4, out, 700, "2026-10-23", set(range(1, 8)),
        "verified_two_result_sources", True,
    )
    updated = json.loads((out / "future_holdout_state.json").read_text(encoding="utf-8"))
    assert updated["matched_ensemble_rank_trusted_draws"] == 1
    assert updated["matched_ensemble_rank_diagnostics_status"] == "active"
    assert updated["matched_ensemble_rank_diagnostics_version"] == rank.VERSION
    assert (out / "future_holdout_matched_ensemble_rank_results.csv").exists()


def test_bootstrap_marks_rank_diagnostics_as_diagnostic_only(tmp_path: Path):
    out = tmp_path / "out"
    out.mkdir()
    (out / "oos_candidate_state.json").write_text("{}", encoding="utf-8")
    (out / "future_holdout_state.json").write_text("{}", encoding="utf-8")
    csv_path = tmp_path / "loto7.csv"
    csv_path.write_text("回別,抽せん日,本数字1,本数字2,本数字3,本数字4,本数字5,本数字6,本数字7\n692,2026-08-28,1,2,3,4,5,6,7\n", encoding="utf-8")
    registry = tmp_path / "shadow_registry.json"
    registry.write_text("{}", encoding="utf-8")

    result = rank.bootstrap_before_main(v4, [
        "--csv", str(csv_path),
        "--out-dir", str(out),
        "--shadow-registry", str(registry),
    ])
    assert result["promotion_role"] == "diagnostic_only"
    assert abs(result["minimum_possible_p"] - 1.0 / 33.0) < 1e-12
    oos = json.loads((out / "oos_candidate_state.json").read_text(encoding="utf-8"))
    assert oos["matched_ensemble_rank_promotion_role"] == "diagnostic_only"
