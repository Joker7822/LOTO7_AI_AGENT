import json
from pathlib import Path

import numpy as np
import pytest

import joint_set_v2_signal_oos as s


def _manifest(tmp_path: Path):
    protocol = tmp_path / "protocol.py"
    model = tmp_path / "model.py"
    research = tmp_path / "research.py"
    protocol.write_text("protocol-v1\n", encoding="utf-8")
    model.write_text("model-v1\n", encoding="utf-8")
    research.write_text("research-v1\n", encoding="utf-8")
    return s.algorithm_manifest(protocol, model, research), protocol, model, research


def _registration(tmp_path: Path):
    manifest, _, _, _ = _manifest(tmp_path)
    return s.create_registration(699, "abc123", manifest)


def _uniform_registry(registration, target=701):
    p = np.full(s.N_NUMBERS, s.PICKS / s.N_NUMBERS, dtype=float)
    can = s.canonical_vector(p)
    return {
        "protocol_version": s.VERSION,
        "target_round": target,
        "latest_resolved_round_at_freeze": target - 1,
        "selected_config": "test-config",
        "selected_config_prior_score": 0.0,
        "inclusion_p_canonical": can,
        "inclusion_p_sha256": s.vector_sha256(can),
        "top7_numbers": list(range(1, 8)),
        "gate": 0.0,
        "regime": {"stable": 1.0, "shift": 0.0, "volatile": 0.0},
        "frozen_at_jst": "2026-10-20T00:00:00+09:00",
        "algorithm_manifest_sha256": registration["algorithm_manifest"]["manifest_sha256"],
    }


def test_registration_excludes_round_700_and_starts_701(tmp_path):
    registration = _registration(tmp_path)
    assert registration["start_target_round"] == 701
    assert registration["excluded_already_frozen_target_round"] == 700
    assert registration["horizon_trusted_draws"] == 26
    assert registration["promotion_role"] == "diagnostic_only"


def test_registration_refuses_retroactive_start(tmp_path):
    manifest, _, _, _ = _manifest(tmp_path)
    with pytest.raises(RuntimeError):
        s.create_registration(701, "abc123", manifest)


def test_algorithm_manifest_change_fails_lock(tmp_path):
    manifest, protocol, model, research = _manifest(tmp_path)
    registration = s.create_registration(699, "abc123", manifest)
    s.validate_manifest(registration, manifest)
    model.write_text("model-v2-changed\n", encoding="utf-8")
    changed = s.algorithm_manifest(protocol, model, research)
    with pytest.raises(ValueError):
        s.validate_manifest(registration, changed)


def test_registry_hash_and_top7_are_fail_closed(tmp_path):
    registration = _registration(tmp_path)
    registry = _uniform_registry(registration)
    p = s.validate_registry(registry, registration)
    assert np.isclose(p.sum(), 7.0)
    broken = dict(registry)
    broken["inclusion_p_sha256"] = "0" * 64
    with pytest.raises(ValueError):
        s.validate_registry(broken, registration)


def test_grade_refuses_missed_target(tmp_path):
    registration = _registration(tmp_path)
    registry = _uniform_registry(registration, 701)
    state = s.default_state(registration)
    action = s.grade_if_ready(
        tmp_path, registry, registration, state,
        latest_round=702, draw_date="2026-10-30",
        actual_idx=np.arange(7), source_verification="verified_two_result_sources", trusted=True,
    )
    assert action == "missed_target_fail_closed"
    assert state["status"] == "invalid_missed_prefrozen_target_or_next_freeze"


def test_uniform_prefrozen_vector_grades_zero_proper_edges(tmp_path):
    registration = _registration(tmp_path)
    registry = _uniform_registry(registration, 701)
    state = s.default_state(registration)
    action = s.grade_if_ready(
        tmp_path, registry, registration, state,
        latest_round=701, draw_date="2026-10-23",
        actual_idx=np.arange(7), source_verification="verified_two_result_sources", trusted=True,
    )
    assert action == "graded_trusted"
    assert state["trusted_draws"] == 1
    rows = s.read_result_rows(tmp_path / s.RESULTS_NAME)
    assert len(rows) == 1
    assert abs(float(rows[0]["bernoulli_log_edge_vs_uniform"])) < 1e-12
    assert abs(float(rows[0]["bernoulli_brier_edge_vs_uniform"])) < 1e-12


def test_fixed_horizon_uniform_permutation_is_neutral(tmp_path):
    registration = _registration(tmp_path)
    history_path = tmp_path / s.FREEZE_HISTORY_NAME
    rows = []
    for i in range(s.HORIZON_TRUSTED_DRAWS):
        target = 701 + i
        registry = _uniform_registry(registration, target)
        with history_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(registry, ensure_ascii=False) + "\n")
        rows.append({
            "round": str(target),
            "trusted": "True",
            "top7_hits": "7.0" if False else "1.0",
            "actual_inclusion_probability": str(s.UNIFORM_INCLUSION),
            "bernoulli_log_edge_vs_uniform": "0.0",
            "bernoulli_brier_edge_vs_uniform": "0.0",
            "actual_numbers": "1 2 3 4 5 6 7",
        })
    result = s.fixed_horizon_permutation_inference(tmp_path, registration, rows, reps=32)
    assert result["available"] is True
    assert abs(result["primary"]["observed"]) < 1e-12
    assert abs(result["primary"]["null_mean"]) < 1e-12
    assert result["primary"]["upper_tail_p"] == 1.0
