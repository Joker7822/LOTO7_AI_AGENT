import csv
from pathlib import Path

import loto7_v2_runner as v2
import loto7_v4_runner as v4


def test_global_restarts_are_deterministic_and_bounded():
    a = v4.global_restarts("abc123", 7, 3)
    b = v4.global_restarts("abc123", 7, 3)
    assert a == b
    assert len(a) == 3
    for cfg in a:
        assert 0.8 <= cfg.eta <= 6.0
        assert 0.982 <= cfg.decay <= 0.9995
        assert 0.08 <= cfg.expert_uniform_mix <= 0.35
        assert 0.10 <= cfg.final_uniform_mix <= 0.42
        assert 0.35 <= cfg.overlap_penalty <= 1.10


def test_untrusted_oos_draw_does_not_spend_promotion_evidence():
    cfg = v2.DEFAULT_CHAMPION
    state = {"evidence": {}}
    rec = v4.update_evidence(
        state,
        "candidate-x",
        cfg.version(),
        {"name": "x", "eta": 2.0, "decay": 0.99, "expert_uniform_mix": 0.2,
         "final_uniform_mix": 0.2, "overlap_penalty": 0.6},
        delta=2.0,
        normalized_delta=0.2,
        trusted=False,
        round_no=100,
    )
    assert rec["all_draws"] == 1
    assert rec["trusted_draws"] == 0
    assert rec["e_value"] == 1.0


def test_promotion_requires_future_oos_thresholds_only():
    champ = v2.DEFAULT_CHAMPION
    candidate = v2.ModelConfig("future", 2.2, 0.994, 0.18, 0.22, 0.7)
    state = {
        "evidence": {
            v4.e_key(candidate.version(), champ.version()): {
                "candidate_version": candidate.version(),
                "champion_version": champ.version(),
                "config": candidate.__dict__,
                "trusted_draws": 8,
                "sum_delta": 1.2,
                "wins": 5,
                "e_value": 25.0,
            }
        }
    }
    eligible = v4.promotion_candidates(state, champ.version())
    assert len(eligible) == 1
    assert eligible[0][1]["candidate_version"] == candidate.version()


def test_grade_registry_is_append_only_and_idempotent(tmp_path: Path):
    champion = v2.DEFAULT_CHAMPION
    cand = v2.ModelConfig("shadow", 2.0, 0.994, 0.2, 0.2, 0.7)
    registry = {
        "target_round": 200,
        "base_data_sha": "old-data",
        "frozen_at_jst": "2026-01-01T00:00:00+09:00",
        "champion_version": champion.version(),
        "champion_tickets": [[1,2,3,4,5,6,7]] * 5,
        "candidates": [{
            "version": cand.version(),
            "config": cand.__dict__,
            "tickets": [[1,2,3,4,5,6,8]] * 5,
        }],
    }
    state = {"graded_rounds": [], "evidence": {}}
    out = tmp_path / "oos.csv"
    actual = {1,2,3,4,5,6,8}
    assert v4.grade_registry(registry, 200, "2026-01-02", actual,
                             "verified_two_result_sources", True, state, out)
    assert not v4.grade_registry(registry, 200, "2026-01-02", actual,
                                 "verified_two_result_sources", True, state, out)
    rows = list(csv.DictReader(out.open(encoding="utf-8-sig")))
    assert len(rows) == 1
    assert rows[0]["trusted_for_promotion"] == "true"
    rec = state["evidence"][v4.e_key(cand.version(), champion.version())]
    assert rec["trusted_draws"] == 1
    assert rec["sum_delta"] > 0
