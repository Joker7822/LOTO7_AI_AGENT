import json

import research_cycle_guard as guard
import robust_signal_optimizer as robust


def test_parse_generation_from_model():
    assert guard.parse_generation_from_model("signal-g02253-c01-b6030e66c9") == 2253
    assert guard.parse_generation_from_model("feedback-g00625-c01") == 625
    assert guard.parse_generation_from_model("baseline-5fdb8dc2ad") is None


def test_guard_pauses_after_parent_plateau():
    result = guard.decide_guard(
        data_sha="sha-a",
        generation=2600,
        last_data_change_generation=1,
        parent_version="signal-g02253-c01-b6030e66c9",
        signal_trials_total=700,
        previous={"data_sha256": "sha-a"},
        max_trials=800,
        max_stale_generations=300,
    )
    assert result["search_enabled"] is False
    assert result["mode"] == "VALIDATION_ONLY"
    assert result["signal_trials_this_data"] == 700
    assert "signal_parent_plateau" in result["reasons"]


def test_guard_waits_after_matched_validation_complete():
    result = guard.decide_guard(
        data_sha="sha-a",
        generation=2600,
        last_data_change_generation=1,
        parent_version="signal-g02253-c01-b6030e66c9",
        signal_trials_total=700,
        previous={"data_sha256": "sha-a"},
        max_trials=800,
        max_stale_generations=300,
        validation_complete=True,
    )
    assert result["search_enabled"] is False
    assert result["mode"] == "WAIT_FOR_NEW_DATA"
    assert "matched_null_calibration_complete" in result["reasons"]


def test_guard_reopens_new_data_with_fresh_budget_and_plateau_clock():
    result = guard.decide_guard(
        data_sha="sha-b",
        generation=2600,
        last_data_change_generation=1,
        parent_version="signal-g02253-c01-b6030e66c9",
        signal_trials_total=900,
        previous={
            "data_sha256": "sha-a",
            "trial_counter_at_data_start": 0,
            "data_start_generation": 1,
        },
        max_trials=800,
        max_stale_generations=300,
        validation_complete=True,
    )
    assert result["search_enabled"] is True
    assert result["mode"] == "SEARCH"
    assert result["reasons"] == ["new_data_reopens_search"]
    assert result["trial_counter_at_data_start"] == 900
    assert result["signal_trials_this_data"] == 0
    assert result["plateau_anchor_generation"] == 2600
    assert result["generations_since_plateau_anchor"] == 0


def test_guard_new_data_budget_remains_open_on_following_generation():
    first = guard.decide_guard(
        data_sha="sha-b",
        generation=2600,
        last_data_change_generation=1,
        parent_version="signal-g02253-c01-b6030e66c9",
        signal_trials_total=900,
        previous={"data_sha256": "sha-a"},
        max_trials=800,
        max_stale_generations=300,
    )
    second = guard.decide_guard(
        data_sha="sha-b",
        generation=2602,
        last_data_change_generation=2601,
        parent_version="signal-g02253-c01-b6030e66c9",
        signal_trials_total=904,
        previous=first,
        max_trials=800,
        max_stale_generations=300,
    )
    assert second["search_enabled"] is True
    assert second["signal_trials_this_data"] == 4
    assert second["plateau_anchor_generation"] == 2601
    assert second["generations_since_plateau_anchor"] == 1


def test_matched_validation_complete_requires_same_sha_and_budget(tmp_path):
    p = tmp_path / "matched_budget_null_calibration_summary.json"
    p.write_text(json.dumps({
        "data_sha256": "sha-a",
        "matched_signal_trial_budget": 708,
        "calibration_complete": True,
    }), encoding="utf-8")
    assert guard.matched_validation_complete(tmp_path, "sha-a", 708) is True
    assert guard.matched_validation_complete(tmp_path, "sha-b", 708) is False
    assert guard.matched_validation_complete(tmp_path, "sha-a", 700) is False


def _eras(values):
    return [{"signal_objective": v} for v in values]


def test_era_gate_accepts_broad_improvement():
    ok, detail = robust.era_accept(
        _eras([-0.030, -0.020, -0.010, -0.040]),
        _eras([-0.031, -0.022, -0.011, -0.041]),
    )
    assert ok is True
    assert detail["improved_era_count"] >= 2


def test_era_gate_rejects_one_era_overfit():
    ok, detail = robust.era_accept(
        _eras([-0.020, -0.020, -0.010, -0.060]),
        _eras([-0.030, -0.021, -0.011, -0.040]),
    )
    assert ok is False
    assert detail["era_checks"]["all_eras_not_materially_regressed"] is False
    assert detail["era_checks"]["worst_era_not_regressed"] is False
