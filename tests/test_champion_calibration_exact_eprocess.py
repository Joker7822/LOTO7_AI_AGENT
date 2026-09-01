import itertools
import json
import math

import numpy as np

import champion_calibration_exact_eprocess as ep
import champion_calibration_oos as shadow


def brute_log_mgf(values, coefficient, lam, k):
    arr = np.asarray(values, dtype=float)
    mean = float(np.mean(arr))
    sd = abs(coefficient) * ep.sample_mean_sd(arr, k)
    if sd <= 1e-15:
        return 0.0
    vals = []
    for combo in itertools.combinations(range(len(arr)), k):
        centered_mean = float(np.mean(arr[list(combo)]) - mean)
        s = coefficient * centered_mean / sd
        vals.append(math.exp(lam * s))
    return math.log(sum(vals) / len(vals))


def test_exact_mgf_matches_bruteforce_small_population():
    values = np.array([0.1, 0.3, 0.8, 1.1, 1.7, 2.2], dtype=float)
    k = 2
    coefficient = 1.7
    lam = 0.8
    sd = abs(coefficient) * ep.sample_mean_sd(values, k)
    observed_centered = coefficient * (float(np.mean(values[[0, 5]])) - float(np.mean(values)))
    got = ep.exact_standardized_log_mgf(values, observed_centered, coefficient, lam, k)
    want = brute_log_mgf(values, coefficient, lam, k)
    assert abs(got["log_mgf"] - want) < 1e-12
    assert abs(got["standardized_observed"] - observed_centered / sd) < 1e-12


def test_exact_factor_has_null_mean_one_small_population():
    values = np.array([-1.0, -0.2, 0.4, 0.9, 1.5, 2.0], dtype=float)
    k = 2
    coefficient = 1.0
    lam = 1.2
    mean = float(np.mean(values))
    factors = []
    for combo in itertools.combinations(range(len(values)), k):
        centered = coefficient * (float(np.mean(values[list(combo)])) - mean)
        terms = ep.exact_standardized_log_mgf(values, centered, coefficient, lam, k)
        factors.append(math.exp(terms["log_factor"]))
    assert abs(float(np.mean(factors)) - 1.0) < 1e-12


def test_uniform_q_has_no_evidence_and_zero_null_variance():
    q = np.full(37, 1.0 / 37.0)
    for lam in ep.LAMBDAS:
        lt = ep.log_endpoint_terms(q, 0.0, lam)
        bt = ep.brier_endpoint_terms(q, 0.0, lam)
        assert lt["factor"] == 1.0
        assert bt["factor"] == 1.0
        assert lt["metric_sd"] == 0.0
        assert bt["metric_sd"] == 0.0


def test_proper_score_null_means_are_nonpositive():
    raw = np.arange(1.0, 38.0)
    q = raw / raw.sum()
    log_terms = ep.log_endpoint_terms(q, 0.0, 1.0)
    brier_terms = ep.brier_endpoint_terms(q, 0.0, 1.0)
    assert log_terms["null_mean"] < 0.0
    assert brier_terms["null_mean"] < 0.0


def test_endpoint_threshold_is_preregistered_bonferroni_40():
    assert ep.FAMILY_ALPHA == 0.05
    assert len(ep.ENDPOINTS) == 2
    assert ep.ENDPOINT_ALPHA == 0.025
    assert ep.E_VALUE_THRESHOLD == 40.0


def test_registration_is_immutable_once_created(tmp_path):
    out = tmp_path
    first = {
        "target_round": 693,
        "calibrated_q_sha256": "cal-693",
        "base_q_sha256": "base-693",
    }
    reg1 = ep.register_if_missing(out, first)
    second = {
        "target_round": 694,
        "calibrated_q_sha256": "cal-694",
        "base_q_sha256": "base-694",
    }
    reg2 = ep.register_if_missing(out, second)
    assert reg1 == reg2
    assert reg2["starts_target_round"] == 693
    assert reg2["initial_calibration_q_sha256"] == "cal-693"
    assert reg2["e_value_threshold_each"] == 40.0


def test_rebuild_with_no_results_is_not_evaluated(tmp_path):
    out = tmp_path
    q = np.linspace(1.0, 2.0, 37)
    q /= q.sum()
    canonical = shadow.canonical_q(q)
    freeze = {
        "target_round": 693,
        "calibrated_q_canonical": canonical,
        "calibrated_q_sha256": shadow.vector_sha256(canonical),
    }
    (out / shadow.FREEZE_HISTORY_NAME).write_text(json.dumps(freeze) + "\n", encoding="utf-8")
    reg = {
        "version": ep.VERSION,
        "registered_at_jst": "2026-09-01T12:00:00+09:00",
        "starts_target_round": 693,
    }
    state = ep.rebuild_state(out, reg)
    assert state["trusted_draws_processed"] == 0
    assert state["log_score_mixture_e_value"] == 1.0
    assert state["brier_mixture_e_value"] == 1.0
    assert state["claim_confirmed"] is False
    assert state["claim_status"] == "not_evaluated_until_horizon_complete"


def test_trusted_result_requires_matching_prefrozen_hash(tmp_path):
    out = tmp_path
    q = np.linspace(1.0, 2.0, 37)
    q /= q.sum()
    canonical = shadow.canonical_q(q)
    freeze = {
        "target_round": 693,
        "calibrated_q_canonical": canonical,
        "calibrated_q_sha256": shadow.vector_sha256(canonical),
    }
    (out / shadow.FREEZE_HISTORY_NAME).write_text(json.dumps(freeze) + "\n", encoding="utf-8")
    fields = shadow.RESULT_FIELDS
    row = {k: "" for k in fields}
    row.update({
        "round": "693",
        "trusted": "true",
        "calibrated_q_sha256": "tampered",
        "log_delta_vs_uniform": "0.01",
        "brier_improvement_vs_uniform": "0.001",
        "actual_mass_delta_vs_uniform": "0.001",
        "rank_preserved": "true",
        "top7_delta_vs_base": "0",
    })
    import csv
    with (out / shadow.RESULTS_NAME).open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerow(row)
    reg = {"version": ep.VERSION, "registered_at_jst": "x", "starts_target_round": 693}
    try:
        ep.rebuild_state(out, reg)
        assert False, "expected hash mismatch"
    except RuntimeError as exc:
        assert "hash mismatch" in str(exc)
