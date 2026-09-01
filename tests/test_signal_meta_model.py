from __future__ import annotations

import numpy as np

import null_search_calibration as nsc
import signal_meta_model as meta


def synthetic(rows: int = 180, seed: int = 123) -> np.ndarray:
    return nsc.synthetic_history(rows, seed=seed)


def test_feature_matrix_is_finite_centered_and_prefix_only():
    x = synthetic(80, 1)
    a, names_a = meta.feature_matrix(x[:60])
    b, names_b = meta.feature_matrix(np.vstack([x[:60], x[60:70]])[:60])
    assert names_a == names_b
    assert a.shape == (37, len(names_a))
    assert np.all(np.isfinite(a))
    assert np.allclose(a, b)
    assert np.max(np.abs(a.mean(axis=0))) < 1e-10


def test_zero_weights_predict_uniform():
    x = synthetic(50, 2)
    features, _ = meta.feature_matrix(x)
    q = meta.predict_from_features(features, np.zeros(features.shape[1]), uniform_mix=0.25)
    assert q.shape == (37,)
    assert np.all(q > 0)
    assert abs(float(q.sum()) - 1.0) < 1e-12
    assert np.max(np.abs(q - 1.0 / 37.0)) < 1e-12


def test_update_occurs_only_after_actual_is_supplied():
    x = synthetic(60, 3)
    features, _ = meta.feature_matrix(x[:50])
    cfg = meta.PREDECLARED_CONFIGS[1]
    w0 = np.zeros(features.shape[1])
    q_before = meta.predict_from_features(features, w0, cfg.uniform_mix)
    actual = np.flatnonzero(x[50])
    w1 = meta.update_weights(features, actual, w0, cfg)
    q_same_weights = meta.predict_from_features(features, w0, cfg.uniform_mix)
    assert np.allclose(q_before, q_same_weights)
    assert not np.allclose(w0, w1)
    assert np.all(np.isfinite(w1))
    assert np.max(np.abs(w1)) <= cfg.max_abs_weight + 1e-12


def test_replay_prefix_predictions_do_not_change_when_future_is_appended():
    x = synthetic(150, 4)
    cfg = meta.PREDECLARED_CONFIGS[0]
    short = meta.replay_config(x[:130], cfg, min_train=100)
    long = meta.replay_config(x, cfg, min_train=100)
    assert len(short["qs"]) == 30
    assert len(long["qs"]) == 50
    for a, b in zip(short["qs"], long["qs"][:30]):
        assert np.allclose(a, b)


def test_nested_selector_uses_only_prior_rows():
    # At index 2 model B has an enormous target-row score, but prior rows favor A.
    def row(logp: float):
        return {
            "top7_hits": 1.0,
            "actual_mass": 7.0 / 37.0,
            "mean_log_prob_actual": logp,
            "brier": 0.02,
            "uniform_brier": 0.02,
        }

    a = {
        "version": "A",
        "rows": [row(-3.0), row(-3.0), row(-10.0)],
        "qs": [np.full(37, 1 / 37)] * 3,
    }
    b = {
        "version": "B",
        "rows": [row(-4.0), row(-4.0), row(0.0)],
        "qs": [np.full(37, 1 / 37)] * 3,
    }
    selected = meta.nested_select([a, b], last_n=1)
    assert selected["selected_versions"] == ["A"]


def test_block_bootstrap_is_deterministic():
    vals = np.linspace(-0.1, 0.2, 40)
    a = meta.block_bootstrap_mean_ci(vals, seed=99, reps=200, block_len=5)
    b = meta.block_bootstrap_mean_ci(vals, seed=99, reps=200, block_len=5)
    assert a == b
    assert a["low95"] <= a["mean"] <= a["high95"]
