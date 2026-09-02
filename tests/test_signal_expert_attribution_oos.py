import copy
import csv
from pathlib import Path

import numpy as np
import pytest

import loto7_v2_runner as v2
import signal_expert_attribution_oos as attr
from loto7_evolving_agent import expert_probabilities


def synthetic_history(n: int = 140, seed: int = 20260902) -> np.ndarray:
    rng = np.random.default_rng(seed)
    x = np.zeros((n, 37), dtype=np.int8)
    for t in range(n):
        idx = rng.choice(np.arange(37), size=7, replace=False)
        x[t, idx] = 1
    return x


def test_champion_snapshot_reproduces_v2_and_exact_decomposition():
    x = synthetic_history(135)
    cfg = v2.DEFAULT_CHAMPION
    snap = attr.champion_snapshot(x, cfg, min_train=100)
    keys = list(snap["keys"])
    assert keys == list(expert_probabilities(x[:100]).keys())
    assert len(keys) == 11

    logw = np.zeros(len(keys), dtype=float)
    for t in range(100, len(x)):
        logw = v2._update_log_weights(x[:t], np.flatnonzero(x[t]), keys, logw, cfg)
    direct = v2._score_distribution(x, keys, logw, cfg)
    assert np.allclose(snap["final_q"], direct, atol=2e-15, rtol=0.0)

    uniform = np.ones(37) / 37.0
    reconstructed = uniform + np.sum(np.stack([snap["contributions"][k] for k in keys]), axis=0)
    assert np.allclose(reconstructed, snap["final_q"], atol=2e-15, rtol=0.0)
    assert float(snap["decomposition_max_abs_error"]) <= 2e-15


def test_leave_one_out_distributions_are_valid_and_prefrozen():
    x = synthetic_history(132)
    snap = attr.champion_snapshot(x, v2.DEFAULT_CHAMPION, min_train=100)
    for key in snap["keys"]:
        q = np.asarray(snap["loo_q"][key], dtype=float)
        assert q.shape == (37,)
        assert np.all(q > 0.0)
        assert abs(float(q.sum()) - 1.0) < 1e-12


def test_freeze_is_deterministic_except_timestamp_and_crosscheck(tmp_path: Path):
    x = synthetic_history(130)
    cfg = v2.DEFAULT_CHAMPION
    r1 = attr.freeze_reference(tmp_path, x, 692, "data-sha", cfg, "verified_two_result_sources", 100)
    sha1 = r1["final_q_sha256"]
    expert_hashes1 = dict(r1["expert_q_sha256"])
    loo_hashes1 = dict(r1["leave_one_out_q_sha256"])
    r2 = attr.freeze_reference(tmp_path, x, 692, "data-sha", cfg, "verified_two_result_sources", 100)
    assert r2["target_round"] == 693
    assert r2["final_q_sha256"] == sha1
    assert r2["expert_q_sha256"] == expert_hashes1
    assert r2["leave_one_out_q_sha256"] == loo_hashes1
    assert r2["expert_count"] == 11
    assert r2["calibration_shadow_crosscheck"]["status"] == "not_available"


def test_same_target_calibration_hash_crosscheck(tmp_path: Path):
    x = synthetic_history(130)
    cfg = v2.DEFAULT_CHAMPION
    snap = attr.champion_snapshot(x, cfg, 100)
    final_can = attr.canonical_vector(snap["final_q"], positive=True, normalize=True)
    final_sha = attr.vector_sha256(final_can, 37)
    attr.write_json(tmp_path / attr.CALIBRATION_REGISTRY_NAME, {"target_round": 693, "base_q_sha256": final_sha})
    reg = attr.freeze_reference(tmp_path, x, 692, "data-sha", cfg, "verified_two_result_sources", 100)
    assert reg["calibration_shadow_crosscheck"]["status"] == "matched"

    attr.write_json(tmp_path / attr.CALIBRATION_REGISTRY_NAME, {"target_round": 693, "base_q_sha256": "bad"})
    with pytest.raises(RuntimeError, match="calibration base q hash mismatch"):
        attr.freeze_reference(tmp_path, x, 692, "data-sha", cfg, "verified_two_result_sources", 100)


def test_registry_hash_tamper_fails_closed(tmp_path: Path):
    x = synthetic_history(130)
    reg = attr.freeze_reference(tmp_path, x, 692, "data-sha", v2.DEFAULT_CHAMPION, "verified_two_result_sources", 100)
    broken = copy.deepcopy(reg)
    broken["expert_q_canonical"][broken["expert_keys"][0]][0] = "0.123"
    with pytest.raises(ValueError, match="expert q hash mismatch"):
        attr.validate_registry(broken)


def test_trusted_grade_exact_mass_contributions_sum_to_full_edge(tmp_path: Path):
    x = synthetic_history(131)
    train = x[:-1]
    actual_idx = np.flatnonzero(x[-1])
    cfg = v2.DEFAULT_CHAMPION
    reg = attr.freeze_reference(tmp_path, train, 692, "data-sha", cfg, "verified_two_result_sources", 100)
    state = attr.default_state(cfg, 693)
    action = attr.grade_if_ready(
        tmp_path, reg, state, 693, "2026-09-04", actual_idx,
        "verified_two_result_sources", True,
    )
    assert action == "graded_trusted"
    assert state["trusted_draws"] == 1
    assert 693 in state["graded_rounds"]
    assert abs(float(state["last_grade_exact_mass_contribution_sum"]) - float(state["last_grade_full_mass_edge_vs_uniform"])) < 1e-12

    with (tmp_path / attr.RESULTS_NAME).open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 11
    total = sum(float(r["exact_weighted_mass_contribution_vs_uniform"]) for r in rows)
    assert abs(total - float(rows[0]["full_mass_edge_vs_uniform"])) < 1e-12


def test_untrusted_result_waits_without_rows(tmp_path: Path):
    x = synthetic_history(131)
    cfg = v2.DEFAULT_CHAMPION
    reg = attr.freeze_reference(tmp_path, x[:-1], 692, "data-sha", cfg, "verified_two_result_sources", 100)
    state = attr.default_state(cfg, 693)
    action = attr.grade_if_ready(tmp_path, reg, state, 693, "2026-09-04", np.flatnonzero(x[-1]), "single_source", False)
    assert action == "awaiting_trusted_verification"
    assert state["trusted_draws"] == 0
    assert not (tmp_path / attr.RESULTS_NAME).exists()


def test_missed_target_fails_closed(tmp_path: Path):
    x = synthetic_history(130)
    cfg = v2.DEFAULT_CHAMPION
    reg = attr.freeze_reference(tmp_path, x, 692, "data-sha", cfg, "verified_two_result_sources", 100)
    state = attr.default_state(cfg, 693)
    action = attr.grade_if_ready(tmp_path, reg, state, 694, "2026-09-11", np.array([], dtype=int), "verified_two_result_sources", True)
    assert action == "missed_target_fail_closed"
    assert state["status"] == "invalid_missed_prefrozen_target"
    assert state["trusted_draws"] == 0


def test_summary_is_descriptive_only(tmp_path: Path):
    x = synthetic_history(131)
    cfg = v2.DEFAULT_CHAMPION
    reg = attr.freeze_reference(tmp_path, x[:-1], 692, "data-sha", cfg, "verified_two_result_sources", 100)
    state = attr.default_state(cfg, 693)
    attr.grade_if_ready(tmp_path, reg, state, 693, "2026-09-04", np.flatnonzero(x[-1]), "verified_two_result_sources", True)
    attr.write_summary(tmp_path, reg["expert_keys"])
    assert (tmp_path / attr.SUMMARY_NAME).exists()
    assert state["interim_model_changes_allowed"] is False
    assert "no_expert_selection_or_weight_change" in state["claim_policy"]
