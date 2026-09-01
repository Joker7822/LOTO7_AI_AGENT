from __future__ import annotations

import json

import numpy as np

import champion_calibration_oos as oos
import champion_ranking_calibration as calibration
import loto7_v2_runner as v2


def base_q() -> np.ndarray:
    q = np.arange(1.0, 38.0, dtype=float)
    return q / q.sum()


def make_registry(tmp_path, monkeypatch, latest_round: int = 692):
    cfg = v2.DEFAULT_CHAMPION
    chosen = next(c for c in calibration.PREDECLARED_CONFIGS if c.name == "shrink-0p93")
    monkeypatch.setattr(oos, "choose_next_calibration", lambda x, locked_cfg, min_train=100: chosen)
    monkeypatch.setattr(oos, "current_q_for_cfg", lambda x, locked_cfg, min_train=100: base_q())
    monkeypatch.setattr(oos.v4, "now_jst", lambda: "2026-09-01T10:30:00+09:00")
    x = np.zeros((100, 37), dtype=float)
    return oos.freeze_reference(tmp_path, x, latest_round, "data-sha", cfg, "verified_two_result_sources")


def test_canonical_vector_hash_is_over_exact_string_vector():
    values = oos.canonical_q(base_q())
    h1 = oos.vector_sha256(values)
    h2 = oos.vector_sha256(list(values))
    assert h1 == h2
    changed = list(values)
    changed[0] = format(float(changed[0]) + 1e-12, oos.CANONICAL_FLOAT_FORMAT)
    assert oos.vector_sha256(changed) != h1


def test_validate_registry_detects_tampering(tmp_path, monkeypatch):
    registry = make_registry(tmp_path, monkeypatch)
    base, calibrated = oos.validate_registry(registry)
    assert calibration.rank_preserved(base, calibrated)
    tampered = dict(registry)
    tampered["calibrated_q_canonical"] = list(registry["calibrated_q_canonical"])
    tampered["calibrated_q_canonical"][0] = "0.5"
    try:
        oos.validate_registry(tampered)
    except ValueError as exc:
        assert "hash mismatch" in str(exc)
    else:
        raise AssertionError("tampered vector was accepted")


def test_freeze_is_future_only_and_persists_audit_history(tmp_path, monkeypatch):
    registry = make_registry(tmp_path, monkeypatch, latest_round=692)
    assert registry["target_round"] == 693
    assert registry["latest_resolved_round_at_freeze"] == 692
    assert registry["calibration_config"]["uniform_mix"] == 0.93
    assert registry["rank_preserved"] is True
    assert len(registry["base_q_canonical"]) == 37
    assert len(registry["calibrated_q_canonical"]) == 37
    history = (tmp_path / oos.FREEZE_HISTORY_NAME).read_text(encoding="utf-8").splitlines()
    assert len(history) == 1
    rec = json.loads(history[0])
    assert rec["target_round"] == 693
    assert rec["base_q_sha256"] == registry["base_q_sha256"]


def test_untrusted_result_waits_without_consuming_draw(tmp_path, monkeypatch):
    registry = make_registry(tmp_path, monkeypatch)
    state = oos.default_state(v2.DEFAULT_CHAMPION, 693)
    actual = np.arange(7, dtype=int)
    action = oos.grade_if_ready(
        tmp_path, registry, state, 693, "2026-09-04", actual, "unknown", False
    )
    assert action == "awaiting_trusted_verification"
    assert state["trusted_draws"] == 0
    assert state["graded_rounds"] == []
    assert not (tmp_path / oos.RESULTS_NAME).exists()


def test_trusted_grade_preserves_top7_and_updates_evidence(tmp_path, monkeypatch):
    registry = make_registry(tmp_path, monkeypatch)
    state = oos.default_state(v2.DEFAULT_CHAMPION, 693)
    actual = np.array([0, 5, 10, 15, 20, 25, 30], dtype=int)
    action = oos.grade_if_ready(
        tmp_path, registry, state, 693, "2026-09-04", actual,
        "verified_two_result_sources", True,
    )
    assert action == "graded_trusted"
    assert state["trusted_draws"] == 1
    assert state["graded_rounds"] == [693]
    assert state["rank_preserved_trusted_draws"] == 1
    assert abs(state["sum_top7_delta_vs_base"]) < 1e-12
    text = (tmp_path / oos.RESULTS_NAME).read_text(encoding="utf-8-sig")
    assert "verified_two_result_sources" in text


def test_missed_target_is_fail_closed_and_not_backfilled(tmp_path, monkeypatch):
    registry = make_registry(tmp_path, monkeypatch)
    state = oos.default_state(v2.DEFAULT_CHAMPION, 693)
    action = oos.grade_if_ready(
        tmp_path, registry, state, 694, "2026-09-11", np.array([], dtype=int),
        "verified_two_result_sources", True,
    )
    assert action == "missed_target_fail_closed"
    assert state["status"] == "invalid_missed_prefrozen_target"
    assert state["trusted_draws"] == 0
    assert not (tmp_path / oos.RESULTS_NAME).exists()


def test_fixed_horizon_completion_requires_trusted_draws(tmp_path, monkeypatch):
    registry = make_registry(tmp_path, monkeypatch)
    state = oos.default_state(v2.DEFAULT_CHAMPION, 693)
    state["horizon_trusted_draws"] = 1
    action = oos.grade_if_ready(
        tmp_path, registry, state, 693, "2026-09-04", np.arange(7, dtype=int),
        "verified_two_result_sources", True,
    )
    assert action == "graded_trusted"
    assert state["status"] == "complete_fixed_horizon"
    assert state["fixed_horizon_claim_status"] == "requires_final_fixed_horizon_analysis"


def test_protocol_locks_base_model_at_start():
    state = oos.default_state(v2.DEFAULT_CHAMPION, 693)
    assert state["locked_base_version"] == v2.DEFAULT_CHAMPION.version()
    assert state["promotion_role"] == "diagnostic_only"
    assert state["horizon_trusted_draws"] == 26
    assert state["fixed_horizon_claim_status"] == "not_evaluated_until_horizon_complete"
