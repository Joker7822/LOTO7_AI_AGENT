from dataclasses import asdict
from pathlib import Path

import numpy as np
import pytest

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


def calibration_registry(
    q: np.ndarray,
    cfg: v2.ModelConfig,
    data_sha: str = "data-sha",
    target_round: int = 693,
):
    canonical = calibration_oos.canonical_q(q)
    return {
        "target_round": target_round,
        "base_data_sha256": data_sha,
        "locked_base_version": cfg.version(),
        "locked_base_config": asdict(cfg),
        "top7_numbers": [int(i + 1) for i in np.argsort(-q, kind="mergesort")[:7]],
        "base_q_canonical": canonical,
        "base_q_sha256": calibration_oos.vector_sha256(canonical),
    }


def test_stable_snapshot_hash_matches_actual_calibration_implementation():
    x = synthetic_history(130)
    cfg = v2.DEFAULT_CHAMPION

    snap = stable.stable_champion_snapshot(x, cfg, 100)
    calibration_q = calibration_oos.current_q_for_cfg(x, cfg, 100)

    assert np.array_equal(np.asarray(snap["final_q"]), np.asarray(calibration_q))

    attr_sha = attr.vector_sha256(
        attr.canonical_vector(snap["final_q"], positive=True, normalize=True), 37
    )
    calibration_sha = calibration_oos.vector_sha256(
        calibration_oos.canonical_q(calibration_q)
    )
    assert attr_sha == calibration_sha


def test_exact_same_target_calibration_crosscheck_matches(tmp_path: Path):
    x = synthetic_history(130)
    cfg = v2.DEFAULT_CHAMPION
    calibration_q = calibration_oos.current_q_for_cfg(x, cfg, 100)
    cal = calibration_registry(calibration_q, cfg)
    attr.write_json(tmp_path / attr.CALIBRATION_REGISTRY_NAME, cal)

    reg = stable.stable_freeze_reference(
        tmp_path, x, 692, "data-sha", cfg, "verified_two_result_sources", 100
    )
    cross = reg["calibration_shadow_crosscheck"]
    assert cross["status"] == "matched"
    assert cross["reconciled_to_frozen_calibration_q"] is False
    assert reg["final_q_sha256"] == cal["base_q_sha256"]


def test_machine_epsilon_drift_reconciles_to_authoritative_frozen_q(tmp_path: Path):
    x = synthetic_history(130)
    cfg = v2.DEFAULT_CHAMPION
    current_q = calibration_oos.current_q_for_cfg(x, cfg, 100)
    current_sha = calibration_oos.vector_sha256(calibration_oos.canonical_q(current_q))

    # Simulate an independent runner/runtime producing a numerically equivalent
    # vector whose .17g representation nevertheless hashes differently.
    frozen_q = current_q.copy()
    frozen_sha = current_sha
    for _ in range(64):
        frozen_q[0] = np.nextafter(frozen_q[0], np.inf)
        frozen_q[1] = np.nextafter(frozen_q[1], -np.inf)
        frozen_sha = calibration_oos.vector_sha256(calibration_oos.canonical_q(frozen_q))
        if frozen_sha != current_sha:
            break
    assert frozen_sha != current_sha
    assert float(np.max(np.abs(frozen_q - current_q))) <= stable.NUMERIC_EQUIVALENCE_ATOL

    cal = calibration_registry(frozen_q, cfg)
    attr.write_json(tmp_path / attr.CALIBRATION_REGISTRY_NAME, cal)
    reg = stable.stable_freeze_reference(
        tmp_path, x, 692, "data-sha", cfg, "verified_two_result_sources", 100
    )

    cross = reg["calibration_shadow_crosscheck"]
    assert cross["status"] == "matched"
    assert cross["reconciled_to_frozen_calibration_q"] is True
    assert cross["max_abs_q_delta_before_reconcile"] <= stable.NUMERIC_EQUIVALENCE_ATOL
    assert reg["final_q_sha256"] == cal["base_q_sha256"]
    assert reg["final_q_canonical"] == cal["base_q_canonical"]
    attr.validate_registry(reg)


def test_same_target_data_identity_mismatch_still_fails_closed(tmp_path: Path):
    x = synthetic_history(130)
    cfg = v2.DEFAULT_CHAMPION
    calibration_q = calibration_oos.current_q_for_cfg(x, cfg, 100)
    cal = calibration_registry(calibration_q, cfg, data_sha="different-data-sha")
    attr.write_json(tmp_path / attr.CALIBRATION_REGISTRY_NAME, cal)

    with pytest.raises(RuntimeError, match="calibration data hash mismatch"):
        stable.stable_freeze_reference(
            tmp_path, x, 692, "data-sha", cfg, "verified_two_result_sources", 100
        )
