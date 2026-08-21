import math

import loto7_v2_runner as v2
from loto7_v3_runner import (
    alpha_per_candidate,
    candidate_decision,
    make_mutants,
    paired_signflip_p,
)


def test_mutants_are_deterministic_unique_and_bounded():
    champ = v2.ModelConfig("baseline", 3.0, 0.995, 0.15, 0.20, 0.65)
    a = make_mutants(champ, "abc123", 7, count=6)
    b = make_mutants(champ, "abc123", 7, count=6)
    assert [x.version() for x in a] == [x.version() for x in b]
    assert len({x.version() for x in a}) == 6
    for x in a:
        assert 0.8 <= x.eta <= 6.0
        assert 0.982 <= x.decay <= 0.9995
        assert 0.08 <= x.expert_uniform_mix <= 0.35
        assert 0.10 <= x.final_uniform_mix <= 0.42
        assert 0.35 <= x.overlap_penalty <= 1.10


def test_alpha_spending_gets_stricter_each_same_data_day():
    a1 = alpha_per_candidate(1, 6)
    a2 = alpha_per_candidate(2, 6)
    a5 = alpha_per_candidate(5, 6)
    assert a1 > a2 > a5 > 0
    assert math.isclose(a1, 0.05 / 12.0)


def test_paired_signflip_detects_clear_paired_improvement():
    p = paired_signflip_p([1.0] * 120, [2.0] * 120, seed=1, reps=4096)
    assert p < 0.01


def _eval(score, max_hits, random_score, daily_value):
    return {
        "windows": {
            w: {
                "model": {"score": score, "max_hits": max_hits},
                "score_delta_vs_random": score - random_score,
            }
            for w in ("30", "60", "120")
        },
        "daily_scores": [daily_value] * 120,
    }


def test_candidate_gate_requires_stable_statistical_improvement():
    champ = _eval(2.0, 2.0, 1.9, 1.0)
    cand = _eval(2.2, 2.1, 1.9, 1.2)
    ok, detail = candidate_decision(champ, cand, alpha=0.01, seed=4)
    assert ok
    assert detail["checks"]["paired_p120_pass"]

    unstable = _eval(2.0, 2.1, 1.9, 1.2)
    ok2, _ = candidate_decision(champ, unstable, alpha=0.01, seed=4)
    assert not ok2
