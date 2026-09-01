from __future__ import annotations

import numpy as np
import pytest

import champion_ranking_calibration as crc
import null_search_calibration as nsc
import separated_optimizer as so


def random_qs(n: int, seed: int = 123) -> list[np.ndarray]:
    rng = np.random.default_rng(seed)
    return [rng.dirichlet(np.ones(37) * 4.0) for _ in range(n)]


def test_identity_is_exact_after_normalization():
    q = random_qs(1)[0]
    out = crc.calibrate_q(q, crc.PREDECLARED_CONFIGS[0])
    assert np.allclose(out, q / q.sum(), atol=1e-14, rtol=0.0)


def test_all_predeclared_configs_preserve_full_ranking_and_top7():
    q = random_qs(1, seed=7)[0]
    base_order = crc.rank_order(q)
    base_top7 = set(base_order[:7].tolist())
    for cfg in crc.PREDECLARED_CONFIGS:
        out = crc.calibrate_q(q, cfg)
        assert np.isclose(out.sum(), 1.0)
        assert np.all(out > 0.0)
        assert crc.rank_preserved(q, out)
        assert np.array_equal(crc.rank_order(out), base_order)
        assert set(crc.rank_order(out)[:7].tolist()) == base_top7


def test_strong_uniform_shrinkage_moves_scores_toward_uniform_without_rank_loss():
    q = random_qs(1, seed=9)[0]
    cfg = crc.CalibrationConfig("test", 1.0, 0.97)
    out = crc.calibrate_q(q, cfg)
    assert crc.rank_preserved(q, out)
    assert np.max(np.abs(out - crc.UNIFORM_Q)) < np.max(np.abs(q / q.sum() - crc.UNIFORM_Q))


def test_uniform_mix_one_is_rejected_because_it_would_destroy_strict_ranking():
    q = random_qs(1)[0]
    with pytest.raises(ValueError):
        crc.calibrate_q(q, crc.CalibrationConfig("bad", 1.0, 1.0))


def test_config_selection_for_target_does_not_use_target_result():
    min_train = 10
    x = nsc.synthetic_history(100, seed=11)
    qs = random_qs(len(x) - min_train, seed=12)
    rows_a = crc.precompute_rows(qs, x, min_train)
    target_index = 70
    selected_a = crc.choose_config(rows_a, target_index)

    x2 = x.copy()
    # Change only the target result. Selection for that target must be unchanged,
    # because choose_config consumes rows strictly before target_index.
    old = np.flatnonzero(x2[min_train + target_index])
    x2[min_train + target_index] = 0.0
    replacement = np.array([(int(old[0]) + k + 9) % 37 for k in range(7)], dtype=int)
    replacement = np.unique(replacement)
    if len(replacement) < 7:
        replacement = np.arange(7, dtype=int)
    x2[min_train + target_index, replacement[:7]] = 1.0
    rows_b = crc.precompute_rows(qs, x2, min_train)
    selected_b = crc.choose_config(rows_b, target_index)
    assert selected_a.version() == selected_b.version()


def test_nested_calibration_keeps_champion_top7_hits_identical_every_round():
    min_train = 20
    x = nsc.synthetic_history(120, seed=21)
    qs = random_qs(len(x) - min_train, seed=22)
    nested = crc.nested_calibration(qs, x, min_train=min_train, last_n=40)
    start = int(nested["start_index"])
    assert nested["rank_preservation_rate"] == 1.0
    for j, calibrated_row in enumerate(nested["rows"]):
        idx = start + j
        actual = np.flatnonzero(x[min_train + idx])
        base_row = so.signal_row(qs[idx], actual)
        assert calibrated_row["top7_hits"] == base_row["top7_hits"]
