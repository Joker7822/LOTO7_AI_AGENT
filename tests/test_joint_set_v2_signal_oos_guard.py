import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import joint_set_v2_signal_oos as shadow
import joint_set_v2_signal_oos_guard as guard


def fixtures(tmp_path):
    csv_path = tmp_path / "loto7.csv"
    csv_path.write_text(
        "抽せん日,本数字,ボーナス数字,回別\n"
        "2026-10-16,05 06 08 14 15 22 29,03 16,第699回\n", encoding="utf-8")
    source_path = tmp_path / "source.json"
    result = {
        "status": "ok", "verification": "verified_two_result_sources",
        "latest": {
            "round": 699, "date": "2026-10-16",
            "main": [5, 6, 8, 14, 15, 22, 29], "bonus": [3, 16],
        },
        "sources": {"rakuten_bank": {
            "round": 699, "date": "2026-10-16",
            "main": [5, 6, 8, 14, 15, 22, 29], "bonus": [3, 16],
        }},
    }
    source_path.write_text(json.dumps(result), encoding="utf-8")
    return csv_path, source_path, result


def test_guard_accepts_verified_source_and_csv(tmp_path):
    csv_path, source_path, _ = fixtures(tmp_path)
    result = guard.validate_trusted_source(csv_path, source_path)
    assert result["round"] == 699
    assert result["trusted"] is True
    assert result["secondary"] == ["rakuten_bank"]


def test_guard_rejects_trusted_main_number_mismatch(tmp_path):
    csv_path, source_path, report = fixtures(tmp_path)
    report["latest"]["main"][-1] = 30
    source_path.write_text(json.dumps(report), encoding="utf-8")
    with pytest.raises(ValueError, match="conflicts"):
        guard.validate_trusted_source(csv_path, source_path)


def test_guard_rejects_trusted_bonus_date_and_secondary_mismatches(tmp_path):
    csv_path, source_path, report = fixtures(tmp_path)
    for change in ("bonus", "date", "secondary"):
        original = json.loads(json.dumps(report))
        if change == "bonus":
            original["latest"]["bonus"] = [3, 17]
        elif change == "date":
            original["latest"]["date"] = "2026-10-23"
        else:
            original["sources"]["rakuten_bank"]["main"][-1] = 37
        source_path.write_text(json.dumps(original), encoding="utf-8")
        with pytest.raises(ValueError):
            guard.validate_trusted_source(csv_path, source_path)


def test_untrusted_source_waits_instead_of_grading(tmp_path):
    csv_path, source_path, report = fixtures(tmp_path)
    report["verification"] = "single_source_only"
    report["latest"]["main"] = [1, 2, 3, 4, 5, 6, 7]
    source_path.write_text(json.dumps(report), encoding="utf-8")
    res = guard.validate_trusted_source(csv_path, source_path)
    assert res["trusted"] is False
    assert res["status"] == "untrusted_wait"


def test_guard_enforces_existing_registered_manifest_and_clean_state(tmp_path):
    for name in (shadow.REGISTRATION_NAME, shadow.STATE_NAME):
        src = Path("loto7_agent_output") / name
        (tmp_path / name).write_bytes(src.read_bytes())
    out = guard.validate_existing_shadow(tmp_path)
    assert out == {"registration_locked": True, "trusted_draws": 0, "current_target": None}
    state_path = tmp_path / shadow.STATE_NAME
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["trusted_draws"] = 1
    state_path.write_text(json.dumps(state), encoding="utf-8")
    with pytest.raises(ValueError, match="count"):
        guard.validate_existing_shadow(tmp_path)


def test_real_registration_lifecycle_699_700_701_702_and_miss(tmp_path, monkeypatch):
    # Runs the actual registered state machine with a synthetic result stream. The
    # computational forecast alone is stubbed to isolate lifecycle/immutability.
    for name in (shadow.REGISTRATION_NAME, shadow.STATE_NAME):
        src = Path("loto7_agent_output") / name
        (tmp_path / name).write_bytes(src.read_bytes())
    reg_bytes = (tmp_path / shadow.REGISTRATION_NAME).read_bytes()
    scenario = {"round": 699, "trusted": True}

    def fake_history(_unused):
        n = scenario["round"]
        x = np.zeros((n, shadow.N_NUMBERS), dtype=np.int8)
        for i in range(n):
            x[i, [(i + k) % shadow.N_NUMBERS for k in range(7)]] = 1
        date = {699: "2026-10-16", 700: "2026-10-23", 701: "2026-10-30",
                702: "2026-11-06", 703: "2026-11-13", 704: "2026-11-20"}.get(n, "2026-10-16")
        clean = pd.DataFrame([{"回別": f"第{n}回", "抽せん日": pd.Timestamp(date)}])
        return x, clean

    p = np.linspace(0.10, 0.28, shadow.N_NUMBERS)
    p *= shadow.PICKS / float(p.sum())
    def fake_forecast(x, min_train=100, selection_window=120):
        assert len(x) == scenario["round"]
        return {
            "selected_config": shadow.candidate_configs()[0].version(),
            "selected_config_prior_score": 0.0,
            "inclusion_p": p,
            "top7_numbers": [int(i + 1) for i in np.argsort(-p)[:7]],
            "gate": 0.05,
            "gate_diagnostics": {},
            "regime": [1.0, 0.0, 0.0],
        }

    monkeypatch.setattr(shadow, "read_csv_flexible", lambda _: object())
    monkeypatch.setattr(shadow, "make_history", fake_history)
    monkeypatch.setattr(shadow, "fingerprint_file", lambda _: f"sha-{scenario['round']}")
    monkeypatch.setattr(shadow, "build_signal_forecast", fake_forecast)
    monkeypatch.setattr(
        shadow.v4, "source_info",
        lambda _path, _round: (
            "verified_two_result_sources" if scenario["trusted"] else "single_source_only",
            bool(scenario["trusted"]),
        ),
    )

    def run():
        return shadow.run(csv_path=tmp_path / "unused.csv", out_dir=tmp_path,
                          source_report=tmp_path / "unused.json")

    assert run()["status"] == "waiting_for_verified_round_700_prefix"
    assert not (tmp_path / shadow.REGISTRY_NAME).exists()
    scenario.update(round=700, trusted=False)
    assert run()["current_target_round"] is None
    assert not (tmp_path / shadow.REGISTRY_NAME).exists()
    scenario["trusted"] = True
    assert run()["current_target_round"] == 701
    first = json.loads((tmp_path / shadow.REGISTRY_NAME).read_text(encoding="utf-8"))
    assert len(shadow.read_freeze_history(tmp_path / shadow.FREEZE_HISTORY_NAME)) == 1
    assert run()["trusted_draws"] == 0
    assert json.loads((tmp_path / shadow.REGISTRY_NAME).read_text(encoding="utf-8")) == first
    scenario.update(round=701, trusted=False)
    assert run()["trusted_draws"] == 0
    assert not (tmp_path / shadow.RESULTS_NAME).exists()
    scenario["trusted"] = True
    res = run()
    assert res["trusted_draws"] == 1
    assert res["current_target_round"] == 702
    assert len(shadow.read_result_rows(tmp_path / shadow.RESULTS_NAME)) == 1
    assert len(shadow.read_freeze_history(tmp_path / shadow.FREEZE_HISTORY_NAME)) == 2
    assert run()["trusted_draws"] == 1
    assert len(shadow.read_result_rows(tmp_path / shadow.RESULTS_NAME)) == 1
    scenario.update(round=704, trusted=True)  # Missed 702; never backfill it.
    assert run()["status"] == "invalid_missed_prefrozen_target_or_next_freeze"
    assert len(shadow.read_result_rows(tmp_path / shadow.RESULTS_NAME)) == 1
    assert (tmp_path / shadow.REGISTRATION_NAME).read_bytes() == reg_bytes


def test_guard_rejects_registry_without_matching_freeze_history(tmp_path):
    for name in (shadow.REGISTRATION_NAME, shadow.STATE_NAME):
        src = Path("loto7_agent_output") / name
        (tmp_path / name).write_bytes(src.read_bytes())
    reg = json.loads((tmp_path / shadow.REGISTRATION_NAME).read_text(encoding="utf-8"))
    p = np.full(shadow.N_NUMBERS, shadow.PICKS / shadow.N_NUMBERS)
    canonical = shadow.canonical_vector(p)
    registry = {
        "protocol_version": shadow.VERSION, "target_round": 701,
        "algorithm_manifest_sha256": reg["algorithm_manifest"]["manifest_sha256"],
        "inclusion_p_canonical": canonical, "inclusion_p_sha256": shadow.vector_sha256(canonical),
        "top7_numbers": list(range(1, 8)),
    }
    (tmp_path / shadow.REGISTRY_NAME).write_text(json.dumps(registry), encoding="utf-8")
    with pytest.raises(ValueError, match="immutable freeze history"):
        guard.validate_existing_shadow(tmp_path)
