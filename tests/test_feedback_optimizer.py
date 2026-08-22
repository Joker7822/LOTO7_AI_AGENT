import pytest

import feedback_optimizer as fo
import loto7_v2_runner as v2


def summary(obj, full_max=2.4, score120=2.8):
    return {
        "feedback_objective": obj,
        "windows": {
            "full": {"max_hits": full_max, "score": 2.7, "random_score": 2.75, "random_max_hits": 2.42,
                     "random_mean_hits": 1.32, "random_ge3": 0.43, "random_ge4": 0.07},
            "120": {"max_hits": 2.4, "score": score120, "random_score": 2.75, "random_max_hits": 2.42,
                    "random_mean_hits": 1.32, "random_ge3": 0.43, "random_ge4": 0.07},
            "60": {"max_hits": 2.4, "score": 2.8, "random_score": 2.75, "random_max_hits": 2.42,
                   "random_mean_hits": 1.32, "random_ge3": 0.43, "random_ge4": 0.07},
            "30": {"max_hits": 2.4, "score": 2.8, "random_score": 2.75, "random_max_hits": 2.42,
                   "random_mean_hits": 1.32, "random_ge3": 0.43, "random_ge4": 0.07},
        },
    }


def test_expanded_candidates_are_deterministic_and_break_old_eta_floor():
    parent = v2.ModelConfig("parent", 0.8, 0.994, 0.22, 0.19, 0.99)
    a = fo.expanded_candidates(parent, "abc", 10, count=2)
    b = fo.expanded_candidates(parent, "abc", 10, count=2)
    assert a == b
    assert len(a) == 2
    assert a[0].eta < 0.8
    for cfg in a:
        assert fo.ETA_BOUNDS[0] <= cfg.eta <= fo.ETA_BOUNDS[1]
        assert fo.DECAY_BOUNDS[0] <= cfg.decay <= fo.DECAY_BOUNDS[1]
        assert fo.EXPERT_MIX_BOUNDS[0] <= cfg.expert_uniform_mix <= fo.EXPERT_MIX_BOUNDS[1]
        assert fo.FINAL_MIX_BOUNDS[0] <= cfg.final_uniform_mix <= fo.FINAL_MIX_BOUNDS[1]
        assert fo.OVERLAP_BOUNDS[0] <= cfg.overlap_penalty <= fo.OVERLAP_BOUNDS[1]


def test_choose_best_uses_full_history_acceptance_gate():
    incumbent = summary(-0.10)
    weak = v2.ModelConfig("weak", 0.7, 0.994, 0.2, 0.2, 1.0)
    strong = v2.ModelConfig("strong", 0.5, 0.995, 0.2, 0.2, 1.2)
    selected, selected_summary, decisions = fo.choose_best(
        incumbent,
        [(weak, summary(-0.099)), (strong, summary(-0.05))],
    )
    assert selected == strong
    assert selected_summary["feedback_objective"] == -0.05
    assert any(d["accepted"] for d in decisions)


def test_choose_best_rejects_recent_regression_even_if_objective_improves():
    incumbent = summary(-0.10, score120=2.8)
    bad_recent = v2.ModelConfig("badrecent", 0.4, 0.994, 0.2, 0.2, 1.0)
    selected, selected_summary, decisions = fo.choose_best(
        incumbent,
        [(bad_recent, summary(-0.01, score120=2.70))],
    )
    assert selected is None
    assert selected_summary is None
    assert decisions[0]["accepted"] is False


def test_summary_reuses_same_random_reference_for_comparability():
    cfg = v2.ModelConfig("x", 0.5, 0.99, 0.2, 0.2, 1.0)
    model_windows = {
        name: {"max_hits": 2.5, "mean_hits": 1.4, "ge3": 0.5, "ge4": 0.1, "score": 2.9}
        for name in ("full", "120", "60", "30")
    }
    ref = summary(-0.1)
    got = fo.summary_with_reference(cfg, model_windows, ref, "sha", 100, 350)
    assert got["windows"]["full"]["random_score"] == ref["windows"]["full"]["random_score"]
    assert got["windows"]["full"]["score_delta_vs_random"] == pytest.approx(0.15)
