from pathlib import Path

import numpy as np

import champion_calibration_oos as calibration_oos
import loto7_v2_runner as v2
import signal_expert_attribution_oos as attr
import signal_expert_attribution_oos_stable as stable


def synthetic_history(n: int = 140, seed: int = 20260913) -> np.ndarray:
    rng = np.random.default_rng(seed)
    x = np.zeros((n, 37), dtype=np.int8)
    for t in range(n):
        idx = rng.choice(np.arange(37), size=7, replace=False)
        x[t, idx] = 1
    return x


def test_stable_snapshot_hash_matches_actual_calibration_implementation():
    x = synthetic_history(130)
    cfg = v2.DEFAULT_CHAMPION

    snap = stable.stable_champion_snapshot(x, cfg, 100)
    calibration_q = calibration_oos.current_q_for_cfg(x, cfg, 100)

    # The canonical distribution must now be the exact same numerical path used
    # by Champion calibration, not only numerically close to it.
    assert np.array_equal(np.asarray(snap["final_q"]), np.asarray(calibration_q))

    attr_sha = attr.vector_sha256(
        attr.canonical_vector(snap["final_q"], positive=True, normalize=True), 37
    )
    calibration_sha = calibration_oos.vector_sha256(
        calibration_oos.canonical_q(calibration_q)
    )
    assert attr_sha == calibration_sha


def test_realistic_same_target_crosscheck_stays_fail_closed(tmp_path: Path):
    x = synthetic_history(130)
    cfg = v2.DEFAULT_CHAMPION
    calibration_q = calibration_oos.current_q_for_cfg(x, cfg, 100)
    calibration_sha = calibration_oos.vector_sha256(
        calibration_oos.canonical_q(calibration_q)
    )
    attr.write_json(
        tmp_path / attr.CALIBRATION_REGISTRY_NAME,
        {"target_round": 693, "base_q_sha256": calibration_sha},
    )

    original = attr.champion_snapshot
    try:
        attr.champion_snapshot = stable.stable_champion_snapshot
        reg = attr.freeze_reference(
            tmp_path, x, 692, "data-sha", cfg, "verified_two_result_sources", 100
        )
        assert reg["calibration_shadow_crosscheck"]["status"] == "matched"

        attr.write_json(
            tmp_path / attr.CALIBRATION_REGISTRY_NAME,
            {"target_round": 693, "base_q_sha256": "bad"},
        )
        try:
            attr.freeze_reference(
                tmp_path, x, 692, "data-sha", cfg, "verified_two_result_sources", 100
            )
        except RuntimeError as exc:
            assert "calibration base q hash mismatch" in str(exc)
        else:
            raise AssertionError("mismatched calibration hash must fail closed")
    finally:
        attr.champion_snapshot = original
