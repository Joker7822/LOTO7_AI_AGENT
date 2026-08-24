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
    assert "signal_parent_plateau" in result["reasons"]


def test_guard_reopens_on_new_data_sha():
    result = guard.decide_guard(
        data_sha="sha-b",
        generation=2600,
        last_data_change_generation=1,
        parent_version="signal-g02253-c01-b6030e66c9",
        signal_trials_total=900,
        previous={"data_sha256": "sha-a"},
        max_trials=800,
        max_stale_generations=300,
    )
    assert result["search_enabled"] is True
    assert result["reasons"] == ["new_data_reopens_search"]


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
